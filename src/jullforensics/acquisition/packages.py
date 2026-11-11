"""Módulo de adquisición del inventario de aplicaciones y paquetes instalados."""

from __future__ import annotations

import csv
import io
import re
import time

from jullforensics.acquisition.base import (
    AcquisitionContext,
    AcquisitionModule,
    ModuleResult,
    ModuleStatus,
)

PACKAGE_LINE_PATTERN = re.compile(
    r"^package:(.*?)=(.*?)(?:\s+versionCode:(\d+))?(?:\s+installer=(.*?))?(?:\s+uid:(\d+))?$"
)


class PackagesModule(AcquisitionModule):
    name = "packages"
    description = "Inventario de aplicaciones de usuario y de sistema con rutas de APK y firmas"
    order_of_volatility = 3
    intrusive = False

    def precheck(self, ctx: AcquisitionContext) -> list[str]:
        return []

    def acquire(self, ctx: AcquisitionContext) -> ModuleResult:
        t0 = time.monotonic()
        artifacts: list[str] = []
        notes: list[str] = []

        cp = ctx.runner.run(
            "shell", "pm", "list", "packages", "-f", "-i", "-U", "--show-versioncode", timeout=30
        )
        if cp.returncode != 0:
            return ModuleResult(
                module_name=self.name,
                status=ModuleStatus.FAILED,
                notes=["Fallo al listar paquetes con pm list packages"],
                duration_seconds=round(time.monotonic() - t0, 3),
            )

        # 1. Guardar volcado crudo
        raw_output = cp.stdout
        ctx.store.put_bytes("apps/packages_raw.txt", raw_output, module=self.name)
        artifacts.append("apps/packages_raw.txt")

        # 2. Parsear a CSV estructurado
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["package_name", "apk_path", "version_code", "installer", "uid"])

        parsed_count = 0
        for line in raw_output.decode("utf-8", "replace").splitlines():
            line_str = line.strip()
            if not line_str.startswith("package:"):
                continue
            # package:/data/app/.../base.apk=com.example versionCode:123 installer=...
            match = PACKAGE_LINE_PATTERN.match(line_str)
            if match:
                apk_path, pkg_name, ver_code, installer, uid = match.groups()
                writer.writerow([pkg_name, apk_path, ver_code or "", installer or "", uid or ""])
                parsed_count += 1
            else:
                # Fallback de parseo simple
                parts = line_str.replace("package:", "").split("=", 1)
                if len(parts) == 2:
                    apk_path, rest = parts
                    pkg_parts = rest.split()
                    pkg_name = pkg_parts[0] if pkg_parts else rest
                    writer.writerow([pkg_name, apk_path, "", "", ""])
                    parsed_count += 1

        csv_bytes = csv_buffer.getvalue().encode("utf-8")
        ctx.store.put_bytes("apps/packages.csv", csv_bytes, module=self.name)
        artifacts.append("apps/packages.csv")

        notes.append(f"Se inventariaron {parsed_count} paquetes instalados.")
        return ModuleResult(
            module_name=self.name,
            status=ModuleStatus.OK,
            artifacts=artifacts,
            notes=notes,
            duration_seconds=round(time.monotonic() - t0, 3),
        )
