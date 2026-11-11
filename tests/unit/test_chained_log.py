"""Pruebas unitarias y de robustez para el registro encadenado inalterable (ChainedLog)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from jullforensics.integrity.chained_log import ChainedLog, verify_chain


@pytest.fixture
def dummy_key() -> bytes:
    return b"\x01" * 32


@pytest.fixture
def genesis_hash() -> str:
    return "0000000000000000000000000000000000000000000000000000000000000000"


def test_chained_log_creation_and_append(
    tmp_path: Path, dummy_key: bytes, genesis_hash: str
) -> None:
    log_file = tmp_path / "logs" / "chain.jsonl"
    logger = ChainedLog(log_file, dummy_key, genesis_hash, "JF-2026-TEST", "perito_forense")

    e1 = logger.append("SESSION_START", "system", {"version": "0.1.0"})
    e2 = logger.append("DEVICE_CONNECTED", "adb", {"serial": "EMU12345"})

    assert e1.seq == 1
    assert e1.prev_hash == genesis_hash
    assert e2.seq == 2
    assert e2.prev_hash == e1.entry_hash

    ok, msg, count = verify_chain(log_file, dummy_key, genesis_hash)
    assert ok is True
    assert count == 2

    # Reabrir el log existente y continuar encadenando
    logger_resumed = ChainedLog(log_file, dummy_key, genesis_hash, "JF-2026-TEST", "perito_forense")
    assert logger_resumed.current_seq == 2
    assert logger_resumed.last_hash == e2.entry_hash
    e3 = logger_resumed.append("ARTIFACT_ACQUIRED", "adb", {"id": 3})
    assert e3.seq == 3
    assert e3.prev_hash == e2.entry_hash

    ok, _, count = verify_chain(log_file, dummy_key, genesis_hash)
    assert ok is True
    assert count == 3


def test_chained_log_corrupt_non_json_line(
    tmp_path: Path, dummy_key: bytes, genesis_hash: str
) -> None:
    log_file = tmp_path / "corrupt.jsonl"
    log_file.write_text("NOT A VALID JSON LINE\n", encoding="utf-8")
    ok, msg, count = verify_chain(log_file, dummy_key, genesis_hash)
    assert ok is False
    assert "no es un JSON válido" in msg


def test_chained_log_empty_file(tmp_path: Path) -> None:
    empty_file = tmp_path / "empty.jsonl"
    empty_file.write_text("", encoding="utf-8")
    ok, msg, count = verify_chain(empty_file)
    assert ok is False
    assert "vacío" in msg


def test_chained_log_detects_payload_tampering(
    tmp_path: Path, dummy_key: bytes, genesis_hash: str
) -> None:
    log_file = tmp_path / "logs" / "chain.jsonl"
    logger = ChainedLog(log_file, dummy_key, genesis_hash, "JF-2026-TEST", "perito_forense")

    logger.append("ARTIFACT_ACQUIRED", "shared_storage", {"file": "evidence1.jpg", "size": 1024})
    logger.append("ARTIFACT_ACQUIRED", "shared_storage", {"file": "evidence2.jpg", "size": 2048})

    # Alterar un solo carácter en la primera línea
    lines = log_file.read_text(encoding="utf-8").splitlines()
    corrupted_entry = json.loads(lines[0])
    corrupted_entry["data"]["size"] = 999999  # alteración
    lines[0] = json.dumps(corrupted_entry)
    log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ok, msg, count = verify_chain(log_file, dummy_key, genesis_hash)
    assert ok is False
    assert "adulterado" in msg or "Ruptura" in msg or "HMAC" in msg


def test_chained_log_detects_deleted_entry(
    tmp_path: Path, dummy_key: bytes, genesis_hash: str
) -> None:
    log_file = tmp_path / "logs" / "chain.jsonl"
    logger = ChainedLog(log_file, dummy_key, genesis_hash, "JF-2026-TEST", "perito_forense")

    logger.append("EVENT_1", "mod", {"x": 1})
    logger.append("EVENT_2", "mod", {"x": 2})
    logger.append("EVENT_3", "mod", {"x": 3})

    # Eliminar la segunda entrada
    lines = log_file.read_text(encoding="utf-8").splitlines()
    del lines[1]
    log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ok, msg, count = verify_chain(log_file, dummy_key, genesis_hash)
    assert ok is False
    assert "Secuencia alterada" in msg or "Ruptura de cadena" in msg


def test_chained_log_detects_invalid_hmac(
    tmp_path: Path, dummy_key: bytes, genesis_hash: str
) -> None:
    log_file = tmp_path / "logs" / "chain.jsonl"
    logger = ChainedLog(log_file, dummy_key, genesis_hash, "JF-2026-TEST", "perito_forense")

    logger.append("EVENT_1", "mod", {"x": 1})

    wrong_key = b"\x02" * 32
    ok, msg, count = verify_chain(log_file, wrong_key, genesis_hash)
    assert ok is False
    assert "HMAC inválido" in msg


@given(st.text(min_size=1, max_size=100))
@settings(max_examples=25, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_hypothesis_tamper_any_field(tmp_path: Path, mutation: str) -> None:
    key = b"\x01" * 32
    genesis = "0" * 64
    log_file = tmp_path / f"chain_{hash(mutation)}.jsonl"
    logger = ChainedLog(log_file, key, genesis, "JF-HYPO", "examiner")

    logger.append("START", "core", {"meta": "val1"})
    logger.append("END", "core", {"meta": "val2"})

    lines = log_file.read_text(encoding="utf-8").splitlines()
    data = json.loads(lines[0])
    if data["data"]["meta"] != mutation:
        data["data"]["meta"] = mutation
        lines[0] = json.dumps(data)
        log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        ok, _, _ = verify_chain(log_file, key, genesis)
        assert ok is False
