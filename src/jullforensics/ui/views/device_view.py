"""Vista 02: Inspección y sondeo técnico del terminal móvil (DeviceView)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from jullforensics.domain.device import DeviceInfo


class DeviceView(QWidget):
    """Muestra los parámetros técnicos, estado de seguridad y huella forense del terminal."""

    probe_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._current_device: DeviceInfo | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        grp = QGroupBox("PARÁMETROS TÉCNICOS Y ESTADO DEL DISPOSITIVO ANDROID")
        v_box = QVBoxLayout(grp)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["PARÁMETRO FORENSE", "VALOR TÉCNICO REGISTRADO"])
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        v_box.addWidget(self._table)

        btn_layout = QHBoxLayout()
        self._btn_refresh = QPushButton("SONDEAR / ACTUALIZAR DISPOSITIVO (ADB GETPROP)")
        self._btn_refresh.setObjectName("btn_primary")
        self._btn_refresh.clicked.connect(self.probe_requested.emit)

        btn_layout.addStretch(1)
        btn_layout.addWidget(self._btn_refresh)
        v_box.addLayout(btn_layout)

        layout.addWidget(grp)

    def update_device(self, dev: DeviceInfo | None) -> None:
        self._current_device = dev
        self._table.setRowCount(0)

        if dev is None:
            return

        rows = [
            ("NÚMERO DE SERIE ADB", dev.serial),
            ("MARCA / FABRICANTE", f"{dev.brand} ({dev.manufacturer})"),
            ("MODELO COMERCIAL", dev.model),
            ("VERSIÓN ANDROID", f"Android {dev.android_version} (API SDK {dev.sdk_version})"),
            ("PARCHE DE SEGURIDAD", dev.security_patch),
            ("HUELLA DE COMPILACIÓN (FINGERPRINT)", dev.build_fingerprint),
            ("ID DE COMPILACIÓN (BUILD ID)", dev.build_id),
            (
                "DESVIACIÓN DE RELOJ (CLOCK OFFSET)",
                f"{dev.clock_offset_seconds:.3f} s respecto a UTC",
            ),
            (
                "NIVEL DE BATERÍA",
                f"{dev.battery_level_percent} %"
                if dev.battery_level_percent is not None
                else "N/A",
            ),
            ("ESTADO DE CIFRADO", dev.encryption_state),
            (
                "IMEI / IDENTIFICADOR DE RED",
                dev.imei_if_accessible or "Restringido (API >= 29 sin root)",
            ),
        ]

        self._table.setRowCount(len(rows))
        align = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        for idx, (param, val) in enumerate(rows):
            it_param = QTableWidgetItem(param)
            it_param.setTextAlignment(align)
            it_val = QTableWidgetItem(val)
            it_val.setTextAlignment(align)
            self._table.setItem(idx, 0, it_param)
            self._table.setItem(idx, 1, it_val)
