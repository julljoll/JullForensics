"""Pruebas unitarias para almacenamiento, sanitización anti-tar-slip y contenedor JF-TAR."""

from __future__ import annotations

import tarfile
from pathlib import Path

import pytest

from jullforensics.domain.case import Case, Examiner, LegalBasis, LegalBasisType
from jullforensics.integrity.chained_log import ChainedLog
from jullforensics.integrity.signing import Signer
from jullforensics.storage.evidence_store import EvidenceStore
from jullforensics.storage.name_sanitizer import (
    PathTraversalSecurityError,
    sanitize_relative_path,
)
from jullforensics.storage.tar_container import create_forensic_tar


@pytest.fixture
def dummy_case() -> Case:
    return Case(
        case_id="JF-2026-STORE",
        title="Test Case Storage",
        docket_number="DOCK-001",
        agency="Lab",
        examiner=Examiner(name="Perito", badge_or_id="ID1", organization="Org"),
        legal_basis=LegalBasis(
            type=LegalBasisType.ORDEN_JUDICIAL,
            reference="ORD-01",
            authority="Juzgado",
            date_issued="2026-01-01",
        ),
    )


@pytest.fixture
def dummy_store(tmp_path: Path, dummy_case: Case) -> EvidenceStore:
    case_dir = tmp_path / "case_dir"
    log_file = case_dir / "logs" / "chain.jsonl"
    logger = ChainedLog(log_file, b"\x01" * 32, "0" * 64, dummy_case.case_id, "examiner")
    return EvidenceStore(case_dir, dummy_case, logger)


def test_sanitize_relative_path_normal() -> None:
    assert sanitize_relative_path("DCIM/Camera/IMG_01.jpg") == "DCIM/Camera/IMG_01.jpg"
    assert sanitize_relative_path("/storage/emulated/0/file.txt") == "storage/emulated/0/file.txt"


def test_sanitize_relative_path_blocks_traversal() -> None:
    with pytest.raises(PathTraversalSecurityError, match="Tar-Slip"):
        sanitize_relative_path("../../../etc/shadow")

    with pytest.raises(PathTraversalSecurityError, match="Tar-Slip"):
        sanitize_relative_path("DCIM/../../etc/passwd")


def test_sanitize_relative_path_blocks_control_chars() -> None:
    with pytest.raises(PathTraversalSecurityError, match="caracteres de control"):
        sanitize_relative_path("file\x00malicious.png")


def test_evidence_store_put_bytes_and_sums(dummy_store: EvidenceStore) -> None:
    data1 = b"Sample Evidence Data 1"
    digests1 = dummy_store.put_bytes("evidence/sdcard/doc1.txt", data1, module="test_mod")

    assert "sha256" in digests1
    assert len(dummy_store.artifacts) == 1

    manifest_path = dummy_store.generate_manifest_and_sums()
    assert manifest_path.is_file()

    sha256sums_path = dummy_store.base_dir / "SHA256SUMS"
    assert sha256sums_path.is_file()
    assert digests1["sha256"] in sha256sums_path.read_text(encoding="utf-8")


def test_create_forensic_tar_container(dummy_store: EvidenceStore) -> None:
    dummy_store.put_bytes("evidence/sample.txt", b"Artifact Content", module="test")
    priv, _ = Signer.generate_keypair()

    tar_path, digests = create_forensic_tar(
        store=dummy_store,
        serial="SM-A54",
        private_key=priv,
    )

    assert tar_path.is_file()
    assert "sha256" in digests

    # Verificar que existen los sidecars externos
    sidecar_sha256 = tar_path.with_suffix(".tar.sha256")
    assert sidecar_sha256.is_file()
    assert digests["sha256"] in sidecar_sha256.read_text(encoding="utf-8")

    # Inspeccionar interior del TAR
    with tarfile.open(tar_path, "r") as tar:
        names = tar.getnames()
        assert any(n.endswith("00_LEEME.txt") for n in names)
        assert any(n.endswith("evidence/sample.txt") for n in names)
        assert any(n.endswith("hashes/manifest.json") for n in names)
        assert any(n.endswith("hashes/manifest.sig") for n in names)
        assert any(n.endswith("hashes/SHA256SUMS") for n in names)


def test_evidence_store_seal_case(dummy_store: EvidenceStore) -> None:
    dummy_store.put_bytes("evidence/sealed_file.txt", b"Permanent Evidence", module="test")
    dummy_store.seal_case()

    f = dummy_store.base_dir / "evidence" / "sealed_file.txt"
    mode = f.stat().st_mode & 0o777
    assert mode == 0o440
