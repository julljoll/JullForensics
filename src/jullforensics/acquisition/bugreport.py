"""Módulo de adquisición de reporte de diagnóstico integral (bugreportz)."""

from __future__ import annotations

import time

from jullforensics.acquisition.base import (
    AcquisitionContext,
    AcquisitionModule,
    ModuleResult,
    ModuleStatus,
)


class BugreportModule(AcquisitionModule):
    name = "bugreport"
    description = "Generación de informe de diagnóstico bugreportz del sistema completo"
    order_of_volatility = 6
    intrusive = False

    def precheck(self, ctx: AcquisitionContext) -> list[str]:
        return [
            "La generación de un bugreport completo puede demorar entre 1 y 4 minutos "
            "según el dispositivo."
        ]

    def acquire(self, ctx: AcquisitionContext) -> ModuleResult:
        t0 = time.monotonic()
        artifacts: list[str] = []
        notes: list[str] = []

        cp = ctx.runner.run("bugreportz", timeout=300)
        output = cp.stdout.decode("utf-8", "replace").strip()

        # bugreportz devuelve: OK:/data/user_de/0/.../bugreports/bugreport-....zip
        if cp.returncode == 0 and "OK:" in output:
            remote_zip = output.split("OK:", 1)[1].strip()
            dest_rel = "bugreport/bugreport.zip"
            # Extraer archivo usando pull
            cp_pull = ctx.runner.run(
                "pull", "-a", remote_zip, str(ctx.store.base_dir / dest_rel), timeout=120
            )
            if cp_pull.returncode == 0:
                # Registrar artefacto en evidence_store
                ctx.store.put_file(dest_rel, ctx.store.base_dir / dest_rel, module=self.name)
                artifacts.append(dest_rel)
                status = ModuleStatus.OK
            else:
                notes.append("Fallo al descargar el archivo ZIP generado por bugreportz")
                status = ModuleStatus.FAILED
        else:
            notes.append(f"bugreportz no completó con éxito: {output}")
            status = ModuleStatus.FAILED

        return ModuleResult(
            module_name=self.name,
            status=status,
            artifacts=artifacts,
            notes=notes,
            duration_seconds=round(time.monotonic() - t0, 3),
        )
