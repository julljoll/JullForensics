"""Ventana principal (MainWindow) de JullForensics con diseño brutalista integral."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from jullforensics.acquisition.screenshot import capture_forensic_screenshot
from jullforensics.adb.device_monitor import DeviceMonitor
from jullforensics.adb.device_probe import DeviceProbe
from jullforensics.adb.runner import AdbRunner
from jullforensics.domain.device import DeviceInfo
from jullforensics.integrity.chained_log import ChainedLog
from jullforensics.integrity.keys import derive_case_key
from jullforensics.reporting.report_generator import ReportGenerator
from jullforensics.services.acquisition_service import AcquisitionService, ProfileType
from jullforensics.storage.evidence_store import EvidenceStore
from jullforensics.ui.adapters.device_signals import DeviceSignalsBridge
from jullforensics.ui.adapters.worker import AcquisitionWorker
from jullforensics.ui.views.acquisition_view import AcquisitionView
from jullforensics.ui.views.case_view import CaseView
from jullforensics.ui.views.custody_view import CustodyView
from jullforensics.ui.views.device_view import DeviceView
from jullforensics.ui.views.integrity_view import IntegrityView
from jullforensics.ui.views.report_view import ReportView
from jullforensics.ui.views.screenshot_view import ScreenshotView
from jullforensics.ui.widgets.log_ticker import LogTicker
from jullforensics.ui.widgets.status_badge import StatusBadge

if TYPE_CHECKING:
    from jullforensics.acquisition.base import ModuleResult
    from jullforensics.domain.case import Case
    from jullforensics.services.acquisition_service import AcquisitionSummary


class MainWindow(QMainWindow):
    """Ventana principal que coordina vistas, monitor de dispositivos y auditoría."""

    def __init__(
        self,
        base_dir: Path | str | None = None,
        adb_path: Path | str | None = None,
        start_monitor: bool = True,
    ) -> None:
        super().__init__()
        self.setWindowTitle("JULLFORENSICS // EXTRACCIÓN LÓGICA ANDROID // ISO 27037")
        self.resize(1180, 820)
        self.setMinimumSize(960, 680)

        self._base_dir = Path(base_dir) if base_dir else Path.home() / "JullForensics_Cases"
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._adb_path = adb_path
        self._start_monitor = start_monitor

        self._active_device: DeviceInfo | None = None
        self._store: EvidenceStore | None = None
        self._runner: AdbRunner | None = None
        self._service: AcquisitionService | None = None
        self._worker: AcquisitionWorker | None = None
        self._monitor: DeviceMonitor | None = None
        self._screenshot_counter = 0

        self._setup_ui()
        self._setup_shortcuts()
        self._init_subsystems()

    def _setup_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 12, 12, 8)
        root_layout.setSpacing(10)

        # 1. Cabecera superior brutalista
        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_app = QLabel("JULLFORENSICS v0.1.0")
        lbl_app.setStyleSheet(
            "font-size: 18px; font-weight: 900; letter-spacing: -0.5px; color: #0A0A0A;"
        )
        lbl_sub = QLabel("EXTRACCIÓN LÓGICA ANDROID | CONFORMIDAD ISO/IEC 27037 / RFC 3227")
        lbl_sub.setStyleSheet("font-size: 11px; font-weight: bold; color: #555555;")
        title_box.addWidget(lbl_app)
        title_box.addWidget(lbl_sub)
        top_bar.addLayout(title_box, stretch=1)

        self._badge = StatusBadge()
        top_bar.addWidget(self._badge, stretch=0)
        root_layout.addLayout(top_bar)

        # 2. Pestañas de las 7 vistas
        self._tabs = QTabWidget()
        self._case_view = CaseView()
        self._device_view = DeviceView()
        self._screenshot_view = ScreenshotView()
        self._acquisition_view = AcquisitionView()
        self._integrity_view = IntegrityView()
        self._report_view = ReportView()
        self._custody_view = CustodyView()

        self._tabs.addTab(self._case_view, "[01 CASO]")
        self._tabs.addTab(self._device_view, "[02 DISPOSITIVO]")
        self._tabs.addTab(self._screenshot_view, "[03 PANTALLAS]")
        self._tabs.addTab(self._acquisition_view, "[04 EXTRACCIÓN]")
        self._tabs.addTab(self._integrity_view, "[05 INTEGRIDAD]")
        self._tabs.addTab(self._report_view, "[06 DICTAMEN]")
        self._tabs.addTab(self._custody_view, "[07 CUSTODIA]")

        root_layout.addWidget(self._tabs, stretch=1)

        # 3. Barra inferior de auditoría (LogTicker)
        self._ticker = LogTicker()
        root_layout.addWidget(self._ticker, stretch=0)

        # Conectar señales entre vistas
        self._case_view.case_saved.connect(self._on_case_saved)
        self._device_view.probe_requested.connect(self._on_manual_probe)
        self._screenshot_view.capture_requested.connect(self._on_screenshot_requested)
        self._acquisition_view.start_requested.connect(self._on_start_acquisition)
        self._acquisition_view.cancel_requested.connect(self._on_cancel_acquisition)
        self._report_view.generate_requested.connect(self._on_generate_reports)

    def _setup_shortcuts(self) -> None:
        # Atajos de teclado Alt+1 a Alt+7 para navegación
        for idx in range(7):
            act = QAction(self)
            act.setShortcut(QKeySequence(f"Alt+{idx + 1}"))
            act.triggered.connect(lambda _, i=idx: self._tabs.setCurrentIndex(i))
            self.addAction(act)

        # Atajo global F12 para captura de pantalla forense
        act_f12 = QAction(self)
        act_f12.setShortcut(QKeySequence(Qt.Key.Key_F12))
        act_f12.triggered.connect(lambda: self._on_screenshot_requested("Captura manual F12"))
        self.addAction(act_f12)

    def _init_subsystems(self) -> None:
        # Configurar puente de señales Qt para el monitor
        self._bridge = DeviceSignalsBridge()
        self._bridge.device_connected.connect(self._on_device_connected_signal)
        self._bridge.device_disconnected.connect(self._on_device_disconnected_signal)
        self._bridge.device_state_changed.connect(self._on_device_state_changed_signal)

        # Iniciar monitor de dispositivos si está habilitado
        if self._start_monitor:
            try:
                mon_runner = AdbRunner(adb_path=self._adb_path)

                def on_event(ev_name: str, entry: Any) -> None:
                    if ev_name == "DEVICE_CONNECTED":
                        try:
                            probe_runner = AdbRunner(serial=entry.serial, adb_path=self._adb_path)
                            dev_info = DeviceProbe(probe_runner).identify_device()
                            self._bridge.on_device_connected(dev_info)
                        except Exception:  # noqa: BLE001
                            basic_info = DeviceInfo(serial=entry.serial)
                            self._bridge.on_device_connected(basic_info)
                    elif ev_name == "DEVICE_DISCONNECTED":
                        self._bridge.on_device_disconnected(entry.serial)
                    elif ev_name == "DEVICE_STATE_CHANGED":
                        self._bridge.on_device_state_changed(entry.serial, entry.state)

                self._monitor = DeviceMonitor(runner=mon_runner, on_event=on_event)
                self._monitor.start()
            except Exception as exc:  # noqa: BLE001
                self._badge.set_error(str(exc))

    def _ensure_case_and_store(self) -> tuple[Case, EvidenceStore]:
        case = self._case_view.get_case()
        if case is None:
            msg = "Debe validar y registrar un caso legal antes de operar."
            raise ValueError(msg)

        if self._store is None or self._store.case.case_id != case.case_id:
            case_path = self._base_dir / case.case_id
            case_path.mkdir(parents=True, exist_ok=True)
            log_file = case_path / "logs" / "chain.jsonl"
            key = derive_case_key("temporary-session-phrase", b"\x00" * 16)
            logger = ChainedLog(
                path=log_file,
                key=key,
                genesis_hash="0" * 64,
                case_id=case.case_id,
                examiner=case.examiner.name,
            )
            self._store = EvidenceStore(case_path, case, logger)
            self._custody_view.update_case(case)

        return case, self._store

    def _on_device_connected_signal(self, dev: DeviceInfo) -> None:
        self._active_device = dev
        self._badge.set_connected(dev)
        self._device_view.update_device(dev)

    def _on_device_disconnected_signal(self, serial: str) -> None:
        self._active_device = None
        self._badge.set_disconnected()
        self._device_view.update_device(None)

    def _on_device_state_changed_signal(self, serial: str, state: str) -> None:
        if state == "unauthorized":
            self._badge.set_unauthorized(serial)

    def _on_manual_probe(self) -> None:
        serial = self._active_device.serial if self._active_device else None
        probe_runner = AdbRunner(serial=serial, adb_path=self._adb_path)
        probe = DeviceProbe(probe_runner)
        try:
            dev = probe.identify_device()
            self._active_device = dev
            self._badge.set_connected(dev)
            self._device_view.update_device(dev)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Error al sondear", f"Fallo al consultar dispositivo: {exc}")

    def _on_case_saved(self, case: Case) -> None:
        try:
            _, store = self._ensure_case_and_store()
            self._integrity_view.update_store(store)
            self._custody_view.update_case(case)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Error de Caso", str(exc))

    def _on_screenshot_requested(self, note: str) -> None:
        if self._active_device is None:
            QMessageBox.information(
                self, "Sin Dispositivo", "Conecte un dispositivo Android para capturar pantalla."
            )
            return

        try:
            _, store = self._ensure_case_and_store()
            runner = AdbRunner(serial=self._active_device.serial, adb_path=self._adb_path)
            self._screenshot_counter += 1

            meta = capture_forensic_screenshot(
                runner=runner,
                store=store,
                seq=self._screenshot_counter,
                note=note,
            )
            self._screenshot_view.add_screenshot(meta, base_path=store.base_dir)
            self._integrity_view.update_store(store)
            self._ticker.update_entry(store.logger.append("SCREENSHOT_TAKEN", "ui", meta))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self, "Error en Captura", f"No se pudo capturar la pantalla: {exc}"
            )

    def _on_start_acquisition(self, profile: ProfileType, selected_mods: list[str]) -> None:
        if self._active_device is None:
            QMessageBox.warning(
                self,
                "Sin Dispositivo",
                "Conecte un terminal Android antes de iniciar la extracción.",
            )
            return

        try:
            case, store = self._ensure_case_and_store()
            runner = AdbRunner(serial=self._active_device.serial, adb_path=self._adb_path)
            service = AcquisitionService(runner=runner, store=store)

            self._worker = AcquisitionWorker(
                service=service,
                case=case,
                device=self._active_device,
                profile=profile,
                custom_modules=selected_mods,
            )

            self._worker.progress_updated.connect(self._acquisition_view.update_progress)
            self._worker.module_finished.connect(self._on_worker_module_finished)
            self._worker.acquisition_finished.connect(self._on_worker_acquisition_finished)
            self._worker.error_occurred.connect(self._on_worker_error)
            self._worker.start()

        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error al Iniciar", str(exc))

    def _on_cancel_acquisition(self) -> None:
        if self._worker:
            self._worker.cancel()

    def _on_worker_module_finished(self, mod_name: str, res: ModuleResult) -> None:
        self._acquisition_view.on_module_finished(mod_name, res)
        if self._store:
            self._integrity_view.update_store(self._store)

    def _on_worker_acquisition_finished(self, summary: AcquisitionSummary) -> None:
        self._acquisition_view.on_acquisition_completed(summary)
        if self._store:
            self._integrity_view.update_store(
                self._store,
                tar_path=summary.tar_path,
                tar_sha256=summary.tar_sha256,
            )
            self._report_view.update_reports(self._store)
            case = self._case_view.get_case()
            self._custody_view.update_case(case)

    def _on_worker_error(self, err_msg: str) -> None:
        QMessageBox.critical(
            self, "Fallo en Adquisición", f"Error durante la extracción: {err_msg}"
        )

    def _on_generate_reports(self) -> None:
        if self._store is None or self._active_device is None:
            QMessageBox.warning(
                self, "Aviso", "Requiere un caso y un dispositivo activo para emitir el dictamen."
            )
            return

        case = self._case_view.get_case()
        if case is None:
            return

        gen = ReportGenerator(case, self._active_device, self._store)
        gen.generate_all()
        self._report_view.update_reports(self._store)
        self._integrity_view.update_store(self._store)

    def closeEvent(self, event: Any) -> None:
        if self._monitor:
            self._monitor.stop()
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(2000)
        event.accept()
