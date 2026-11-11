"""Modelo de información de hardware y sistema operativo del dispositivo móvil."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DeviceInfo(BaseModel):
    """Metadatos técnicos y propiedades forenses del dispositivo Android conectado."""

    serial: str = Field(..., min_length=1)
    model: str = Field("Desconocido")
    manufacturer: str = Field("Desconocido")
    brand: str = Field("Desconocido")
    android_version: str = Field("Desconocido")
    sdk_version: int = Field(0)
    security_patch: str = Field("Desconocido")
    build_fingerprint: str = Field("Desconocido")
    build_id: str = Field("Desconocido")
    battery_level_percent: int | None = None
    clock_offset_seconds: float = 0.0
    encryption_state: str = "Desconocido"
    imei_if_accessible: str | None = None
