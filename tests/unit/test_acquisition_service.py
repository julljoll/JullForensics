"""Pruebas unitarias para el orquestador de adquisición forense (AcquisitionService)."""

from __future__ import annotations

import struct
import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from jullforensics.acquisition.screenshot import PNG_SIGNATURE
from jullforensics.adb.runner import AdbRunner
from jullforensics.domain.case import Case, CaseStatus, Examiner, LegalBasis, LegalBasisType
from jullforensics.domain.custody import CustodyEventType
from jullforensics.domain.device import DeviceInfo
from jullforensics.integrity.chained_log import ChainedLog
from jullforensics.integrity.signing import Verifier
from jullforensics.services.acquisition_service import (
    AcquisitionService,
    ProfileType,
)
from jullforensics.storage.evidence_store import EvidenceStore


def _make_dummy_png(width: int = 1080, height: int = 2400) -> bytes:
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_chunk = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + b"\x00\x00\x00\x00"
    return PNG_SIGNATURE + ihdr_chunk + b"IDAT" + b"\x00" * 200 + b"IEND\x00\x00\x00\x00"


@pytest.fixture
def service_env(tmp_path: Path) -> tuple[AcquisitionService, Case, DeviceInfo, EvidenceStore]:
    examiner = Examiner(
        name="Laura Gómez",
        badge_or_id="PER-7721",
        organization="Sección de Informática Forense",
        email="lgomez@forense.gob",
    )
    legal_basis = LegalBasis(
        type=LegalBasisType.ORDEN_JUDICIAL,
        reference="ORD-882-2026",
        authority="Juzgado de Instrucción 5",
        date_issued="2026-11-10",
        document_hash_sha256="d" * 64,
    )
    case = Case(
        case_id="JF-2026-SVC1",
        title="Caso de Prueba de Servicio",
        docket_number="CAUSA-2026-99",
        agency="Guardia Civil",
        examiner=examiner,
        legal_basis=legal_basis,
        device_description="Xiaomi Redmi Note 12 azul",
    )
    logger = ChainedLog(tmp_path / "chain.jsonl", b"\x02" * 32, "0" * 64, case.case_id, "laura")
    store = EvidenceStore(tmp_path / "case_dir", case, logger)
    runner = AdbRunner(serial="XIAOMI001")
    dev_info = DeviceInfo(
        serial="XIAOMI001",
        model="Redmi Note 12",
        brand="xiaomi",
        manufacturer="Xiaomi",
        android_version="13",
        sdk_version=33,
    )
    service = AcquisitionService(runner=runner, store=store)
    return service, case, dev_info, store


def test_service_module_registry_and_profiles(
    service_env: tuple[AcquisitionService, Case, DeviceInfo, EvidenceStore],
) -> None:
    service, _, _, _ = service_env
    all_mods = service.get_available_modules()
    assert "screenshot" in all_mods
    assert "device_props" in all_mods
    assert "content_providers" in all_mods

    rapida = service.get_profile_modules(ProfileType.RAPIDA)
    assert rapida == ["screenshot", "device_props", "packages", "system_dumps"]

    completa = service.get_profile_modules(ProfileType.COMPLETA)
    assert "shared_storage" in completa
    assert "bugreport" in completa


def test_service_invalid_case_raises(
    service_env: tuple[AcquisitionService, Case, DeviceInfo, EvidenceStore],
) -> None:
    service, case, dev, _ = service_env

    # 1. Sin examinador válido
    bad_case = case.model_copy(deep=True)
    bad_case.examiner.name = ""
    with pytest.raises(ValueError, match="Falta examinador"):
        service.run_acquisition(bad_case, dev)

    # 2. Sin fundamento legal
    bad_case2 = case.model_copy(deep=True)
    bad_case2.legal_basis.reference = ""
    with pytest.raises(ValueError, match="Falta fundamento"):
        service.run_acquisition(bad_case2, dev)


def test_service_run_acquisition_full_flow(
    service_env: tuple[AcquisitionService, Case, DeviceInfo, EvidenceStore],
) -> None:
    service, case, dev, store = service_env

    # Simular respuestas ADB
    dummy_png = _make_dummy_png()
    dummy_prop = b"[ro.product.model]: [Redmi Note 12]\n[ro.build.version.release]: [13]\n"
    dummy_pkgs = b"package:com.android.settings\npackage:com.whatsapp\n"
    dummy_dumpsys = b"DUMP OF SERVICE battery:\n  level: 95\n"

    def mock_adb_run(*args: str, **kwargs: object) -> MagicMock:
        cmd = args[0] if args else ""
        if cmd == "exec-out" and len(args) > 1 and args[1] == "screencap":
            return MagicMock(returncode=0, stdout=dummy_png, stderr=b"")
        if cmd == "shell":
            subcmd = args[1] if len(args) > 1 else ""
            if subcmd == "getprop":
                return MagicMock(returncode=0, stdout=dummy_prop, stderr=b"")
            if subcmd == "pm":
                return MagicMock(returncode=0, stdout=dummy_pkgs, stderr=b"")
            if subcmd == "dumpsys":
                return MagicMock(returncode=0, stdout=dummy_dumpsys, stderr=b"")
            return MagicMock(returncode=0, stdout=b"dummy output\n", stderr=b"")
        return MagicMock(returncode=0, stdout=b"", stderr=b"")

    service.runner.run = MagicMock(side_effect=mock_adb_run)  # type: ignore[method-assign]

    started_mods: list[str] = []
    completed_mods: list[str] = []
    progress_records: list[tuple[str, float]] = []

    def on_start(mod: str, idx: int, total: int) -> None:
        started_mods.append(mod)

    def on_progress(mod: str, pct: float, msg: str) -> None:
        progress_records.append((mod, pct))

    def on_complete(mod: str, res: object) -> None:
        completed_mods.append(mod)

    summary = service.run_acquisition(
        case=case,
        device=dev,
        profile=ProfileType.RAPIDA,
        on_start_cb=on_start,
        on_progress_cb=on_progress,
        on_complete_cb=on_complete,
    )

    assert summary.status == "COMPLETED"
    assert summary.case_id == case.case_id
    assert summary.serial == dev.serial
    assert summary.total_artifacts > 0
    assert summary.tar_path is not None
    assert summary.tar_sha256 is not None
    assert summary.tar_sha512 is not None
    assert Path(summary.tar_path).is_file()

    # Verificar que los módulos se ejecutaron en el orden adecuado (screenshot primero)
    assert started_mods[0] == "screenshot"
    assert "device_props" in started_mods
    assert len(completed_mods) == 4

    # Verificar eventos de cadena de custodia
    event_types = [e.event_type for e in case.chain_of_custody]
    assert CustodyEventType.EXTRACTION_STARTED in event_types
    assert CustodyEventType.CONTAINER_SEALED in event_types
    assert case.status == CaseStatus.COMPLETED

    # Verificar que se generaron los reportes
    assert "json" in summary.report_paths
    assert "html" in summary.report_paths
    assert "pdf" in summary.report_paths


def test_service_run_acquisition_with_ed25519_signing(
    service_env: tuple[AcquisitionService, Case, DeviceInfo, EvidenceStore],
) -> None:
    service, case, dev, store = service_env

    # Generar par de claves para firma
    priv_key = ed25519.Ed25519PrivateKey.generate()
    pub_key = priv_key.public_key()

    dummy_prop = b"[ro.product.model]: [Redmi]\n"
    service.runner.run = MagicMock(  # type: ignore[method-assign]
        return_value=MagicMock(returncode=0, stdout=dummy_prop, stderr=b"")
    )

    summary = service.run_acquisition(
        case=case,
        device=dev,
        profile=ProfileType.CUSTOM,
        custom_modules=["device_props"],
        private_key=priv_key,
    )

    assert summary.status == "COMPLETED"
    tar_path = Path(summary.tar_path)  # type: ignore[arg-type]
    sig_sidecar = tar_path.with_suffix(".tar.sig")
    assert sig_sidecar.is_file()

    # Verificar firma con Verifier
    tar_bytes = tar_path.read_bytes()
    sig_bytes = sig_sidecar.read_bytes()
    assert Verifier.verify(pub_key, tar_bytes, sig_bytes) is True


def test_service_cancellation(
    service_env: tuple[AcquisitionService, Case, DeviceInfo, EvidenceStore],
) -> None:
    service, case, dev, _ = service_env

    cancel_evt = threading.Event()
    cancel_evt.set()  # Cancelado antes de comenzar el bucle

    dummy_prop = b"[ro.product.model]: [Redmi]\n"
    service.runner.run = MagicMock(  # type: ignore[method-assign]
        return_value=MagicMock(returncode=0, stdout=dummy_prop, stderr=b"")
    )

    summary = service.run_acquisition(
        case=case,
        device=dev,
        profile=ProfileType.RAPIDA,
        cancel_event=cancel_evt,
    )

    assert summary.status == "CANCELLED"
    assert len(summary.module_results) == 0


def test_service_module_exception_handling(
    service_env: tuple[AcquisitionService, Case, DeviceInfo, EvidenceStore],
) -> None:
    service, case, dev, _ = service_env

    # Simular fallo en ejecución ADB
    service.runner.run = MagicMock(side_effect=RuntimeError("ADB communication crash"))  # type: ignore[method-assign]

    summary = service.run_acquisition(
        case=case,
        device=dev,
        profile=ProfileType.CUSTOM,
        custom_modules=["device_props"],
    )

    assert summary.status == "PARTIAL"
    assert "device_props" in summary.module_results
    assert summary.module_results["device_props"].status.value == "FAILED"
