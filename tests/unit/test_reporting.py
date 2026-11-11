"""Pruebas unitarias para generación de dictámenes periciales (JSON, HTML, PDF)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jullforensics.domain.case import Case, Examiner, LegalBasis, LegalBasisType
from jullforensics.domain.custody import CustodyEvent, CustodyEventType
from jullforensics.domain.device import DeviceInfo
from jullforensics.integrity.chained_log import ChainedLog
from jullforensics.reporting.html_report import generate_html_report
from jullforensics.reporting.json_report import generate_json_report
from jullforensics.reporting.pdf_report import generate_pdf_report
from jullforensics.reporting.report_generator import ReportGenerator
from jullforensics.storage.evidence_store import EvidenceStore


@pytest.fixture
def sample_case() -> Case:
    examiner = Examiner(
        name="Carlos Mendoza",
        badge_or_id="PER-4091",
        organization="Laboratorio de Policía Científica",
        email="cmendoza@policia.gob",
    )
    legal_basis = LegalBasis(
        type=LegalBasisType.ORDEN_JUDICIAL,
        reference="AUTO-2026-9912",
        authority="Juzgado Central de Instrucción nº 2",
        date_issued="2026-11-01",
        document_hash_sha256="b" * 64,
        notes="Autorización de clonado y extracción lógica integral",
    )
    case = Case(
        case_id="JF-2026-8801",
        title="Operación Centinela Digital",
        docket_number="DIL-450-2026",
        agency="Policía Nacional",
        examiner=examiner,
        legal_basis=legal_basis,
        device_description="Terminal Google Pixel 7 negro con cristal templado",
    )
    event1 = CustodyEvent(
        event_id="evt-1",
        event_type=CustodyEventType.EVIDENCE_RECEIVED,
        actor="Carlos Mendoza",
        action_description="Recepción de terminal en bolsa de Faraday precintada",
        location="Laboratorio Central",
        evidence_hash_sha256="c" * 64,
    )
    case.chain_of_custody.append(event1)
    return case


@pytest.fixture
def sample_device() -> DeviceInfo:
    return DeviceInfo(
        serial="HT87B1A00123",
        model="Pixel 7",
        manufacturer="Google",
        brand="google",
        android_version="14",
        sdk_version=34,
        security_patch="2026-10-05",
        build_fingerprint="google/panther/panther:14/UQ1A.240105.004:user/release-keys",
        build_id="UQ1A.240105.004",
        battery_level_percent=88,
        clock_offset_seconds=-0.12,
        encryption_state="encrypted",
    )


@pytest.fixture
def prepared_store(tmp_path: Path, sample_case: Case) -> EvidenceStore:
    log_path = tmp_path / "test.jsonl"
    logger = ChainedLog(log_path, key=b"test-hmac-key-32-bytes-minimum!!")
    store = EvidenceStore(tmp_path / "case_dir", sample_case, logger)
    store.put_bytes("evidence/props/build.prop", b"ro.build.version.release=14\n", "device_props")
    store.put_bytes("evidence/packages/packages.txt", b"package:com.android.shell\n", "packages")
    return store


def test_generate_json_report(
    sample_case: Case, sample_device: DeviceInfo, prepared_store: EvidenceStore
) -> None:
    json_str = generate_json_report(
        sample_case,
        sample_device,
        prepared_store,
        tar_info={"file": "test.tar", "sha256": "1" * 64},
    )
    data = json.loads(json_str)

    assert data["case"]["case_id"] == "JF-2026-8801"
    assert data["device"]["serial"] == "HT87B1A00123"
    assert len(data["artifacts"]) == 2
    assert len(data["chain_of_custody"]) == 1
    assert data["integrity"]["total_artifacts"] == 2
    assert data["tar_container"]["file"] == "test.tar"


def test_generate_html_report(
    sample_case: Case, sample_device: DeviceInfo, prepared_store: EvidenceStore
) -> None:
    html_str = generate_html_report(
        sample_case,
        sample_device,
        prepared_store,
        tar_info={"file": "test.tar", "sha256": "1" * 64},
    )

    assert "<!DOCTYPE html>" in html_str
    assert "JF-2026-8801" in html_str
    assert "HT87B1A00123" in html_str
    assert "Carlos Mendoza" in html_str
    assert "evidence/props/build.prop" in html_str
    assert "sha256sum -c SHA256SUMS" in html_str
    assert "ISO/IEC 27037:2012" in html_str


def test_generate_pdf_report(
    sample_case: Case, sample_device: DeviceInfo, prepared_store: EvidenceStore
) -> None:
    pdf_bytes = generate_pdf_report(
        sample_case,
        sample_device,
        prepared_store,
        tar_info={"file": "test.tar", "sha256": "1" * 64},
    )

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 2000


def test_report_generator_generates_all(
    sample_case: Case, sample_device: DeviceInfo, prepared_store: EvidenceStore
) -> None:
    generator = ReportGenerator(sample_case, sample_device, prepared_store)
    results = generator.generate_all(tar_info={"file": "test.tar", "sha256": "1" * 64})

    assert "json" in results
    assert "html" in results
    assert "pdf" in results

    assert (prepared_store.base_dir / "reports" / "report.json").is_file()
    assert (prepared_store.base_dir / "reports" / "report.html").is_file()
    assert (prepared_store.base_dir / "reports" / "report.pdf").is_file()

    # Verificar que los reportes fueron registrados como artefactos forenses
    report_artifacts = [
        a for a in prepared_store.artifacts if a.relative_path.startswith("reports/")
    ]
    assert len(report_artifacts) == 3
