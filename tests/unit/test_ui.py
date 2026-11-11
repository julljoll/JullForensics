"""Pruebas unitarias para componentes de la interfaz de usuario brutalista (PySide6 / pytest-qt)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

# Asegurar entorno headless offscreen antes de importar widgets
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from jullforensics.domain.artifact import Artifact, ArtifactStatus
from jullforensics.domain.case import Case, Examiner, LegalBasis, LegalBasisType
from jullforensics.domain.device import DeviceInfo
from jullforensics.integrity.chained_log import LogEntry
from jullforensics.ui.main_window import MainWindow
from jullforensics.ui.theme.qss import get_application_stylesheet
from jullforensics.ui.theme.tokens import COLOR_ACCENT, COLOR_BG, COLOR_INK, FONT_FAMILY
from jullforensics.ui.views.acquisition_view import AcquisitionView
from jullforensics.ui.views.case_view import CaseView
from jullforensics.ui.views.custody_view import CustodyView
from jullforensics.ui.views.device_view import DeviceView
from jullforensics.ui.views.integrity_view import IntegrityView
from jullforensics.ui.views.report_view import ReportView
from jullforensics.ui.views.screenshot_view import ScreenshotView
from jullforensics.ui.widgets.log_ticker import LogTicker
from jullforensics.ui.widgets.status_badge import StatusBadge


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app  # type: ignore[return-value]


def test_theme_tokens_and_stylesheet() -> None:
    assert COLOR_BG == "#F4F4F0"
    assert COLOR_INK == "#0A0A0A"
    assert COLOR_ACCENT == "#FFE600"
    assert "monospace" in FONT_FAMILY

    css = get_application_stylesheet()
    assert "QPushButton" in css
    assert "QTabWidget" in css
    assert "QProgressBar" in css
    assert COLOR_ACCENT in css


def test_status_badge(qapp: QApplication) -> None:
    badge = StatusBadge()
    assert "SIN DISPOSITIVO" in badge.text()

    dev = DeviceInfo(serial="DEV123", model="TestPixel", brand="Google")
    badge.set_connected(dev)
    assert "CONECTADO" in badge.text()
    assert "DEV123" in badge.text()

    badge.set_unauthorized("DEV123")
    assert "NO AUTORIZADO" in badge.text()

    badge.set_error("ADB Server down")
    assert "ERROR ADB" in badge.text()


def test_log_ticker(qapp: QApplication) -> None:
    ticker = LogTicker()
    entry = LogEntry(
        seq=12,
        ts_utc="2026-11-11T20:00:00Z",
        case_id="JF-001",
        examiner="Perito",
        event="EXTRACTION_STARTED",
        module="core",
        data={"profile": "RAPIDA"},
        prev_hash="0" * 64,
        entry_hash="a" * 64,
        hmac="b" * 64,
    )
    ticker.update_entry(entry)
    assert "#0012" in ticker._lbl_event.text()
    assert "EXTRACTION_STARTED" in ticker._lbl_event.text()
    assert "aaaaaaaa" in ticker._lbl_hash.text()


def test_case_view(qapp: QApplication) -> None:
    view = CaseView()
    case = view.get_case()
    assert case is not None
    assert case.case_id == "JF-2026-0001"
    assert "VALIDADO" in view._lbl_status.text()

    # Probar setter
    new_case = case.model_copy()
    new_case.case_id = "JF-2026-9999"
    view.set_case(new_case)
    assert view.get_case().case_id == "JF-2026-9999"  # type: ignore[union-attr]


def test_device_view(qapp: QApplication) -> None:
    view = DeviceView()
    dev = DeviceInfo(
        serial="ADB-SER-99",
        model="Galaxy S23",
        brand="Samsung",
        manufacturer="Samsung",
        android_version="14",
        sdk_version=34,
        security_patch="2026-10-01",
        clock_offset_seconds=-0.45,
    )
    view.update_device(dev)
    assert view._table.rowCount() > 0

    view.update_device(None)
    assert view._table.rowCount() == 0


def test_screenshot_view(qapp: QApplication) -> None:
    view = ScreenshotView()
    meta = {
        "ts_before_utc": "2026-11-11T20:00:00Z",
        "foreground_activity": "com.android.settings/.MainSettings",
        "security_warning": False,
        "sha256": "c" * 64,
        "size_bytes": 1024,
        "width": 1080,
        "height": 2400,
        "note": "Test capture",
    }
    view.add_screenshot(meta)
    assert view._table.rowCount() == 1

    received_note: list[str] = []
    view.capture_requested.connect(received_note.append)
    view._in_note.setText("Nota manual")
    view._on_capture_click()
    assert received_note == ["Nota manual"]


def test_acquisition_view(qapp: QApplication) -> None:
    view = AcquisitionView()
    assert view._cb_profile.count() == 4

    # Cambiar a rápida
    view._cb_profile.setCurrentIndex(1)
    assert view._checkboxes["screenshot"].isChecked() is True
    assert view._checkboxes["shared_storage"].isChecked() is False

    started: list[tuple[object, list[str]]] = []
    view.start_requested.connect(lambda p, m: started.append((p, m)))
    view._on_start_click()
    assert len(started) == 1
    assert "screenshot" in started[0][1]


def test_integrity_view(qapp: QApplication) -> None:
    view = IntegrityView()
    art1 = Artifact(
        relative_path="device/getprop.txt",
        size_bytes=450,
        sha256="d" * 64,
        sha512="e" * 128,
        module="device_props",
        acquired_at_utc="2026-11-11T20:00:00Z",
        status=ArtifactStatus.VERIFIED,
    )
    view._all_artifacts = [art1]
    view._apply_filter()
    assert view._table.rowCount() == 1

    # Filtrar por algo que no coincida
    view._in_filter.setText("non_existent")
    assert view._table.rowCount() == 0


def test_custody_view(qapp: QApplication) -> None:
    view = CustodyView()
    case = Case(
        case_id="JF-CUST",
        title="Custody Case",
        docket_number="123",
        agency="Lab",
        examiner=Examiner(name="Perito", badge_or_id="123", organization="Lab"),
        legal_basis=LegalBasis(
            type=LegalBasisType.ORDEN_JUDICIAL,
            reference="ORD-1",
            authority="Juzgado",
            date_issued="2026-01-01",
        ),
    )
    view.update_case(case)
    assert view._table.rowCount() == 0

    view._in_action.setText("Recepción en juzgado")
    view._on_add_click()
    assert len(case.chain_of_custody) == 1
    assert view._table.rowCount() == 1


def test_report_view(qapp: QApplication) -> None:
    view = ReportView()
    view.update_reports(None)
    assert view._btn_open_html.isEnabled() is False


def test_main_window_initialization(qapp: QApplication, tmp_path: Path) -> None:
    win = MainWindow(base_dir=tmp_path / "cases", start_monitor=False)
    assert win._tabs.count() == 7
    case, store = win._ensure_case_and_store()
    assert case.case_id == "JF-2026-0001"
    assert store.base_dir.is_dir()

    # Probar señales de dispositivo en MainWindow
    dev = DeviceInfo(serial="DEV-TEST", model="TestModel", brand="TestBrand")
    win._on_device_connected_signal(dev)
    assert win._active_device == dev
    assert "CONECTADO" in win._badge.text()

    win._on_device_state_changed_signal("DEV-TEST", "unauthorized")
    assert "NO AUTORIZADO" in win._badge.text()

    win._on_device_disconnected_signal("DEV-TEST")
    assert win._active_device is None
    assert "SIN DISPOSITIVO" in win._badge.text()

    win.close()


def test_device_signals_bridge(qapp: QApplication) -> None:
    from jullforensics.ui.adapters.device_signals import DeviceSignalsBridge

    bridge = DeviceSignalsBridge()
    conn_received: list[DeviceInfo] = []
    disc_received: list[str] = []
    state_received: list[tuple[str, str]] = []

    bridge.device_connected.connect(conn_received.append)
    bridge.device_disconnected.connect(disc_received.append)
    bridge.device_state_changed.connect(lambda s, st: state_received.append((s, st)))

    dev = DeviceInfo(serial="D1", model="M1")
    bridge.on_device_connected(dev)
    bridge.on_device_disconnected("D1")
    bridge.on_device_state_changed("D1", "device")

    assert len(conn_received) == 1
    assert disc_received == ["D1"]
    assert state_received == [("D1", "device")]


def test_acquisition_worker(qapp: QApplication) -> None:
    from unittest.mock import MagicMock

    from jullforensics.acquisition.base import ModuleResult, ModuleStatus
    from jullforensics.services.acquisition_service import AcquisitionSummary, ProfileType
    from jullforensics.ui.adapters.worker import AcquisitionWorker

    mock_service = MagicMock()
    mock_summary = AcquisitionSummary(
        case_id="JF-WORKER",
        serial="DEV1",
        profile=ProfileType.RAPIDA,
        status="COMPLETED",
        started_at_utc="2026-01-01T00:00:00Z",
        completed_at_utc="2026-01-01T00:01:00Z",
        duration_seconds=60.0,
        total_artifacts=5,
        total_bytes=1024,
    )
    mock_service.run_acquisition.return_value = mock_summary

    case = Case(
        case_id="JF-WORKER",
        title="Worker Test",
        docket_number="123",
        agency="Lab",
        examiner=Examiner(name="Perito", badge_or_id="123", organization="Lab"),
        legal_basis=LegalBasis(
            type=LegalBasisType.ORDEN_JUDICIAL,
            reference="ORD-1",
            authority="Juzgado",
            date_issued="2026-01-01",
        ),
    )
    dev = DeviceInfo(serial="DEV1")
    worker = AcquisitionWorker(
        service=mock_service,
        case=case,
        device=dev,
        profile=ProfileType.RAPIDA,
    )

    finished_summaries: list[AcquisitionSummary] = []
    worker.acquisition_finished.connect(finished_summaries.append)

    worker.run()
    assert len(finished_summaries) == 1
    assert finished_summaries[0].case_id == "JF-WORKER"

    # Probar callbacks
    worker._on_start("screenshot", 1, 3)
    worker._on_progress("screenshot", 33.3, "capturando")
    worker._on_complete(
        "screenshot",
        ModuleResult(module_name="screenshot", status=ModuleStatus.OK),
    )
    worker.cancel()
    assert worker._cancel_event.is_set()


def test_report_view_with_store_files(qapp: QApplication, tmp_path: Path) -> None:
    from jullforensics.integrity.chained_log import ChainedLog
    from jullforensics.storage.evidence_store import EvidenceStore

    case = Case(
        case_id="JF-REP",
        title="Report Case",
        docket_number="123",
        agency="Lab",
        examiner=Examiner(name="Perito", badge_or_id="123", organization="Lab"),
        legal_basis=LegalBasis(
            type=LegalBasisType.ORDEN_JUDICIAL,
            reference="ORD-1",
            authority="Juzgado",
            date_issued="2026-01-01",
        ),
    )
    logger = ChainedLog(tmp_path / "chain.jsonl", key=b"\x00" * 32)
    store = EvidenceStore(tmp_path / "case_dir", case, logger)

    store.put_bytes("reports/report.html", b"<h1>Dictamen</h1>", "reporting")
    store.put_bytes("reports/report.pdf", b"%PDF-1.4 dummy", "reporting")
    store.put_bytes("reports/report.json", b"{}", "reporting")

    view = ReportView()
    view.update_reports(store)

    assert view._btn_open_html.isEnabled() is True
    assert view._btn_open_pdf.isEnabled() is True


def test_main_cli_entrypoint(monkeypatch: pytest.MonkeyPatch) -> None:
    from jullforensics.__main__ import main, parse_args

    monkeypatch.setattr("sys.argv", ["jullforensics", "--offscreen"])
    args = parse_args()
    assert args.offscreen is True

    rc = main()
    assert rc == 0
