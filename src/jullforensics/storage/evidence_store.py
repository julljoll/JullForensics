"""Almacén central de evidencias forenses con control de integridad en streaming."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, BinaryIO

from jullforensics.domain.artifact import Artifact, ArtifactStatus
from jullforensics.domain.case import Case
from jullforensics.integrity.chained_log import ChainedLog
from jullforensics.integrity.hashing import MultiHasher, hash_bytes, tee_stream
from jullforensics.storage.name_sanitizer import sanitize_relative_path

DEFAULT_HASH_ALGOS: tuple[str, ...] = ("sha256", "sha512")


class EvidenceStore:
    """Gestiona el almacenamiento seguro y persistencia de evidencias con hashes en vuelo."""

    def __init__(self, base_dir: Path | str, case: Case, logger: ChainedLog) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.case = case
        self.logger = logger
        self.artifacts: list[Artifact] = []

        # Crear estructura de subdirectorios
        self.evidence_dir = self.base_dir / "evidence"
        self.screenshots_dir = self.base_dir / "screenshots"
        self.logs_dir = self.base_dir / "logs"
        self.export_dir = self.base_dir / "export"
        self.custody_dir = self.base_dir / "custody"

        for d in (
            self.evidence_dir,
            self.screenshots_dir,
            self.logs_dir,
            self.export_dir,
            self.custody_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)
            d.chmod(0o750)

        # Guardar case.json inicial
        self._save_case_metadata()

    def _save_case_metadata(self) -> None:
        case_file = self.base_dir / "case.json"
        case_data = self.case.model_dump_json(indent=2)
        case_file.write_text(case_data, encoding="utf-8")
        case_file.chmod(0o640)

    def put_bytes(
        self,
        rel_path: str,
        data: bytes,
        module: str,
        algos: Iterable[str] = DEFAULT_HASH_ALGOS,
    ) -> dict[str, str]:
        """Calcula los resúmenes en memoria ANTES de persistir a disco y registra el artefacto."""
        sanitized_rel = sanitize_relative_path(rel_path)
        dest_path = self.base_dir / sanitized_rel
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        digests = hash_bytes(data, algos)
        dest_path.write_bytes(data)
        dest_path.chmod(0o640)

        self._record_artifact(sanitized_rel, len(data), digests, module)
        return digests

    def put_file(
        self,
        rel_path: str,
        src_path: Path | str,
        module: str,
        algos: Iterable[str] = DEFAULT_HASH_ALGOS,
    ) -> dict[str, str]:
        """Copia un archivo local al almacén de evidencias calculando hashes en streaming."""
        sanitized_rel = sanitize_relative_path(rel_path)
        dest_path = self.base_dir / sanitized_rel
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        src = Path(src_path)
        hasher = MultiHasher(algos)
        with src.open("rb") as f_src, dest_path.open("wb") as f_dst:
            total_bytes = tee_stream(f_src, f_dst, hasher)

        dest_path.chmod(0o640)
        digests = hasher.hexdigests()
        self._record_artifact(sanitized_rel, total_bytes, digests, module)
        return digests

    def write_stream(
        self,
        rel_path: str,
        stream: BinaryIO | IO[bytes],
        module: str,
        algos: Iterable[str] = DEFAULT_HASH_ALGOS,
    ) -> dict[str, str]:
        """Escribe un flujo entrante (ej. de adb) al disco calculando hashes simultáneamente."""
        sanitized_rel = sanitize_relative_path(rel_path)
        dest_path = self.base_dir / sanitized_rel
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        hasher = MultiHasher(algos)
        with dest_path.open("wb") as f_dst:
            total_bytes = tee_stream(stream, f_dst, hasher)

        dest_path.chmod(0o640)
        digests = hasher.hexdigests()
        self._record_artifact(sanitized_rel, total_bytes, digests, module)
        return digests

    def _record_artifact(
        self,
        rel_path: str,
        size_bytes: int,
        digests: dict[str, str],
        module: str,
    ) -> None:
        now_utc = datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")

        artifact = Artifact(
            relative_path=rel_path,
            size_bytes=size_bytes,
            sha256=digests.get("sha256", ""),
            sha512=digests.get("sha512", ""),
            module=module,
            acquired_at_utc=now_utc,
            status=ArtifactStatus.VERIFIED,
        )
        self.artifacts.append(artifact)

        # Notificar en el log encadenado
        self.logger.append(
            "ARTIFACT_ACQUIRED",
            module,
            {
                "path": rel_path,
                "size_bytes": size_bytes,
                "sha256": digests.get("sha256"),
                "sha512": digests.get("sha512"),
            },
        )

    def generate_manifest_and_sums(self) -> Path:
        """Genera manifest.json, SHA256SUMS y SHA512SUMS en el caso."""
        manifest_file = self.base_dir / "manifest.json"
        manifest_data = {
            "case_id": self.case.case_id,
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "total_artifacts": len(self.artifacts),
            "artifacts": [a.model_dump() for a in self.artifacts],
        }
        manifest_file.write_text(
            json.dumps(manifest_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        manifest_file.chmod(0o640)

        # Generar archivos de sumas compatibles con sha256sum y sha512sum
        sha256_lines = [f"{a.sha256}  {a.relative_path}\n" for a in self.artifacts if a.sha256]
        (self.base_dir / "SHA256SUMS").write_text("".join(sha256_lines), encoding="utf-8")
        (self.base_dir / "SHA256SUMS").chmod(0o640)

        sha512_lines = [f"{a.sha512}  {a.relative_path}\n" for a in self.artifacts if a.sha512]
        (self.base_dir / "SHA512SUMS").write_text("".join(sha512_lines), encoding="utf-8")
        (self.base_dir / "SHA512SUMS").chmod(0o640)

        self.logger.append(
            "MANIFEST_CREATED",
            "storage",
            {"total_artifacts": len(self.artifacts), "manifest": "manifest.json"},
        )
        return manifest_file

    def seal_case(self) -> None:
        """Aplica permisos de solo lectura (0440) para preservación forense."""
        for root, dirs, files in os.walk(self.base_dir):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o750)  # noqa: S103 # nosec B103
            for f in files:
                os.chmod(os.path.join(root, f), 0o440)
