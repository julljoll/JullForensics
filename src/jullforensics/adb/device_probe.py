"""Sondeo e identificación forense detallada de terminales Android conectados."""

from __future__ import annotations

import contextlib
import re
import time

from jullforensics.adb.runner import AdbRunner
from jullforensics.domain.device import DeviceInfo

GETPROP_LINE_PATTERN = re.compile(r"^\[(.*?)\]:\s*\[(.*?)\]$")


def parse_getprop_output(output: str) -> dict[str, str]:
    """Parsea el volcado completo de getprop en un diccionario clave-valor."""
    props: dict[str, str] = {}
    for line in output.splitlines():
        match = GETPROP_LINE_PATTERN.match(line.strip())
        if match:
            k, v = match.groups()
            props[k] = v
    return props


class DeviceProbe:
    """Interrogador de hardware y sistema operativo mediante comandos seguros de solo lectura."""

    def __init__(self, runner: AdbRunner) -> None:
        self.runner = runner

    def identify_device(self) -> DeviceInfo:
        """Obtiene las propiedades del dispositivo en una sola llamada optimizada de getprop."""
        # 1. Obtener todas las propiedades
        cp_prop = self.runner.run("shell", "getprop", timeout=10)
        props = parse_getprop_output(cp_prop.stdout.decode("utf-8", "replace"))

        serial = (
            self.runner.serial
            or props.get("ro.serialno")
            or props.get("ro.boot.serialno")
            or "DESCONOCIDO"
        )
        model = props.get("ro.product.model", "Desconocido")
        manufacturer = props.get("ro.product.manufacturer", "Desconocido")
        brand = props.get("ro.product.brand", "Desconocido")
        android_ver = props.get("ro.build.version.release", "Desconocido")
        sdk_str = props.get("ro.build.version.sdk", "0")
        try:
            sdk_ver = int(sdk_str)
        except ValueError:
            sdk_ver = 0

        sec_patch = props.get("ro.build.version.security_patch", "Desconocido")
        fingerprint = props.get("ro.build.fingerprint", "Desconocido")
        build_id = props.get("ro.build.id", "Desconocido")
        enc_state = props.get("ro.crypto.state", "Desconocido")

        # 2. Medir desfase del reloj (host UTC vs dispositivo)
        t_host_before = time.time()
        cp_date = self.runner.run("shell", "date", "+%s", timeout=5)
        t_host_after = time.time()
        offset = 0.0
        with contextlib.suppress(Exception):
            dev_secs = int(cp_date.stdout.decode("ascii").strip())
            host_est = (t_host_before + t_host_after) / 2.0
            offset = round(dev_secs - host_est, 2)

        # 3. Nivel de batería
        battery_pct: int | None = None
        with contextlib.suppress(Exception):
            cp_bat = self.runner.run("shell", "dumpsys", "battery", timeout=5)
            for line in cp_bat.stdout.decode("utf-8", "replace").splitlines():
                if "level:" in line:
                    battery_pct = int(line.split(":", 1)[1].strip())
                    break

        return DeviceInfo(
            serial=serial,
            model=model,
            manufacturer=manufacturer,
            brand=brand,
            android_version=android_ver,
            sdk_version=sdk_ver,
            security_patch=sec_patch,
            build_fingerprint=fingerprint,
            build_id=build_id,
            battery_level_percent=battery_pct,
            clock_offset_seconds=offset,
            encryption_state=enc_state,
        )
