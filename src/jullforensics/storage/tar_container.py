"""Empaquetador streaming de contenedor forense JF-TAR con resúmenes y sidecars."""

from __future__ import annotations

import io
import os
import tarfile
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

from jullforensics.integrity.hashing import MultiHasher, hash_file
from jullforensics.integrity.signing import Signer

if TYPE_CHECKING:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from jullforensics.storage.evidence_store import EvidenceStore


class HashingWriter(io.RawIOBase):
    """Escribe los bytes al archivo real y actualiza simultáneamente el hasher del TAR completo."""

    def __init__(self, fh: BinaryIO, hasher: MultiHasher) -> None:
        self._fh = fh
        self.hasher = hasher

    def writable(self) -> bool:
        return True

    def write(self, b: bytes | bytearray | memoryview) -> int:  # type: ignore[override]
        n = self._fh.write(b)
        self.hasher.update(bytes(memoryview(b)[:n]))
        return n


class HashingReader(io.RawIOBase):
    """Calcula el hash de cada miembro individual mientras tarfile lo copia al contenedor."""

    def __init__(self, src: BinaryIO, hasher: MultiHasher) -> None:
        self._src = src
        self.hasher = hasher
        self.bytes_read = 0

    def readable(self) -> bool:
        return True

    def read(self, n: int = -1) -> bytes:
        chunk = self._src.read(n)
        self.bytes_read += len(chunk)
        self.hasher.update(chunk)
        return chunk


def create_forensic_tar(
    store: EvidenceStore,
    serial: str = "DEVICE",
    output_dir: Path | str | None = None,
    private_key: Ed25519PrivateKey | None = None,
    algos: Iterable[str] = ("sha256", "sha512"),
) -> tuple[Path, dict[str, str]]:
    """Empaqueta toda la evidencia de un caso en un contenedor JF-TAR en una sola pasada.

    Genera:
      1. Contenedor POSIX PAX con estructura interna.
      2. Hashes integrados dentro del TAR (SHA256SUMS, SHA512SUMS, manifest.json, manifest.sig).
      3. Sidecars externos (.tar.sha256, .tar.sha512, .tar.sig).
      4. Re-verificación leyendo del disco al finalizar.
    """
    out_dir = Path(output_dir) if output_dir else store.export_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    now_tag = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    base_name = f"{store.case.case_id}_{serial}_{now_tag}"
    final_tar_path = out_dir / f"{base_name}.tar"
    part_tar_path = out_dir / f"{base_name}.tar.part"

    tar_hasher = MultiHasher(algos)
    root_folder = base_name

    # Generar manifiesto actualizado antes de empaquetar
    store.generate_manifest_and_sums()

    with part_tar_path.open("wb") as raw_fh:
        hashing_writer = HashingWriter(raw_fh, tar_hasher)
        with tarfile.open(fileobj=hashing_writer, mode="w|", format=tarfile.PAX_FORMAT) as tar:
            # 1. Añadir 00_LEEME.txt
            readme_text = (
                f"JullForensics - Contenedor Forense JF-TAR\n"
                f"Caso: {store.case.case_id}\n"
                f"Dispositivo: {serial}\n"
                f"Sellado (UTC): {now_tag}\n\n"
                f"Instrucciones de verificación:\n"
                f"1. Integridad del contenedor: sha256sum -c {base_name}.tar.sha256\n"
                f"2. Extracción: tar -xf {base_name}.tar\n"
                f"3. Integridad de miembros: cd {base_name} && sha256sum -c hashes/SHA256SUMS\n"
            )
            ti_readme = tarfile.TarInfo(f"{root_folder}/00_LEEME.txt")
            ti_readme.size = len(readme_text.encode("utf-8"))
            tar.addfile(ti_readme, io.BytesIO(readme_text.encode("utf-8")))

            # 2. Añadir evidencia física en disco
            for artifact in store.artifacts:
                art_file = store.base_dir / artifact.relative_path
                if art_file.is_file():
                    stat_info = art_file.stat()
                    ti = tarfile.TarInfo(f"{root_folder}/{artifact.relative_path}")
                    ti.size = stat_info.st_size
                    ti.mtime = int(stat_info.st_mtime)
                    ti.mode = stat_info.st_mode & 0o777

                    with art_file.open("rb") as f_in:
                        tar.addfile(ti, f_in)

            # 3. Añadir hashes y manifiesto dentro del tar
            for sums_file_name in ("SHA256SUMS", "SHA512SUMS", "manifest.json"):
                f_path = store.base_dir / sums_file_name
                if f_path.is_file():
                    data = f_path.read_bytes()
                    ti = tarfile.TarInfo(f"{root_folder}/hashes/{sums_file_name}")
                    ti.size = len(data)
                    tar.addfile(ti, io.BytesIO(data))

            # 4. Firma digital Ed25519 del manifiesto si se proveyó clave
            if private_key:
                manifest_bytes = (store.base_dir / "manifest.json").read_bytes()
                sig_bytes = Signer.sign_bytes(private_key, manifest_bytes)
                ti_sig = tarfile.TarInfo(f"{root_folder}/hashes/manifest.sig")
                ti_sig.size = len(sig_bytes)
                tar.addfile(ti_sig, io.BytesIO(sig_bytes))

                pubkey_pem = Signer.export_public_key_pem(private_key.public_key())
                ti_pub = tarfile.TarInfo(f"{root_folder}/hashes/signing_pubkey.pem")
                ti_pub.size = len(pubkey_pem)
                tar.addfile(ti_pub, io.BytesIO(pubkey_pem))

            # 5. Añadir log encadenado
            chain_path = store.base_dir / "logs" / "chain.jsonl"
            if chain_path.is_file():
                chain_bytes = chain_path.read_bytes()
                ti_log = tarfile.TarInfo(f"{root_folder}/logs/chain.jsonl")
                ti_log.size = len(chain_bytes)
                tar.addfile(ti_log, io.BytesIO(chain_bytes))

        raw_fh.flush()
        os.fsync(raw_fh.fileno())

    # Renombrado atómico de .part a .tar
    part_tar_path.rename(final_tar_path)
    final_tar_path.chmod(0o440)

    # Hashes calculados en streaming durante la creación
    tar_digests = tar_hasher.hexdigests()

    # Escribir sidecars externos
    sidecar_sha256 = out_dir / f"{base_name}.tar.sha256"
    sidecar_sha256.write_text(f"{tar_digests['sha256']}  {base_name}.tar\n", encoding="utf-8")
    sidecar_sha256.chmod(0o440)

    if "sha512" in tar_digests:
        sidecar_sha512 = out_dir / f"{base_name}.tar.sha512"
        sidecar_sha512.write_text(f"{tar_digests['sha512']}  {base_name}.tar\n", encoding="utf-8")
        sidecar_sha512.chmod(0o440)

    if private_key:
        tar_sig = Signer.sign_bytes(private_key, final_tar_path.read_bytes())
        sidecar_sig = out_dir / f"{base_name}.tar.sig"
        sidecar_sig.write_bytes(tar_sig)
        sidecar_sig.chmod(0o440)

    # Re-verificación leyendo desde el disco
    disk_digests = hash_file(final_tar_path, algos)
    if disk_digests["sha256"] != tar_digests["sha256"]:
        raise ValueError(
            "Discrepancia en re-verificación de hash del contenedor TAR recién escrito."
        )

    store.logger.append(
        "PACKAGE_SEALED",
        "storage",
        {
            "tar_file": final_tar_path.name,
            "size_bytes": final_tar_path.stat().st_size,
            "sha256": tar_digests["sha256"],
            "sha512": tar_digests.get("sha512"),
            "sidecar": sidecar_sha256.name,
        },
    )

    return final_tar_path, tar_digests
