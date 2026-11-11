"""Módulo de adquisición de volcados del sistema (dumpsys, settings, logcat)."""

from __future__ import annotations

import time

from jullforensics.acquisition.base import (
    AcquisitionContext,
    AcquisitionModule,
    ModuleResult,
    ModuleStatus,
)

DUMPSYS_SERVICES: tuple[str, ...] = (
    "activity",
    "package",
    "account",
    "usagestats",
    "wifi",
    "connectivity",
    "notification",
)

SETTINGS_NAMESPACES: tuple[str, ...] = (
    "global",
    "secure",
    "system",
)


class SystemDumpsModule(AcquisitionModule):
    name = "system_dumps"
    description = "Volcados forenses de servicios dumpsys, tablas de settings y buffers de logcat"
    order_of_volatility = 2
    intrusive = False

    def precheck(self, ctx: AcquisitionContext) -> list[str]:
        return []

    def acquire(self, ctx: AcquisitionContext) -> ModuleResult:
        t0 = time.monotonic()
        artifacts: list[str] = []
        notes: list[str] = []

        # 1. Dumpsys por servicio seleccionado
        for svc in DUMPSYS_SERVICES:
            if ctx.cancel_requested:
                break
            cp = ctx.runner.run("shell", "dumpsys", svc, timeout=30)
            if cp.returncode == 0 and cp.stdout:
                rel = f"system/dumpsys_{svc}.txt"
                ctx.store.put_bytes(rel, cp.stdout, module=self.name)
                artifacts.append(rel)

        # 2. Settings de los tres namespaces
        for ns in SETTINGS_NAMESPACES:
            if ctx.cancel_requested:
                break
            cp = ctx.runner.run("shell", "settings", "list", ns, timeout=10)
            if cp.returncode == 0 and cp.stdout:
                rel = f"system/settings_{ns}.txt"
                ctx.store.put_bytes(rel, cp.stdout, module=self.name)
                artifacts.append(rel)

        # 3. Logcat completo
        if not ctx.cancel_requested:
            cp_logcat = ctx.runner.run("logcat", "-d", timeout=45)
            if cp_logcat.returncode == 0 and cp_logcat.stdout:
                rel = "system/logcat.txt"
                ctx.store.put_bytes(rel, cp_logcat.stdout, module=self.name)
                artifacts.append(rel)

        status = ModuleStatus.OK if artifacts else ModuleStatus.FAILED
        return ModuleResult(
            module_name=self.name,
            status=status,
            artifacts=artifacts,
            notes=notes,
            duration_seconds=round(time.monotonic() - t0, 3),
        )
