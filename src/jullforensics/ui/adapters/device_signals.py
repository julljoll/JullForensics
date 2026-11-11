"""Puente de señales Qt para el monitor de dispositivos ADB en tiempo real."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    from jullforensics.domain.device import DeviceInfo


class DeviceSignalsBridge(QObject):
    """Emite señales seguras de hilo cuando el estado de los dispositivos cambia."""

    device_connected = Signal(object)  # Emite DeviceInfo
    device_disconnected = Signal(str)  # Emite serial
    device_state_changed = Signal(str, str)  # Emite (serial, state)

    def on_device_connected(self, device_info: DeviceInfo) -> None:
        self.device_connected.emit(device_info)

    def on_device_disconnected(self, serial: str) -> None:
        self.device_disconnected.emit(serial)

    def on_device_state_changed(self, serial: str, state: str) -> None:
        self.device_state_changed.emit(serial, state)
