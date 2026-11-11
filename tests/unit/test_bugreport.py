"""Pruebas unitarias para BugreportModule."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from jullforensics.acquisition.base import AcquisitionContext, ModuleStatus
from jullforensics.acquisition.bugreport import BugreportModule
from jullforensics.adb.runner import AdbRunner
from jullforensics.domain.case import Case, Examiner, LegalBasis, LegalBasisType
from jullforensics.domain.device import DeviceInfo
from jullforensics.integrity.chained_log import ChainedLog
from jullforensics.storage.evidence_store import EvidenceStore


def test_bugreport_module_success(tmp_path: Path) -> None:
    case = Case(
        case_id="JF-BUG",
        title="Bugreport Test",
        docket_number="DOCK-456",
        agency="Lab",
        examiner=Examiner(name="Perito", badge_or_id="ID12", organization="Org"),
        legal_basis=LegalBasis(
            type=LegalBasisType.ORDEN_JUDICIAL,
            reference="ORD-01",
            authority="Juzgado",
            date_issued="2026-01-01",
        ),
    )
    store = EvidenceStore(
        tmp_path / "store",
        case,
        ChainedLog(tmp_path / "chain.jsonl", b"\x01" * 32, "0" * 64, case.case_id, "p"),
    )
    runner = AdbRunner(serial="D1")
    ctx = AcquisitionContext(runner=runner, store=store, device_info=DeviceInfo(serial="D1"))

    mod = BugreportModule()
    assert len(mod.precheck(ctx)) > 0

    def mock_run(*args, **kwargs):
        if "bugreportz" in args:
            return MagicMock(returncode=0, stdout=b"OK:/data/user_de/0/bugreport.zip\n")
        elif "pull" in args:
            # Crear archivo simulado descargado
            dest = Path(args[3])
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b"PK\x03\x04DUMMY_ZIP_CONTENT")
            return MagicMock(returncode=0, stdout=b"")
        return MagicMock(returncode=0, stdout=b"")

    runner.run = MagicMock(side_effect=mock_run)  # type: ignore[method-assign]
    res = mod.acquire(ctx)

    assert res.status == ModuleStatus.OK
    assert "bugreport/bugreport.zip" in res.artifacts
