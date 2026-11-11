"""Registro de auditoría encadenado e inalterable (Chained Log Tamper-Evident).

Cada entrada en formato JSON Lines (JSONL) contiene el hash SHA-256 de la entrada
previa y un código de autenticación de mensajes HMAC-SHA256, garantizando que
cualquier inserción, eliminación, truncamiento o modificación de bits sea detectada.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def canonical_json(obj: Any) -> bytes:
    """Serializa un objeto Python a JSON canónico determinista (RFC 8785 aproximado).

    Claves ordenadas, sin espacios en separadores, codificación UTF-8 sin escape innecesario.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


@dataclass(frozen=True)
class LogEntry:
    seq: int
    ts_utc: str
    case_id: str
    examiner: str
    event: str
    module: str
    data: dict[str, Any]
    prev_hash: str
    entry_hash: str
    hmac: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json_line(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


def compute_entry_hash(payload: dict[str, Any]) -> str:
    """Calcula el hash SHA-256 de una entrada excluyendo los campos derivados entry_hash y hmac."""
    clean = {k: v for k, v in payload.items() if k not in ("entry_hash", "hmac")}
    return hashlib.sha256(canonical_json(clean)).hexdigest()


def compute_hmac(key: bytes, entry_hash: str) -> str:
    """Calcula el HMAC-SHA256 del hash de una entrada usando la clave de caso."""
    return hmac.new(key, entry_hash.encode("utf-8"), hashlib.sha256).hexdigest()


class ChainedLog:
    """Manejador de archivo de log continuo de solo adición con encadenamiento criptográfico."""

    def __init__(
        self,
        path: Path | str,
        key: bytes,
        genesis_hash: str,
        case_id: str,
        examiner: str,
    ) -> None:
        self.path = Path(path)
        self._key = key
        self.genesis_hash = genesis_hash
        self.case_id = case_id
        self.examiner = examiner
        self._prev_hash = genesis_hash
        self._seq = 0

        # Si el archivo ya existe, cargar la última secuencia y hash previo
        if self.path.exists() and self.path.stat().st_size > 0:
            self._load_existing_state()
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load_existing_state(self) -> None:
        last_line = ""
        count = 0
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped:
                    last_line = stripped
                    count += 1

        if last_line:
            data = json.loads(last_line)
            self._seq = data["seq"]
            self._prev_hash = data["entry_hash"]
        else:
            self._seq = 0
            self._prev_hash = self.genesis_hash

    @property
    def current_seq(self) -> int:
        return self._seq

    @property
    def last_hash(self) -> str:
        return self._prev_hash

    def append(self, event: str, module: str, data: dict[str, Any]) -> LogEntry:
        """Registra un nuevo evento en el archivo de log forzando fsync a disco."""
        self._seq += 1
        now_utc = datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")

        entry_payload: dict[str, Any] = {
            "seq": self._seq,
            "ts_utc": now_utc,
            "case_id": self.case_id,
            "examiner": self.examiner,
            "event": event,
            "module": module,
            "data": data,
            "prev_hash": self._prev_hash,
        }

        entry_hash = compute_entry_hash(entry_payload)
        hmac_sig = compute_hmac(self._key, entry_hash)

        entry = LogEntry(
            seq=self._seq,
            ts_utc=now_utc,
            case_id=self.case_id,
            examiner=self.examiner,
            event=event,
            module=module,
            data=data,
            prev_hash=self._prev_hash,
            entry_hash=entry_hash,
            hmac=hmac_sig,
        )

        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(entry.to_json_line() + "\n")
            fh.flush()
            os.fsync(fh.fileno())

        self._prev_hash = entry_hash
        return entry


def verify_chain(
    path: Path | str,
    key: bytes | None = None,
    expected_genesis: str | None = None,
) -> tuple[bool, str, int]:
    """Verifica la integridad criptográfica de un archivo de log JSONL encadenado.

    Retorna: (es_valido, mensaje_diagnostico, total_entradas_verificadas)
    """
    target = Path(path)
    if not target.is_file():
        return False, f"Archivo de log no encontrado: {path}", 0

    prev_hash: str | None = expected_genesis
    line_number = 0

    with target.open("r", encoding="utf-8") as fh:
        for line in fh:
            line_str = line.strip()
            if not line_str:
                continue
            line_number += 1

            try:
                entry = json.loads(line_str)
            except Exception as e:
                return False, f"Línea {line_number} no es un JSON válido: {e}", line_number - 1

            # 1. Verificar número de secuencia incremental
            seq = entry.get("seq")
            if seq != line_number:
                return (
                    False,
                    f"Secuencia alterada en línea {line_number}: "
                    f"esperado {line_number}, obtenido {seq}",
                    line_number - 1,
                )

            # 2. Verificar encadenamiento con el hash previo
            current_prev_hash = entry.get("prev_hash")
            if prev_hash is not None and current_prev_hash != prev_hash:
                return (
                    False,
                    f"Ruptura de cadena en secuencia {seq}: "
                    "prev_hash no coincide con la entrada previa.",
                    line_number - 1,
                )

            # 3. Recalcular y validar entry_hash
            claimed_hash = entry.get("entry_hash")
            recalculated_hash = compute_entry_hash(entry)
            if claimed_hash != recalculated_hash:
                return (
                    False,
                    f"Hash de entrada adulterado en secuencia {seq}: "
                    f"{claimed_hash} != {recalculated_hash}",
                    line_number - 1,
                )

            # 4. Verificar HMAC si se proveyó la clave
            if key is not None:
                claimed_hmac = entry.get("hmac")
                expected_hmac = compute_hmac(key, recalculated_hash)
                if not hmac.compare_digest(claimed_hmac or "", expected_hmac):
                    return (
                        False,
                        f"HMAC inválido en secuencia {seq}: "
                        "clave de caso no coincide o entrada modificada.",
                        line_number - 1,
                    )

            prev_hash = claimed_hash

    if line_number == 0:
        return False, "El archivo de log está vacío.", 0

    return True, f"Cadena íntegra. {line_number} entradas verificadas con éxito.", line_number
