"""Modelos de datos para el Caso, Examinador y Base Legal (ISO/IEC 27037)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from jullforensics.domain.custody import CustodyEvent


class LegalBasisType(StrEnum):
    ORDEN_JUDICIAL = "ORDEN_JUDICIAL"
    CONSENTIMIENTO_INFORMADO = "CONSENTIMIENTO_INFORMADO"
    MANDATO_FISCAL = "MANDATO_FISCAL"
    AUDITORIA_AUTORIZADA = "AUDITORIA_AUTORIZADA"
    OTRO = "OTRO"


class LegalBasis(BaseModel):
    """Fundamento jurídico que legitima la adquisición forense."""

    type: LegalBasisType
    reference: str = Field(..., min_length=3, description="Número de oficio o expediente judicial")
    authority: str = Field(..., min_length=2, description="Juzgado o fiscalía emisora")
    date_issued: str = Field(..., description="Fecha de emisión de la orden (YYYY-MM-DD)")
    document_hash_sha256: str | None = Field(
        None, description="Hash SHA-256 del oficio/documento digital adjunto"
    )
    notes: str = ""


class Examiner(BaseModel):
    """Datos de filiación del perito o examinador informático forense."""

    name: str = Field(..., min_length=2)
    badge_or_id: str = Field(..., min_length=2, description="Identificación profesional o carnet")
    organization: str = Field(..., min_length=2, description="Cuerpo policial o laboratorio")
    email: str | None = None


class CaseStatus(StrEnum):
    OPEN = "OPEN"
    ACQUIRING = "ACQUIRING"
    COMPLETED = "COMPLETED"
    SEALED = "SEALED"
    CLOSED = "CLOSED"


class Case(BaseModel):
    """Entidad principal que representa una investigación o actuación pericial."""

    case_id: str = Field(
        ...,
        pattern=r"^[A-Z0-9_\-]+$",
        description="Identificador único del caso (ej. JF-2026-0001)",
    )
    title: str = Field(..., min_length=3)
    docket_number: str = Field(..., min_length=2, description="Número de sumario o causa penal")
    agency: str = Field(..., min_length=2, description="Organismo solicitante")
    examiner: Examiner
    legal_basis: LegalBasis
    device_description: str = Field("", description="Descripción física del terminal")
    created_at_utc: str = Field(
        default_factory=lambda: (
            datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
        )
    )
    status: CaseStatus = CaseStatus.OPEN
    chain_of_custody: list[CustodyEvent] = Field(default_factory=list)
