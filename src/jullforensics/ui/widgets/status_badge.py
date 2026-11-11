"""Insignia de estado de conexión ADB en tiempo real (WCAG 2.2 AA)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from jullforensics.ui.theme.tokens import (
    COLOR_DANGER,
    COLOR_DARK_SURFACE,
    COLOR_SUCCESS,
    COLOR_WARNING,
)

if TYPE_CHECKING:
    from jullforensics.domain.device import DeviceInfo


class StatusBadge(QLabel):
    """Etiqueta prominente de estado de conexión ADB con texto explícito y color accesible."""

    def __init__(self) -> None:
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(34)
        self.set_disconnected()

    def set_connected(self, device: DeviceInfo) -> None:
        label_text = f" ■ CONECTADO: {device.brand} {device.model} [{device.serial}] "
        self.setText(label_text)
        self.setStyleSheet(
            f"background-color: {COLOR_SUCCESS}; color: #FFFFFF; font-weight: bold; "
            "border: 2px solid #0A0A0A; padding: 4px 12px;"
        )

    def set_unauthorized(self, serial: str) -> None:
        label_text = f" ▲ NO AUTORIZADO: {serial} (Acepte depuración USB en pantalla) "
        self.setText(label_text)
        self.setStyleSheet(
            f"background-color: {COLOR_WARNING}; color: #FFFFFF; font-weight: bold; "
            "border: 2px solid #0A0A0A; padding: 4px 12px;"
        )

    def set_disconnected(self) -> None:
        self.setText(" ● SIN DISPOSITIVO CONECTADO (Esperando ADB...) ")
        self.setStyleSheet(
            f"background-color: {COLOR_DARK_SURFACE}; color: #FFFFFF; font-weight: bold; "
            "border: 2px solid #0A0A0A; padding: 4px 12px;"
        )

    def set_error(self, message: str) -> None:
        self.setText(f" ✖ ERROR ADB: {message} ")
        self.setStyleSheet(
            f"background-color: {COLOR_DANGER}; color: #FFFFFF; font-weight: bold; "
            "border: 2px solid #0A0A0A; padding: 4px 12px;"
        )
