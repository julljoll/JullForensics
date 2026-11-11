"""Módulo de adquisición de almacenamiento compartido (/sdcard) con estrategias A y B."""

from __future__ import annotations

import contextlib
import tarfile
import time

from jullforensics.acquisition.base import (
    AcquisitionContext,
    AcquisitionModule,
    ModuleResult,
    ModuleStatus,
)
from jullforensics.storage.name_sanitizer import sanitize_relative_path


class SharedStorageModule(AcquisitionModule):
    name = "shared_storage"
    description = (
        "Extracción lógica de almacenamiento compartido (/storage/emulated/0) en streaming directo"
    )
    order_of_volatility = 5
    intrusive = False

    def precheck(self, ctx: AcquisitionContext) -> list[str]:
        # Pre-chequeo de espacio
        warnings: list[str] = []
        with contextlib.suppress(Exception):
            cp_df = ctx.runner.run("shell", "df", "/storage/emulated/0", timeout=5)
            lines = cp_df.stdout.decode("utf-8", "replace").splitlines()
            if len(lines) >= 2:
                warnings.append(f"Uso en dispositivo: {lines[1]}")
        return warnings

    def _supports_strategy_a(self, ctx: AcquisitionContext) -> bool:
        """Comprueba si el dispositivo tiene tar ejecutable en toybox/toolbox."""
        try:
            cp = ctx.runner.run("shell", "which", "tar", timeout=5)
            return cp.returncode == 0 and b"tar" in cp.stdout
        except Exception:
            return False

    def acquire(self, ctx: AcquisitionContext) -> ModuleResult:
        t0 = time.monotonic()
        artifacts: list[str] = []
        notes: list[str] = []

        has_toybox_tar = self._supports_strategy_a(ctx)
        strat_name = "A (Stream TAR toybox)" if has_toybox_tar else "B (Por archivo)"
        notes.append(f"Estrategia seleccionada: {strat_name}")

        if has_toybox_tar:
            # Estrategia A: Stream directo de tar desde el dispositivo
            try:
                proc = ctx.runner.run_stream(
                    "exec-out", "tar", "-cf", "-", "-C", "/storage/emulated/0", "."
                )
                if proc.stdout is None:
                    raise RuntimeError("No se pudo abrir stdout de tar streaming")

                extracted_count = 0
                # Desempaquetar el flujo tar recibido directamente al evidence_store
                with tarfile.open(fileobj=proc.stdout, mode="r|") as tar_stream:
                    for member in tar_stream:
                        if ctx.cancel_requested:
                            break
                        if not member.isfile():
                            continue

                        f_data = tar_stream.extractfile(member)
                        if f_data:
                            # Sanitizar nombre relativo de miembro
                            clean_name = sanitize_relative_path(member.name)
                            rel_evidence_path = f"evidence/sdcard/{clean_name}"
                            ctx.store.write_stream(rel_evidence_path, f_data, module=self.name)
                            artifacts.append(rel_evidence_path)
                            extracted_count += 1

                proc.wait()
                notes.append(f"Se extrajeron {extracted_count} archivos mediante Estrategia A.")
                return ModuleResult(
                    module_name=self.name,
                    status=ModuleStatus.OK if extracted_count > 0 else ModuleStatus.PARTIAL,
                    artifacts=artifacts,
                    notes=notes,
                    duration_seconds=round(time.monotonic() - t0, 3),
                )
            except Exception as e:
                notes.append(f"Fallo en Estrategia A ({e}), recurriendo a Estrategia B.")

        # Estrategia B: Enumerar archivos y extraer con cat
        try:
            cp_find = ctx.runner.run("exec-out", "find", "/sdcard", "-type", "f", timeout=30)
            file_paths = [
                f.strip()
                for f in cp_find.stdout.decode("utf-8", "replace").splitlines()
                if f.strip()
            ]
            extracted_count = 0

            for dev_path in file_paths:
                if ctx.cancel_requested:
                    break
                cp_file = ctx.runner.run("exec-out", "cat", dev_path, timeout=30)
                if cp_file.returncode == 0 and cp_file.stdout:
                    # Derivar nombre relativo
                    rel_sub = dev_path.lstrip("/").replace("sdcard/", "", 1)
                    clean_name = sanitize_relative_path(rel_sub)
                    rel_evidence_path = f"evidence/sdcard/{clean_name}"
                    ctx.store.put_bytes(rel_evidence_path, cp_file.stdout, module=self.name)
                    artifacts.append(rel_evidence_path)
                    extracted_count += 1

            notes.append(f"Se extrajeron {extracted_count} archivos mediante Estrategia B.")
            return ModuleResult(
                module_name=self.name,
                status=ModuleStatus.OK if extracted_count > 0 else ModuleStatus.PARTIAL,
                artifacts=artifacts,
                notes=notes,
                duration_seconds=round(time.monotonic() - t0, 3),
            )
        except Exception as e:
            notes.append(f"Fallo en Estrategia B: {e}")
            return ModuleResult(
                module_name=self.name,
                status=ModuleStatus.FAILED,
                artifacts=artifacts,
                notes=notes,
                duration_seconds=round(time.monotonic() - t0, 3),
            )
