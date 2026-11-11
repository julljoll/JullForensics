"""Definición de la interfaz base y contexto para módulos de adquisición forense."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field

from jullforensics.adb.runner import AdbRunner
from jullforensics.domain.device import DeviceInfo
from jullforensics.storage.evidence_store import EvidenceStore


class ModuleStatus(StrEnum):
    OK = "OK"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ModuleResult(BaseModel):
    """Resultado devuelto por un módulo de adquisición al finalizar su tarea."""

    module_name: str
    status: ModuleStatus
    artifacts: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0


@dataclass
class AcquisitionContext:
    """Contexto de ejecución inyectado a cada módulo extractor."""

    runner: AdbRunner
    store: EvidenceStore
    device_info: DeviceInfo
    cancel_requested: bool = False


class AcquisitionModule(ABC):
    """Clase base abstracta para todos los extractores forenses (plugins)."""

    name: str
    description: str
    order_of_volatility: int  # RFC 3227: menor número = mayor volatilidad
    intrusive: bool = False

    @abstractmethod
    def precheck(self, ctx: AcquisitionContext) -> list[str]:
        """Comprueba requisitos y retorna una lista de advertencias previas."""
        ...

    @abstractmethod
    def acquire(self, ctx: AcquisitionContext) -> ModuleResult:
        """Ejecuta la adquisición escribiendo exclusivamente a través de ctx.store."""
        ...
