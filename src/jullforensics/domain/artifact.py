"""Modelo de artefacto forense adquirido."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ArtifactStatus(StrEnum):
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    INCOMPLETE = "INCOMPLETE"
    CORRUPTED = "CORRUPTED"


class Artifact(BaseModel):
    """Representa un archivo de evidencia adquirido con sus resúmenes criptográficos."""

    relative_path: str = Field(..., description="Ruta relativa dentro del contenedor del caso")
    size_bytes: int = Field(..., ge=0)
    sha256: str = Field(..., min_length=64, max_length=64)
    sha512: str = Field(..., min_length=128, max_length=128)
    module: str = Field(..., description="Módulo extractor responsable")
    device_mtime_utc: str | None = None
    acquired_at_utc: str
    status: ArtifactStatus = ArtifactStatus.VERIFIED
    notes: str = ""
