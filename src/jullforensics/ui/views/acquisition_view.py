"""Vista 04: Configuración, control y ejecución de la adquisición lógica forense."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from jullforensics.services.acquisition_service import ProfileType

if TYPE_CHECKING:
    from jullforensics.acquisition.base import ModuleResult
    from jullforensics.services.acquisition_service import AcquisitionSummary


class AcquisitionView(QWidget):
    """Panel central de control y orquestación de la adquisición de evidencias."""

    start_requested = Signal(object, list)  # (ProfileType, list[str] modules)
    cancel_requested = Signal()

    MODULE_DESCRIPTIONS: dict[str, str] = {
        "screenshot": "Captura forense inicial de pantalla en RAM (Volatilidad 0)",
        "device_props": "Propiedades de hardware getprop y desfase horario (Volatilidad 10)",
        "system_dumps": "Volcados dumpsys, base de datos settings y logcat (Volatilidad 20)",
        "packages": "Inventario de aplicaciones instaladas y firmas APK (Volatilidad 30)",
        "content_providers": "Proveedores de contenido: contactos, SMS y medios (Volatilidad 40)",
        "shared_storage": "Almacenamiento compartido (/sdcard) vía streaming (Volatilidad 50)",
        "bugreport": "Volcado integral bugreportz del sistema (Volatilidad 60)",
    }

    def __init__(self) -> None:
        super().__init__()
        self._checkboxes: dict[str, QCheckBox] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # 1. Selector de perfil forense
        grp_profile = QGroupBox("PERFIL DE ADQUISICIÓN LÓGICA (ISO/IEC 27037 / RFC 3227)")
        h_prof = QHBoxLayout(grp_profile)

        self._cb_profile = QComboBox()
        self._cb_profile.addItem(
            "ESTÁNDAR (Recomendado: Captura, Props, Dumps, Apps, Proveedores)", ProfileType.ESTANDAR
        )
        self._cb_profile.addItem(
            "RÁPIDA (Mínima intrusión: Captura, Props, Dumps, Apps)", ProfileType.RAPIDA
        )
        self._cb_profile.addItem(
            "COMPLETA (Exhaustiva: Estándar + /sdcard + Bugreport)", ProfileType.COMPLETA
        )
        self._cb_profile.addItem("PERSONALIZADA (Selección manual de módulos)", ProfileType.CUSTOM)
        self._cb_profile.currentIndexChanged.connect(self._on_profile_changed)

        h_prof.addWidget(QLabel("PERFIL FORENSE:"), stretch=0)
        h_prof.addWidget(self._cb_profile, stretch=1)
        layout.addWidget(grp_profile)

        # 2. Lista de módulos seleccionables
        grp_mods = QGroupBox("MÓDULOS DE EXTRACCIÓN Y ORDEN DE VOLATILIDAD")
        v_mods = QVBoxLayout(grp_mods)

        for mod_name, desc in self.MODULE_DESCRIPTIONS.items():
            cb = QCheckBox(f"{mod_name.upper()} — {desc}")
            cb.stateChanged.connect(self._on_checkbox_toggled)
            self._checkboxes[mod_name] = cb
            v_mods.addWidget(cb)

        layout.addWidget(grp_mods)

        # 3. Barra de progreso y estado
        grp_prog = QGroupBox("PROGRESO DE LA ADQUISICIÓN Y BITÁCORA EN TIEMPO REAL")
        v_prog = QVBoxLayout(grp_prog)

        self._lbl_current_step = QLabel("Listo para iniciar extracción lógica.")
        self._lbl_current_step.setStyleSheet("font-weight: bold;")
        v_prog.addWidget(self._lbl_current_step)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        v_prog.addWidget(self._progress_bar)

        self._console = QPlainTextEdit()
        self._console.setReadOnly(True)
        self._console.setStyleSheet("background-color: #1A1A1A; color: #00FF66; font-size: 11px;")
        self._console.setMaximumHeight(140)
        v_prog.addWidget(self._console)

        layout.addWidget(grp_prog)

        # 4. Botones de acción
        h_actions = QHBoxLayout()
        self._btn_start = QPushButton("INICIAR ADQUISICIÓN LÓGICA FORENSE")
        self._btn_start.setObjectName("btn_primary")
        self._btn_start.clicked.connect(self._on_start_click)

        self._btn_cancel = QPushButton("CANCELAR ADQUISICIÓN")
        self._btn_cancel.setObjectName("btn_danger")
        self._btn_cancel.setEnabled(False)
        self._btn_cancel.clicked.connect(self._on_cancel_click)

        h_actions.addWidget(self._btn_start, stretch=1)
        h_actions.addWidget(self._btn_cancel, stretch=0)
        layout.addLayout(h_actions)

        # Aplicar perfil inicial
        self._on_profile_changed(0)

    def _on_profile_changed(self, index: int) -> None:
        profile = self._cb_profile.currentData()
        if profile == ProfileType.RAPIDA:
            active = {"screenshot", "device_props", "packages", "system_dumps"}
        elif profile == ProfileType.ESTANDAR:
            active = {"screenshot", "device_props", "packages", "system_dumps", "content_providers"}
        elif profile == ProfileType.COMPLETA:
            active = set(self.MODULE_DESCRIPTIONS.keys())
        else:
            return  # En personalizado mantener selecciones del usuario

        for name, cb in self._checkboxes.items():
            cb.blockSignals(True)
            cb.setChecked(name in active)
            cb.blockSignals(False)

    def _on_checkbox_toggled(self) -> None:
        # Si el usuario modifica checkboxes manualmente, cambiar combo a CUSTOM
        current_prof = self._cb_profile.currentData()
        if current_prof != ProfileType.CUSTOM:
            self._cb_profile.blockSignals(True)
            idx = self._cb_profile.findData(ProfileType.CUSTOM)
            if idx >= 0:
                self._cb_profile.setCurrentIndex(idx)
            self._cb_profile.blockSignals(False)

    def _on_start_click(self) -> None:
        profile = self._cb_profile.currentData()
        selected_mods = [k for k, cb in self._checkboxes.items() if cb.isChecked()]
        if not selected_mods:
            self._console.appendPlainText("⚠ Debe seleccionar al menos un módulo de extracción.")
            return

        self._btn_start.setEnabled(False)
        self._btn_cancel.setEnabled(True)
        self._progress_bar.setValue(0)
        self._console.clear()
        self._console.appendPlainText(f"=== INICIANDO ADQUISICIÓN: PERFIL {profile} ===")
        self.start_requested.emit(profile, selected_mods)

    def _on_cancel_click(self) -> None:
        self._btn_cancel.setEnabled(False)
        self._console.appendPlainText(
            "⚠ Cancelación solicitada por el usuario. Finalizando módulo actual..."
        )
        self.cancel_requested.emit()

    def update_progress(self, mod_name: str, pct: float, msg: str) -> None:
        self._progress_bar.setValue(int(pct))
        self._lbl_current_step.setText(f"Módulo: {mod_name} ({pct:.0f}%) — {msg}")
        self._console.appendPlainText(f"[{pct:.0f}%] {mod_name}: {msg}")

    def on_module_finished(self, mod_name: str, result: ModuleResult) -> None:
        status_str = (
            f"✓ {mod_name} completado ({result.status}) con {len(result.artifacts)} artefactos."
        )
        self._console.appendPlainText(status_str)

    def on_acquisition_completed(self, summary: AcquisitionSummary) -> None:
        self._btn_start.setEnabled(True)
        self._btn_cancel.setEnabled(False)
        self._progress_bar.setValue(100)
        self._lbl_current_step.setText(f"Adquisición finalizada con estado: {summary.status}")
        self._console.appendPlainText(
            f"=== ADQUISICIÓN FINALIZADA ===\n"
            f"Artefactos totales: {summary.total_artifacts} | Tamaño: {summary.total_bytes} bytes\n"
            f"Contenedor JF-TAR: {summary.tar_path}\n"
            f"SHA-256 TAR: {summary.tar_sha256}\n"
        )
