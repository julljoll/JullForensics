"""Pruebas unitarias para capturas forenses en memoria (screenshot.py)."""

from __future__ import annotations

import json
import struct
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from jullforensics.acquisition.screenshot import (
    PNG_SIGNATURE,
    ScreenshotError,
    capture_forensic_screenshot,
)
from jullforensics.adb.runner import AdbRunner
from jullforensics.domain.case import Case, Examiner, LegalBasis, LegalBasisType
from jullforensics.integrity.chained_log import ChainedLog
from jullforensics.storage.evidence_store import EvidenceStore


def _make_dummy_png(width: int = 1080, height: int = 2400) -> bytes:
    # Cabecera PNG + chunk IHDR mínimo
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_chunk = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + b"\x00\x00\x00\x00"
    return PNG_SIGNATURE + ihdr_chunk + b"IDAT" + b"\x00" * 200 + b"IEND\x00\x00\x00\x00"


@pytest.fixture
def store_and_runner(tmp_path: Path) -> tuple[EvidenceStore, AdbRunner]:
    case_dir = tmp_path / "case"
    case = Case(
        case_id="JF-SCREEN",
        title="Screen Test Case",
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
    logger = ChainedLog(
        case_dir / "logs" / "chain.jsonl", b"\x01" * 32, "0" * 64, case.case_id, "p"
    )
    store = EvidenceStore(case_dir, case, logger)

    runner = AdbRunner(serial="EMU123", logger=logger)
    return store, runner


def test_capture_forensic_screenshot_success(
    store_and_runner: tuple[EvidenceStore, AdbRunner],
) -> None:
    store, runner = store_and_runner
    dummy_png = _make_dummy_png(1080, 2400)

    # Mock de subprocess.run para screencap
    runner.run = MagicMock()  # type: ignore[method-assign]
    mock_cp = MagicMock()
    mock_cp.returncode = 0
    mock_cp.stdout = dummy_png
    runner.run.return_value = mock_cp

    meta = capture_forensic_screenshot(runner, store, seq=1, note="Pantalla de inicio")

    assert meta["sequence"] == 1
    assert meta["width"] == 1080
    assert meta["height"] == 2400
    assert "sha256" in meta

    # Comprobar que los archivos existen en disco
    png_path = store.base_dir / str(meta["png_file"])
    json_path = png_path.with_suffix(".json")
    assert png_path.is_file()
    assert json_path.is_file()

    # Comprobar que los metadatos JSON coinciden
    saved_meta = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved_meta["sha256"] == meta["sha256"]
    assert saved_meta["note"] == "Pantalla de inicio"


def test_capture_forensic_screenshot_invalid_output(
    store_and_runner: tuple[EvidenceStore, AdbRunner],
) -> None:
    store, runner = store_and_runner

    runner.run = MagicMock()  # type: ignore[method-assign]
    mock_cp = MagicMock()
    mock_cp.returncode = 1
    mock_cp.stdout = b"Error: Device offline"
    runner.run.return_value = mock_cp

    with pytest.raises(ScreenshotError, match="Salida inválida"):
        capture_forensic_screenshot(runner, store, seq=2)
