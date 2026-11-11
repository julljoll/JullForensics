"""Hilo de trabajo (QThread) para ejecución asíncrona de la adquisición forense."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from PySide6.QtCore import QThread, Signal

if TYPE_CHECKING:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from jullforensics.acquisition.base import ModuleResult
    from jullforensics.domain.case import Case
    from jullforensics.domain.device import DeviceInfo
    from jullforensics.services.acquisition_service import (
        AcquisitionService,
        AcquisitionSummary,
        ProfileType,
    )


class AcquisitionWorker(QThread):
    """Ejecuta la adquisición forense en segundo plano sin congelar la interfaz gráfica."""

    progress_updated = Signal(str, float, str)  # modulo, porcentaje, mensaje
    module_started = Signal(str, int, int)  # modulo, indice, total
    module_finished = Signal(str, object)  # modulo, ModuleResult
    acquisition_finished = Signal(object)  # AcquisitionSummary
    error_occurred = Signal(str)  # mensaje de error

    def __init__(
        self,
        service: AcquisitionService,
        case: Case,
        device: DeviceInfo,
        profile: ProfileType,
        custom_modules: list[str] | None = None,
        private_key: Ed25519PrivateKey | None = None,
    ) -> None:
        super().__init__()
        self.service = service
        self.case = case
        self.device = device
        self.profile = profile
        self.custom_modules = custom_modules
        self.private_key = private_key
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        """Solicita la cancelación segura y ordenada de la adquisición."""
        self._cancel_event.set()

    def run(self) -> None:
        """Punto de entrada del hilo de trabajo."""
        try:
            summary: AcquisitionSummary = self.service.run_acquisition(
                case=self.case,
                device=self.device,
                profile=self.profile,
                custom_modules=self.custom_modules,
                private_key=self.private_key,
                cancel_event=self._cancel_event,
                on_start_cb=self._on_start,
                on_progress_cb=self._on_progress,
                on_complete_cb=self._on_complete,
            )
            self.acquisition_finished.emit(summary)
        except Exception as exc:  # noqa: BLE001
            self.error_occurred.emit(str(exc))

    def _on_start(self, module_name: str, current_idx: int, total: int) -> None:
        self.module_started.emit(module_name, current_idx, total)

    def _on_progress(self, module_name: str, pct: float, message: str) -> None:
        self.progress_updated.emit(module_name, pct, message)

    def _on_complete(self, module_name: str, result: ModuleResult) -> None:
        self.module_finished.emit(module_name, result)
