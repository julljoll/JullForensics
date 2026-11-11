"""Adquisición forense de capturas de pantalla a memoria RAM sin alteración del terminal."""

from __future__ import annotations

import contextlib
import json
import re
import struct
import time
from datetime import UTC, datetime

from jullforensics.adb.runner import AdbRunner
from jullforensics.storage.evidence_store import EvidenceStore

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
TOP_ACTIVITY_PATTERN = re.compile(r"(?:topResumedActivity|mResumedActivity).*?\{([^\}]+)\}")


class ScreenshotError(Exception):
    """Lanzada ante fallos en la obtención o parseo de la captura de pantalla."""


def get_foreground_activity(runner: AdbRunner) -> str:
    """Obtiene la actividad de la app que está actualmente en primer plano en el teléfono."""
    with contextlib.suppress(Exception):
        cp = runner.run("shell", "dumpsys", "activity", "activities", timeout=5)
        text = cp.stdout.decode("utf-8", "replace")
        match = TOP_ACTIVITY_PATTERN.search(text)
        if match:
            return match.group(1).split()[-1]
    return "Desconocida"


def is_black_screen(png_data: bytes) -> bool:
    """Heurística para detectar pantallas negras (FLAG_SECURE o pantalla apagada)."""
    # En PNG comprimido, si la gran mayoría de bytes en chunks IDAT son constantes
    # o si se muestrean bytes de píxeles sin descomprimir exhaustivamente
    # Una imagen 1080x2400 completamente negra suele comprimir a menos de 15 KiB
    return len(png_data) < 16 * 1024


def capture_forensic_screenshot(
    runner: AdbRunner,
    store: EvidenceStore,
    seq: int,
    note: str = "",
) -> dict[str, str | int]:
    """Toma una captura de pantalla transfiriendo los bytes PNG directamente a RAM en Python.

    Calcula hashes en memoria ANTES de persistir en disco y genera metadatos contextuales.
    """
    t0 = time.monotonic()
    ts_before = datetime.now(UTC)
    cp = runner.run("exec-out", "screencap", "-p", timeout=15)
    ts_after = datetime.now(UTC)

    data = cp.stdout
    if cp.returncode != 0 or not data.startswith(PNG_SIGNATURE):
        raise ScreenshotError(
            f"Salida inválida de screencap (rc={cp.returncode}, longitud={len(data)} bytes)"
        )

    # Parsear dimensiones de cabecera IHDR
    try:
        width, height = struct.unpack(">II", data[16:24])
    except Exception:
        width, height = 0, 0

    fg_activity = get_foreground_activity(runner)
    time_tag = ts_before.strftime("%Y%m%dT%H%M%SZ")
    png_rel_path = f"screenshots/{seq:04d}_{time_tag}.png"
    json_rel_path = f"screenshots/{seq:04d}_{time_tag}.json"

    # Persistir PNG en el almacén de evidencias con hash calculado en RAM
    digests = store.put_bytes(png_rel_path, data, module="screenshot")

    # Analizar si la captura es potencialmente negra (FLAG_SECURE)
    is_black = is_black_screen(data)
    warning_flag = "FLAG_SECURE_DETECTADO" if is_black else None
    if is_black and store.logger:
        store.logger.append(
            "SCREENSHOT_WARNING",
            "screenshot",
            {"seq": seq, "reason": "Captura vacía o negra, posible protección FLAG_SECURE"},
        )

    # Metadatos forenses asociados
    metadata = {
        "sequence": seq,
        "png_file": png_rel_path,
        "size_bytes": len(data),
        "sha256": digests["sha256"],
        "sha512": digests["sha512"],
        "width": width,
        "height": height,
        "ts_before_utc": ts_before.isoformat(),
        "ts_after_utc": ts_after.isoformat(),
        "duration_seconds": round(time.monotonic() - t0, 3),
        "foreground_activity": fg_activity,
        "note": note,
        "security_warning": warning_flag,
    }

    # Guardar archivo JSON de metadatos
    store.put_bytes(
        json_rel_path,
        json.dumps(metadata, indent=2, ensure_ascii=False).encode("utf-8"),
        module="screenshot",
    )

    if store.logger:
        store.logger.append(
            "SCREENSHOT_CAPTURED",
            "screenshot",
            {
                "seq": seq,
                "file": png_rel_path,
                "sha256": digests["sha256"],
                "activity": fg_activity,
            },
        )

    return metadata
