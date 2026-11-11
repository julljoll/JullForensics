"""Módulo de adquisición de proveedores de contenido (Contactos, Llamadas, SMS)."""

from __future__ import annotations

import time

from jullforensics.acquisition.base import (
    AcquisitionContext,
    AcquisitionModule,
    ModuleResult,
    ModuleStatus,
)

PROVIDERS: tuple[tuple[str, str], ...] = (
    ("contacts", "content://com.android.contacts/data/phones/"),
    ("call_log", "content://call_log/calls"),
    ("sms", "content://sms"),
)


class ContentProvidersModule(AcquisitionModule):
    name = "content_providers"
    description = (
        "Consulta a content providers accesibles por el usuario shell (contactos, llamadas, sms)"
    )
    order_of_volatility = 4
    intrusive = False

    def precheck(self, ctx: AcquisitionContext) -> list[str]:
        if ctx.device_info.sdk_version >= 29:
            return [
                "En Android 10+ (SDK >= 29), las consultas directas a SMS/Llamadas por ADB shell "
                "pueden estar restringidas por la política de permisos del sistema."
            ]
        return []

    def acquire(self, ctx: AcquisitionContext) -> ModuleResult:
        t0 = time.monotonic()
        artifacts: list[str] = []
        notes: list[str] = []

        denied_count = 0
        success_count = 0

        for label, uri in PROVIDERS:
            if ctx.cancel_requested:
                break
            cp = ctx.runner.run("shell", "content", "query", "--uri", uri, timeout=20)
            if cp.returncode == 0 and cp.stdout and b"SecurityException" not in cp.stderr:
                rel = f"providers/{label}.txt"
                ctx.store.put_bytes(rel, cp.stdout, module=self.name)
                artifacts.append(rel)
                success_count += 1
            else:
                denied_count += 1
                notes.append(f"Acceso denegado o vacío en proveedor {label} ({uri})")

        if success_count > 0:
            status = ModuleStatus.OK if denied_count == 0 else ModuleStatus.PARTIAL
        else:
            status = ModuleStatus.PARTIAL if denied_count > 0 else ModuleStatus.SKIPPED

        return ModuleResult(
            module_name=self.name,
            status=status,
            artifacts=artifacts,
            notes=notes,
            duration_seconds=round(time.monotonic() - t0, 3),
        )
