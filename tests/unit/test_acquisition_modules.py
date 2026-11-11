"""Pruebas unitarias para módulos de adquisición de evidencias (plugins)."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from jullforensics.acquisition.base import AcquisitionContext, ModuleStatus
from jullforensics.acquisition.content_providers import ContentProvidersModule
from jullforensics.acquisition.device_props import DevicePropsModule
from jullforensics.acquisition.packages import PackagesModule
from jullforensics.acquisition.shared_storage import SharedStorageModule
from jullforensics.acquisition.system_dumps import SystemDumpsModule
from jullforensics.adb.runner import AdbRunner
from jullforensics.domain.case import Case, Examiner, LegalBasis, LegalBasisType
from jullforensics.domain.device import DeviceInfo
from jullforensics.integrity.chained_log import ChainedLog
from jullforensics.storage.evidence_store import EvidenceStore


@pytest.fixture
def acq_context(tmp_path: Path) -> AcquisitionContext:
    case = Case(
        case_id="JF-MODS",
        title="Modules Test Case",
        docket_number="DOCK-123",
        agency="Laboratorio Central",
        examiner=Examiner(name="Perito Forense", badge_or_id="PER-001", organization="Policia"),
        legal_basis=LegalBasis(
            type=LegalBasisType.ORDEN_JUDICIAL,
            reference="ORD-2026-001",
            authority="Juzgado 1",
            date_issued="2026-01-01",
        ),
    )
    logger = ChainedLog(tmp_path / "chain.jsonl", b"\x01" * 32, "0" * 64, case.case_id, "p")
    store = EvidenceStore(tmp_path / "store", case, logger)
    runner = AdbRunner(serial="DEV1")
    dev_info = DeviceInfo(serial="DEV1", model="TestPhone", sdk_version=34)
    return AcquisitionContext(runner=runner, store=store, device_info=dev_info)


def test_device_props_module(acq_context: AcquisitionContext) -> None:
    mod = DevicePropsModule()
    acq_context.runner.run = MagicMock()  # type: ignore[method-assign]
    mock_cp = MagicMock(returncode=0, stdout=b"[ro.product.model]: [TestPhone]\n")
    acq_context.runner.run.return_value = mock_cp

    res = mod.acquire(acq_context)
    assert res.status == ModuleStatus.OK
    assert "device/getprop.txt" in res.artifacts
    assert "device/clock_offset.json" in res.artifacts


def test_packages_module(acq_context: AcquisitionContext) -> None:
    mod = PackagesModule()
    raw_pm = b"package:/data/app/~~/base.apk=com.example.app versionCode:42 installer=com.android.vending uid:10245\n"
    acq_context.runner.run = MagicMock(return_value=MagicMock(returncode=0, stdout=raw_pm))  # type: ignore[method-assign]

    res = mod.acquire(acq_context)
    assert res.status == ModuleStatus.OK
    assert "apps/packages.csv" in res.artifacts

    csv_content = (acq_context.store.base_dir / "apps/packages.csv").read_text(encoding="utf-8")
    assert "com.example.app" in csv_content
    assert "42" in csv_content


def test_system_dumps_module(acq_context: AcquisitionContext) -> None:
    mod = SystemDumpsModule()
    acq_context.runner.run = MagicMock(return_value=MagicMock(returncode=0, stdout=b"DUMP DATA"))  # type: ignore[method-assign]

    res = mod.acquire(acq_context)
    assert res.status == ModuleStatus.OK
    assert len(res.artifacts) > 0


def test_content_providers_module(acq_context: AcquisitionContext) -> None:
    mod = ContentProvidersModule()
    acq_context.runner.run = MagicMock(
        return_value=MagicMock(returncode=0, stdout=b"Row 0: name=John", stderr=b"")
    )  # type: ignore[method-assign]

    res = mod.acquire(acq_context)
    assert res.status == ModuleStatus.OK
    assert any("contacts.txt" in a for a in res.artifacts)


def test_shared_storage_module_strategy_b(acq_context: AcquisitionContext) -> None:
    mod = SharedStorageModule()
    # Mock no toybox tar -> fallback to Strategy B
    mod._supports_strategy_a = MagicMock(return_value=False)  # type: ignore[method-assign]

    def mock_run(*args, **kwargs):
        if "find" in args:
            return MagicMock(returncode=0, stdout=b"/sdcard/DCIM/photo.jpg\n")
        elif "cat" in args:
            return MagicMock(returncode=0, stdout=b"JPEG_BYTES_12345")
        return MagicMock(returncode=0, stdout=b"")

    acq_context.runner.run = MagicMock(side_effect=mock_run)  # type: ignore[method-assign]

    res = mod.acquire(acq_context)
    assert res.status == ModuleStatus.OK
    assert "evidence/sdcard/DCIM/photo.jpg" in res.artifacts


def test_shared_storage_module_strategy_a(acq_context: AcquisitionContext) -> None:
    mod = SharedStorageModule()
    mod._supports_strategy_a = MagicMock(return_value=True)  # type: ignore[method-assign]

    # Crear un flujo tar en memoria simulando la salida de toybox tar
    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode="w") as t:
        ti = tarfile.TarInfo("DCIM/toybox_img.jpg")
        ti.size = 11
        t.addfile(ti, io.BytesIO(b"TOYBOX_DATA"))

    tar_bytes = tar_buf.getvalue()
    mock_proc = MagicMock()
    mock_proc.stdout = io.BytesIO(tar_bytes)
    mock_proc.wait = MagicMock()
    acq_context.runner.run_stream = MagicMock(return_value=mock_proc)  # type: ignore[method-assign]

    res = mod.acquire(acq_context)
    assert res.status == ModuleStatus.OK
    assert any("toybox_img.jpg" in a for a in res.artifacts)
