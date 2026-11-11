"""Pruebas unitarias para modelos de dominio de caso, examinador, base legal y custodia."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from jullforensics.domain.artifact import Artifact, ArtifactStatus
from jullforensics.domain.case import Case, CaseStatus, Examiner, LegalBasis, LegalBasisType
from jullforensics.domain.custody import CustodyEvent, CustodyEventType
from jullforensics.domain.device import DeviceInfo


def test_valid_case_creation() -> None:
    examiner = Examiner(
        name="Elena García",
        badge_or_id="PER-9821",
        organization="Laboratorio Central de Criminalística",
        email="elena.garcia@forense.org",
    )
    legal_basis = LegalBasis(
        type=LegalBasisType.ORDEN_JUDICIAL,
        reference="AUTO-2026-104",
        authority="Juzgado de Instrucción nº 4",
        date_issued="2026-11-10",
        document_hash_sha256="a" * 64,
    )
    case = Case(
        case_id="JF-2026-0001",
        title="Diligencias Previas 45/26",
        docket_number="DP-45-2026",
        agency="Policía Judicial",
        examiner=examiner,
        legal_basis=legal_basis,
        device_description="Samsung Galaxy A54 negro con funda de silicona",
    )

    assert case.status == CaseStatus.OPEN
    assert case.case_id == "JF-2026-0001"
    assert case.examiner.name == "Elena García"


def test_case_id_pattern_validation() -> None:
    examiner = Examiner(name="Perito", badge_or_id="123", organization="Lab")
    legal = LegalBasis(
        type=LegalBasisType.ORDEN_JUDICIAL,
        reference="123",
        authority="Juzgado",
        date_issued="2026-01-01",
    )

    with pytest.raises(ValidationError):
        Case(
            case_id="CASO CON ESPACIOS Y PUNTOS..",
            title="Titulo",
            docket_number="123",
            agency="Org",
            examiner=examiner,
            legal_basis=legal,
        )


def test_device_info_model() -> None:
    dev = DeviceInfo(
        serial="R58W123ABC",
        model="SM-A546E",
        manufacturer="samsung",
        brand="samsung",
        android_version="14",
        sdk_version=34,
        battery_level_percent=85,
    )
    assert dev.serial == "R58W123ABC"
    assert dev.sdk_version == 34


def test_custody_event() -> None:
    ev = CustodyEvent(
        event_id="CUST-001",
        event_type=CustodyEventType.EVIDENCE_RECEIVED,
        actor="Guardia de Custodia",
        action_description="Recepción de sobre sellado con terminal móvil",
        location="Depósito de Efectos Judiciales",
        evidence_hash_sha256="b" * 64,
    )
    assert ev.event_type == CustodyEventType.EVIDENCE_RECEIVED
    assert len(ev.evidence_hash_sha256) == 64


def test_artifact_model() -> None:
    art = Artifact(
        relative_path="evidence/sdcard/DCIM/IMG_01.jpg",
        size_bytes=2048,
        sha256="c" * 64,
        sha512="d" * 128,
        module="shared_storage",
        acquired_at_utc="2026-11-11T12:00:00Z",
        status=ArtifactStatus.VERIFIED,
    )
    assert art.size_bytes == 2048
    assert art.status == ArtifactStatus.VERIFIED
