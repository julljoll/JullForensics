"""Monitor en tiempo real del estado de conexión de dispositivos ADB (track-devices)."""

from __future__ import annotations

import contextlib
import logging
import subprocess
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from enum import StrEnum
from typing import IO, BinaryIO

from jullforensics.adb.runner import AdbRunner

logger = logging.getLogger(__name__)


class DeviceState(StrEnum):
    DEVICE = "device"
    UNAUTHORIZED = "unauthorized"
    OFFLINE = "offline"
    RECOVERY = "recovery"
    SIDELOAD = "sideload"
    BOOTLOADER = "bootloader"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DeviceEntry:
    serial: str
    state: DeviceState
    model: str | None = None
    transport_id: str | None = None


def parse_devices(payload: str) -> dict[str, DeviceEntry]:
    """Parsea el payload de salida de adb track-devices -l."""
    devices: dict[str, DeviceEntry] = {}
    for line in payload.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue
        parts = line_stripped.split()
        if len(parts) < 2:
            continue
        serial, raw_state, *rest = parts
        try:
            state = DeviceState(raw_state.lower())
        except ValueError:
            state = DeviceState.UNKNOWN

        attrs: dict[str, str] = {}
        for p in rest:
            if ":" in p:
                k, v = p.split(":", 1)
                attrs[k] = v

        devices[serial] = DeviceEntry(
            serial=serial,
            state=state,
            model=attrs.get("model"),
            transport_id=attrs.get("transport_id"),
        )
    return devices


def read_frames(stream: BinaryIO | IO[bytes]) -> Iterator[dict[str, DeviceEntry]]:
    """Generador que lee tramas continuas de longitud fija (4 caracteres hex) de track-devices."""
    while True:
        head = stream.read(4)
        if len(head) < 4:
            break
        try:
            size = int(head.decode("ascii"), 16)
        except ValueError:
            break

        payload = stream.read(size).decode("utf-8", "replace") if size > 0 else ""
        yield parse_devices(payload)


def diff_devices(
    prev: dict[str, DeviceEntry],
    cur: dict[str, DeviceEntry],
) -> list[tuple[str, DeviceEntry]]:
    """Calcula la diferencia entre dos estados para emitir eventos forenses precisos."""
    events: list[tuple[str, DeviceEntry]] = []
    # Nuevas conexiones
    for s in cur.keys() - prev.keys():
        events.append(("DEVICE_CONNECTED", cur[s]))
    # Desconexiones
    for s in prev.keys() - cur.keys():
        events.append(("DEVICE_DISCONNECTED", prev[s]))
    # Cambios de estado (ej. unauthorized -> device)
    for s in cur.keys() & prev.keys():
        if cur[s].state != prev[s].state:
            events.append(("DEVICE_STATE_CHANGED", cur[s]))
    return events


class DeviceMonitor(threading.Thread):
    """Demonio en hilo secundario que vigila las conexiones USB y notifica a los escuchas."""

    def __init__(
        self,
        runner: AdbRunner,
        on_event: Callable[[str, DeviceEntry], None],
    ) -> None:
        super().__init__(name="AdbDeviceMonitor", daemon=True)
        self.runner = runner
        self.on_event = on_event
        self._stop_event = threading.Event()
        self.current_devices: dict[str, DeviceEntry] = {}
        self._process: subprocess.Popen[bytes] | None = None

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                proc = self.runner.run_stream("track-devices", "-l")
                self._process = proc
                if proc.stdout is None:
                    break

                for snapshot in read_frames(proc.stdout):
                    if self._stop_event.is_set():
                        break
                    events = diff_devices(self.current_devices, snapshot)
                    self.current_devices = snapshot
                    for ev_name, entry in events:
                        self.on_event(ev_name, entry)

                proc.wait()
            except Exception as e:
                logger.warning(f"Reintentando conexión con monitor adb: {e}")
                self._stop_event.wait(timeout=2.0)

    def stop(self) -> None:
        """Detiene el hilo del monitor y termina el proceso subyacente."""
        self._stop_event.set()
        if self._process:
            with contextlib.suppress(Exception):
                self._process.terminate()
