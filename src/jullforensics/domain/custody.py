"""Eventos formales de Cadena de Custodia (ISO/IEC 27037 / ISO/IEC 17025)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class CustodyEventType(StrEnum):
    EVIDENCE_RECEIVED = "EVIDENCE_RECEIVED"
    CASE_INITIALIZED = "CASE_INITIALIZED"
    EXTRACTION_STARTED = "EXTRACTION_STARTED"
    EXTRACTION_COMPLETED = "EXTRACTION_COMPLETED"
    CONTAINER_SEALED = "CONTAINER_SEALED"
    EVIDENCE_TRANSFERRED = "EVIDENCE_TRANSFERRED"
    EXAMINATION_CONCLUDED = "EXAMINATION_CONCLUDED"


class CustodyEvent(BaseModel):
    """Registro inalterable de un hito en la cadena de custodia de la evidencia."""

    event_id: str
    ts_utc: str = Field(
        default_factory=lambda: (
            datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
        )
    )
    event_type: CustodyEventType
    actor: str = Field(..., description="Nombre e identificación de quien ejecuta la acción")
    action_description: str = Field(..., min_length=5)
    location: str = Field(..., description="Laboratorio, juzgado o sede pericial")
    evidence_hash_sha256: str = Field(
        ..., description="Hash del artefacto o contenedor en este hito"
    )
    notes: str = ""
