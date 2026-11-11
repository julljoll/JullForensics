"""Pruebas unitarias para la herramienta de verificación forense (verify.py)."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

from jullforensics.integrity.chained_log import ChainedLog
from jullforensics.integrity.hashing import hash_bytes, hash_file
from jullforensics.integrity.signing import Signer
from jullforensics.integrity.verify import main, verify_case_directory, verify_tar_container


def test_verify_tar_container_success(tmp_path: Path) -> None:
    tar_path = tmp_path / "case_archive.tar"
    payload = b"Sample artifact evidence data for validation"
    payload_hash = hash_bytes(payload, ["sha256"])["sha256"]

    # Crear estructura interna del TAR
    with tarfile.open(tar_path, "w") as tar:
        ti_file = tarfile.TarInfo("evidence/file1.txt")
        ti_file.size = len(payload)
        tar.addfile(ti_file, io.BytesIO(payload))

        sums_text = f"{payload_hash}  evidence/file1.txt\n"
        ti_sums = tarfile.TarInfo("hashes/SHA256SUMS")
        ti_sums.size = len(sums_text)
        tar.addfile(ti_sums, io.BytesIO(sums_text.encode("utf-8")))

    # Generar sidecar externo .sha256
    tar_hash = hash_file(tar_path, ["sha256"])["sha256"]
    sidecar_path = tmp_path / "case_archive.tar.sha256"
    sidecar_path.write_text(f"{tar_hash}  case_archive.tar\n", encoding="utf-8")

    assert verify_tar_container(tar_path) == 0


def test_verify_tar_container_corrupted_sidecar(tmp_path: Path) -> None:
    tar_path = tmp_path / "bad_sidecar.tar"
    with tarfile.open(tar_path, "w"):
        pass

    sidecar_path = tmp_path / "bad_sidecar.tar.sha256"
    sidecar_path.write_text(
        "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff  bad_sidecar.tar\n"
    )

    assert verify_tar_container(tar_path) == 2


def test_verify_case_directory_success(tmp_path: Path) -> None:
    case_dir = tmp_path / "JF-2026-CASE"
    case_dir.mkdir()
    logs_dir = case_dir / "logs"
    logs_dir.mkdir()

    # 1. Crear log encadenado
    key = b"\x03" * 32
    genesis = "0" * 64
    chain_log = logs_dir / "chain.jsonl"
    logger = ChainedLog(chain_log, key, genesis, "JF-2026-CASE", "examiner")
    logger.append("START", "core", {})

    # 2. Crear manifiesto y firma
    priv, pub = Signer.generate_keypair()
    manifest_path = case_dir / "manifest.json"
    manifest_bytes = b'{"artifacts": []}'
    manifest_path.write_bytes(manifest_bytes)

    sig_path = case_dir / "manifest.sig"
    sig_path.write_bytes(Signer.sign_bytes(priv, manifest_bytes))

    pubkey_path = case_dir / "signing_pubkey.pem"
    pubkey_path.write_bytes(Signer.export_public_key_pem(pub))

    assert verify_case_directory(case_dir) == 0


def test_verify_tar_container_corrupted_member(tmp_path: Path) -> None:
    tar_path = tmp_path / "corrupt_member.tar"
    payload = b"Original data"
    bad_payload = b"Tampered data"
    payload_hash = hash_bytes(payload, ["sha256"])["sha256"]

    with tarfile.open(tar_path, "w") as tar:
        ti_file = tarfile.TarInfo("evidence/file1.txt")
        ti_file.size = len(bad_payload)
        tar.addfile(ti_file, io.BytesIO(bad_payload))

        sums_text = f"{payload_hash}  evidence/file1.txt\n"
        ti_sums = tarfile.TarInfo("hashes/SHA256SUMS")
        ti_sums.size = len(sums_text)
        tar.addfile(ti_sums, io.BytesIO(sums_text.encode("utf-8")))

    assert verify_tar_container(tar_path) == 3


def test_verify_tar_container_non_existent(tmp_path: Path) -> None:
    assert verify_tar_container(tmp_path / "does_not_exist.tar") == 1


def test_verify_case_directory_invalid_sig(tmp_path: Path) -> None:
    case_dir = tmp_path / "JF-BAD-SIG"
    case_dir.mkdir()
    (case_dir / "logs").mkdir()

    manifest_path = case_dir / "manifest.json"
    manifest_path.write_bytes(b'{"test": 1}')

    sig_path = case_dir / "manifest.sig"
    sig_path.write_bytes(b"\x00" * 64)

    _, pub = Signer.generate_keypair()
    pubkey_path = case_dir / "signing_pubkey.pem"
    pubkey_path.write_bytes(Signer.export_public_key_pem(pub))

    assert verify_case_directory(case_dir) == 3


def test_verify_case_directory_non_existent(tmp_path: Path) -> None:
    assert verify_case_directory(tmp_path / "not_a_dir") == 1


def test_verify_main_cli_dispatch(tmp_path: Path) -> None:
    # Test file that does not exist
    assert main(["/non/existent/path/file.tar"]) == 1

    # Test chain file directly
    chain_file = tmp_path / "chain.jsonl"
    key = b"\x01" * 32
    genesis = "0" * 64
    logger = ChainedLog(chain_file, key, genesis, "CASE-CLI", "user")
    logger.append("EV", "mod", {})

    assert main([str(chain_file)]) == 0

    # Test case dir dispatch
    case_dir = tmp_path / "CASE-DIR"
    case_dir.mkdir()
    assert main([str(case_dir)]) == 0

    # Test unknown format
    unknown = tmp_path / "test.unknown"
    unknown.write_text("hello")
    assert main([str(unknown)]) == 1
