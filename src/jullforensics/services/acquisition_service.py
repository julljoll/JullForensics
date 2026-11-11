"""Servicio de orquestación de adquisición forense lógica de Android (ISO/IEC 27037 / RFC 3227)."""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from jullforensics.acquisition.base import (
    AcquisitionContext,
    AcquisitionModule,
    ModuleResult,
    ModuleStatus,
)
from jullforensics.acquisition.bugreport import BugreportModule
from jullforensics.acquisition.content_providers import ContentProvidersModule
from jullforensics.acquisition.device_props import DevicePropsModule
from jullforensics.acquisition.packages import PackagesModule
from jullforensics.acquisition.screenshot import capture_forensic_screenshot
from jullforensics.acquisition.shared_storage import SharedStorageModule
from jullforensics.acquisition.system_dumps import SystemDumpsModule
from jullforensics.domain.case import CaseStatus
from jullforensics.domain.custody import CustodyEvent, CustodyEventType
from jullforensics.reporting.report_generator import ReportGenerator
from jullforensics.storage.tar_container import create_forensic_tar

if TYPE_CHECKING:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from jullforensics.adb.runner import AdbRunner
    from jullforensics.domain.case import Case
    from jullforensics.domain.device import DeviceInfo
    from jullforensics.storage.evidence_store import EvidenceStore


class ProfileType(StrEnum):
    RAPIDA = "RAPIDA"
    ESTANDAR = "ESTANDAR"
    COMPLETA = "COMPLETA"
    CUSTOM = "CUSTOM"


class AcquisitionSummary(BaseModel):
    """Resumen integral de la operación de adquisición lógica."""

    case_id: str
    serial: str
    profile: ProfileType
    status: str
    started_at_utc: str
    completed_at_utc: str
    duration_seconds: float
    total_artifacts: int
    total_bytes: int
    module_results: dict[str, ModuleResult] = Field(default_factory=dict)
    tar_path: str | None = None
    tar_sha256: str | None = None
    tar_sha512: str | None = None
    report_paths: dict[str, str] = Field(default_factory=dict)


class AcquisitionService:
    """Orquesta la ejecución secuencial de módulos según el orden de volatilidad."""

    MODULE_REGISTRY: dict[str, type[AcquisitionModule]] = {
        "device_props": DevicePropsModule,
        "system_dumps": SystemDumpsModule,
        "packages": PackagesModule,
        "content_providers": ContentProvidersModule,
        "shared_storage": SharedStorageModule,
        "bugreport": BugreportModule,
    }

    PROFILE_MODULES: dict[ProfileType, list[str]] = {
        ProfileType.RAPIDA: ["screenshot", "device_props", "packages", "system_dumps"],
        ProfileType.ESTANDAR: [
            "screenshot",
            "device_props",
            "packages",
            "system_dumps",
            "content_providers",
        ],
        ProfileType.COMPLETA: [
            "screenshot",
            "device_props",
            "packages",
            "system_dumps",
            "content_providers",
            "shared_storage",
            "bugreport",
        ],
    }

    def __init__(
        self,
        runner: AdbRunner,
        store: EvidenceStore,
    ) -> None:
        self.runner = runner
        self.store = store

    def get_available_modules(self) -> list[str]:
        return ["screenshot", *list(self.MODULE_REGISTRY.keys())]

    def get_profile_modules(self, profile: ProfileType) -> list[str]:
        return list(self.PROFILE_MODULES.get(profile, []))

    def run_acquisition(
        self,
        case: Case,
        device: DeviceInfo,
        profile: ProfileType = ProfileType.ESTANDAR,
        custom_modules: list[str] | None = None,
        private_key: Ed25519PrivateKey | None = None,
        cancel_event: threading.Event | None = None,
        on_start_cb: Callable[[str, int, int], None] | None = None,
        on_progress_cb: Callable[[str, float, str], None] | None = None,
        on_complete_cb: Callable[[str, ModuleResult], None] | None = None,
    ) -> AcquisitionSummary:
        """Ejecuta el ciclo de vida completo de adquisición lógica forense."""
        # 1. Validación previa de fundamentación legal y examinador (ISO/IEC 27037)
        if not case.examiner.name.strip() or not case.examiner.badge_or_id.strip():
            msg = "Falta examinador pericial válido para iniciar la adquisición"
            raise ValueError(msg)
        if not case.legal_basis.reference.strip() or not case.legal_basis.authority.strip():
            msg = "Falta fundamento jurídico válido (mandato/oficio) requerido por ISO 27037"
            raise ValueError(msg)

        start_time = time.monotonic()
        now_utc = datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")

        # 2. Registrar evento de inicio en la cadena de custodia
        initial_hash = self.store.logger.head_hash
        case.status = CaseStatus.ACQUIRING
        start_event = CustodyEvent(
            event_id=str(uuid.uuid4()),
            ts_utc=now_utc,
            event_type=CustodyEventType.EXTRACTION_STARTED,
            actor=f"{case.examiner.name} ({case.examiner.badge_or_id})",
            action_description=f"Inicio de adquisición lógica Android (perfil {profile})",
            location=case.examiner.organization,
            evidence_hash_sha256=initial_hash,
            notes=f"Dispositivo {device.brand} {device.model} ({device.serial})",
        )
        case.chain_of_custody.append(start_event)
        self.store._save_case_metadata()

        self.store.logger.append(
            "ACQUISITION_STARTED",
            "service",
            {
                "case_id": case.case_id,
                "serial": device.serial,
                "profile": profile,
            },
        )

        # 3. Determinar módulos a ejecutar y ordenarlos por volatilidad
        selected_mod_names: list[str]
        if profile == ProfileType.CUSTOM:
            selected_mod_names = custom_modules or []
        else:
            selected_mod_names = self.get_profile_modules(profile)

        # Ordenar módulos: screenshot primero (volatilidad 0), luego por orden de volatilidad
        def get_volatility_rank(name: str) -> int:
            if name == "screenshot":
                return 0
            cls = self.MODULE_REGISTRY.get(name)
            return cls.order_of_volatility if cls else 999

        sorted_modules = sorted(selected_mod_names, key=get_volatility_rank)
        total_modules = len(sorted_modules)

        ctx = AcquisitionContext(
            runner=self.runner,
            store=self.store,
            device_info=device,
            cancel_requested=False,
        )

        module_results: dict[str, ModuleResult] = {}
        acquisition_status = "COMPLETED"

        # 4. Iterar y ejecutar módulos
        for idx, mod_name in enumerate(sorted_modules, start=1):
            if cancel_event and cancel_event.is_set():
                ctx.cancel_requested = True
                acquisition_status = "CANCELLED"
                self.store.logger.append(
                    "ACQUISITION_CANCELLED_BY_USER",
                    "service",
                    {"cancelled_at_module": mod_name},
                )
                break

            if on_start_cb:
                on_start_cb(mod_name, idx, total_modules)
            if on_progress_cb:
                pct = ((idx - 1) / total_modules) * 100.0
                on_progress_cb(mod_name, pct, f"Iniciando módulo {mod_name}...")

            mod_start = time.monotonic()

            try:
                if mod_name == "screenshot":
                    # Captura de pantalla forense inicial
                    sc_res = capture_forensic_screenshot(
                        self.runner,
                        self.store,
                        seq=1,
                        note="Captura forense inicial de pantalla al conectar",
                    )
                    mod_dur = time.monotonic() - mod_start
                    png_path = str(sc_res.get("png_file", ""))
                    json_path = "screenshots/screenshot_0001.json"
                    res = ModuleResult(
                        module_name="screenshot",
                        status=ModuleStatus.OK,
                        artifacts=[png_path, json_path],
                        notes=["Captura inicial procesada en RAM con hash anticipado"],
                        duration_seconds=mod_dur,
                    )
                else:
                    mod_cls = self.MODULE_REGISTRY.get(mod_name)
                    if mod_cls is None:
                        res = ModuleResult(
                            module_name=mod_name,
                            status=ModuleStatus.SKIPPED,
                            notes=[f"Módulo '{mod_name}' desconocido"],
                        )
                    else:
                        module_inst = mod_cls()
                        warnings = module_inst.precheck(ctx)
                        res = module_inst.acquire(ctx)
                        if warnings:
                            res.notes.extend(warnings)

                module_results[mod_name] = res
                if on_complete_cb:
                    on_complete_cb(mod_name, res)

                if res.status == ModuleStatus.FAILED:
                    acquisition_status = "PARTIAL"

            except Exception as exc:  # noqa: BLE001
                mod_dur = time.monotonic() - mod_start
                res = ModuleResult(
                    module_name=mod_name,
                    status=ModuleStatus.FAILED,
                    notes=[f"Excepción no controlada: {exc}"],
                    duration_seconds=mod_dur,
                )
                module_results[mod_name] = res
                acquisition_status = "PARTIAL"
                self.store.logger.append(
                    "MODULE_EXECUTION_EXCEPTION",
                    mod_name,
                    {"error": str(exc)},
                )
                if on_complete_cb:
                    on_complete_cb(mod_name, res)

        # 5. Generar dictámenes periciales (JSON, HTML, PDF)
        if on_progress_cb:
            on_progress_cb("reporting", 90.0, "Generando dictámenes periciales (PDF/HTML/JSON)...")

        report_gen = ReportGenerator(case, device, self.store)
        report_results = report_gen.generate_all()
        report_paths = {k: v["path"] for k, v in report_results.items()}

        # 6. Guardar snapshot del log encadenado en el store
        log_bytes = self.store.logger.log_path.read_bytes()
        self.store.put_bytes("logs/chained_log.jsonl", log_bytes, module="chained_log")

        # 7. Actualizar manifiesto y generar sumas antes de empaquetar en TAR
        self.store.generate_manifest_and_sums()

        # 8. Empaquetar todo el caso en contenedor forense JF-TAR
        if on_progress_cb:
            on_progress_cb("container", 95.0, "Empaquetando evidencia en contenedor JF-TAR...")

        tar_path, tar_digests = create_forensic_tar(
            store=self.store,
            serial=device.serial,
            private_key=private_key,
        )

        tar_sha256 = tar_digests.get("sha256", "")
        tar_sha512 = tar_digests.get("sha512", "")

        # 9. Cerrar cadena de custodia
        end_utc = datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
        seal_event = CustodyEvent(
            event_id=str(uuid.uuid4()),
            ts_utc=end_utc,
            event_type=CustodyEventType.CONTAINER_SEALED,
            actor=f"{case.examiner.name} ({case.examiner.badge_or_id})",
            action_description=f"Contenedor forense empaquetado y sellado: {tar_path.name}",
            location=case.examiner.organization,
            evidence_hash_sha256=tar_sha256,
            notes=f"SHA-256: {tar_sha256}",
        )
        case.chain_of_custody.append(seal_event)
        case.status = CaseStatus.COMPLETED if acquisition_status == "COMPLETED" else CaseStatus.OPEN
        self.store._save_case_metadata()

        # 10. Aplicar permisos de solo lectura al caso en disco (0440)
        self.store.seal_case()

        duration = time.monotonic() - start_time
        total_bytes = sum(a.size_bytes for a in self.store.artifacts)

        if on_progress_cb:
            on_progress_cb("completed", 100.0, "Adquisición finalizada y sellada con éxito.")

        return AcquisitionSummary(
            case_id=case.case_id,
            serial=device.serial,
            profile=profile,
            status=acquisition_status,
            started_at_utc=now_utc,
            completed_at_utc=end_utc,
            duration_seconds=duration,
            total_artifacts=len(self.store.artifacts),
            total_bytes=total_bytes,
            module_results=module_results,
            tar_path=str(tar_path),
            tar_sha256=tar_sha256,
            tar_sha512=tar_sha512,
            report_paths=report_paths,
        )
