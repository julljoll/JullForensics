"""Modelo de información de hardware y sistema operativo del dispositivo móvil."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DeviceInfo(BaseModel):
    """Metadatos técnicos y propiedades forenses del dispositivo Android conectado."""

    serial: str = Field(..., min_length=1)
    model: str = "Desconocido"
    manufacturer: str = "Desconocido"
    brand: str = "Desconocido"
    android_version: str = "Desconocido"
    sdk_version: int = 0
    security_patch: str = "Desconocido"
    build_fingerprint: str = "Desconocido"
    build_id: str = "Desconocido"
    battery_level_percent: int | None = None
    clock_offset_seconds: float = 0.0
    encryption_state: str = "Desconocido"
    imei_if_accessible: str | None = None
