"""Ticker inferior de eventos auditables en tiempo real con hash encadenado."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

if TYPE_CHECKING:
    from jullforensics.integrity.chained_log import LogEntry


class LogTicker(QWidget):
    """Barra inferior con visualización en vivo de eventos y hash de integridad de cabecera."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(30)
        self.setStyleSheet(
            "background-color: #1A1A1A; border-top: 2px solid #0A0A0A; padding: 2px 8px;"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)

        self._lbl_event = QLabel("SISTEMA FORENSE INICIALIZADO - ESPERANDO ACTUACIÓN")
        self._lbl_event.setStyleSheet("color: #00FF66; font-size: 11px; font-weight: bold;")
        self._lbl_event.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._lbl_hash = QLabel("HEAD HASH: [GENESIS]")
        self._lbl_hash.setStyleSheet("color: #FFE600; font-size: 11px;")
        self._lbl_hash.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(self._lbl_event, stretch=1)
        layout.addWidget(self._lbl_hash, stretch=0)

    def update_entry(self, entry: LogEntry) -> None:
        event_text = f"#{entry.seq:04d} | {entry.event} [{entry.module}]"
        self._lbl_event.setText(event_text)
        short_hash = entry.entry_hash[:16] + "..."
        self._lbl_hash.setText(f"HEAD HASH: {short_hash}")
