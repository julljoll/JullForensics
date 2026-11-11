"""Vista 07: Libro de actas y trazabilidad de Cadena de Custodia (ISO/IEC 27037 / 17025)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from jullforensics.domain.custody import CustodyEvent, CustodyEventType

if TYPE_CHECKING:
    from jullforensics.domain.case import Case


class CustodyView(QWidget):
    """Gestión y visualización inalterable de la cadena de custodia pericial."""

    event_added = Signal(object)  # Emite CustodyEvent

    def __init__(self) -> None:
        super().__init__()
        self._case: Case | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # 1. Tabla de eventos de cadena de custodia
        grp_table = QGroupBox("REGISTRO CRONOLÓGICO DE LA CADENA DE CUSTODIA (ISO/IEC 27037)")
        v_table = QVBoxLayout(grp_table)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            [
                "FECHA / HORA (UTC)",
                "EVENTO DE CUSTODIA",
                "RESPONSABLE / ACTOR",
                "SEDE / UBICACIÓN",
                "HASH SHA-256 EVIDENCIA",
            ]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        v_table.addWidget(self._table)
        layout.addWidget(grp_table)

        # 2. Formulario para añadir eventos manuales (traslados, entrega de evidencias, etc.)
        grp_form = QGroupBox("ANOTAR NUEVO HITO EN LA CADENA DE CUSTODIA")
        fl = QFormLayout(grp_form)

        self._cb_event_type = QComboBox()
        for et in CustodyEventType:
            self._cb_event_type.addItem(et.value, et)

        self._in_actor = QLineEdit("Perito Judicial")
        self._in_action = QLineEdit()
        self._in_action.setPlaceholderText("Descripción detallada de la actuación o traspaso...")
        self._in_location = QLineEdit("Sede Central del Laboratorio")
        self._in_hash = QLineEdit()
        self._in_hash.setPlaceholderText("Hash SHA-256 del precinto o evidencia (opcional)")

        fl.addRow("TIPO DE EVENTO:", self._cb_event_type)
        fl.addRow("RESPONSABLE (ACTOR):", self._in_actor)
        fl.addRow("ACCIÓN PRACTICADA:", self._in_action)
        fl.addRow("UBICACIÓN / SEDE:", self._in_location)
        fl.addRow("HASH DE CONTROL:", self._in_hash)

        h_btn = QHBoxLayout()
        h_btn.addStretch(1)
        self._btn_add = QPushButton("REGISTRAR HITO EN CADENA DE CUSTODIA")
        self._btn_add.setObjectName("btn_primary")
        self._btn_add.clicked.connect(self._on_add_click)
        h_btn.addWidget(self._btn_add)
        fl.addRow(h_btn)

        layout.addWidget(grp_form)

    def update_case(self, case: Case | None) -> None:
        self._case = case
        self._table.setRowCount(0)

        if case is None:
            return

        self._table.setRowCount(len(case.chain_of_custody))
        for row, ev in enumerate(case.chain_of_custody):
            it_ts = QTableWidgetItem(ev.ts_utc[:19])
            it_type = QTableWidgetItem(ev.event_type.value)
            it_actor = QTableWidgetItem(ev.actor)
            it_loc = QTableWidgetItem(ev.location)
            it_hash = QTableWidgetItem(ev.evidence_hash_sha256)

            self._table.setItem(row, 0, it_ts)
            self._table.setItem(row, 1, it_type)
            self._table.setItem(row, 2, it_actor)
            self._table.setItem(row, 3, it_loc)
            self._table.setItem(row, 4, it_hash)

    def _on_add_click(self) -> None:
        action_text = self._in_action.text().strip()
        if not action_text:
            return

        ev_type = self._cb_event_type.currentData()
        now_utc = datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
        hash_val = self._in_hash.text().strip() or ("0" * 64)

        event = CustodyEvent(
            event_id=str(uuid.uuid4()),
            ts_utc=now_utc,
            event_type=ev_type,
            actor=self._in_actor.text().strip(),
            action_description=action_text,
            location=self._in_location.text().strip(),
            evidence_hash_sha256=hash_val,
        )

        if self._case:
            self._case.chain_of_custody.append(event)
            self.update_case(self._case)

        self.event_added.emit(event)
        self._in_action.clear()
        self._in_hash.clear()
