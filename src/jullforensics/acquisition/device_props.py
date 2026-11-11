"""Módulo de adquisición de propiedades del dispositivo (getprop, battery, date)."""

from __future__ import annotations

import json
import time

from jullforensics.acquisition.base import (
    AcquisitionContext,
    AcquisitionModule,
    ModuleResult,
    ModuleStatus,
)


class DevicePropsModule(AcquisitionModule):
    name = "device_props"
    description = (
        "Captura de propiedades completas del sistema (getprop), batería y desfase temporal"
    )
    order_of_volatility = 1  # Máxima volatilidad (RFC 3227)
    intrusive = False

    def precheck(self, ctx: AcquisitionContext) -> list[str]:
        return []

    def acquire(self, ctx: AcquisitionContext) -> ModuleResult:
        t0 = time.monotonic()
        artifacts: list[str] = []
        notes: list[str] = []

        # 1. getprop
        cp_prop = ctx.runner.run("shell", "getprop", timeout=15)
        if cp_prop.returncode == 0:
            ctx.store.put_bytes("device/getprop.txt", cp_prop.stdout, module=self.name)
            artifacts.append("device/getprop.txt")
        else:
            notes.append("Fallo al ejecutar getprop")

        # 2. dumpsys battery
        cp_bat = ctx.runner.run("shell", "dumpsys", "battery", timeout=10)
        if cp_bat.returncode == 0:
            ctx.store.put_bytes("device/battery.txt", cp_bat.stdout, module=self.name)
            artifacts.append("device/battery.txt")

        # 3. Metadatos de reloj
        clock_meta = {
            "clock_offset_seconds": ctx.device_info.clock_offset_seconds,
            "acquired_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        ctx.store.put_bytes(
            "device/clock_offset.json",
            json.dumps(clock_meta, indent=2).encode("utf-8"),
            module=self.name,
        )
        artifacts.append("device/clock_offset.json")

        status = ModuleStatus.OK if len(artifacts) >= 2 else ModuleStatus.PARTIAL
        return ModuleResult(
            module_name=self.name,
            status=status,
            artifacts=artifacts,
            notes=notes,
            duration_seconds=round(time.monotonic() - t0, 3),
        )
