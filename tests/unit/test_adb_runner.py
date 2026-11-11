"""Pruebas unitarias para AdbRunner, auditoría en log y control de ejecución."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jullforensics.adb.allowlist import ForbiddenCommandError, IntrusiveCommandUnauthorizedError
from jullforensics.adb.runner import AdbRunner
from jullforensics.integrity.chained_log import ChainedLog


@pytest.fixture
def dummy_logger(tmp_path: Path) -> ChainedLog:
    log_file = tmp_path / "chain.jsonl"
    return ChainedLog(log_file, b"\x01" * 32, "0" * 64, "CASE-ADB", "examiner")


def test_adb_runner_version_check() -> None:
    runner = AdbRunner()
    assert runner.adb_path.is_file()
    assert len(runner.binary_hash) == 64
    assert "Android Debug Bridge" in runner.version_info


def test_adb_runner_blocks_forbidden(dummy_logger: ChainedLog) -> None:
    runner = AdbRunner(serial="EMU1234", logger=dummy_logger)

    with pytest.raises(ForbiddenCommandError):
        runner.run("root")

    # Verificar que el evento ADB_CMD_BLOCKED fue registrado en el log
    assert dummy_logger.current_seq == 1


def test_adb_runner_blocks_unauthorized_intrusive(dummy_logger: ChainedLog) -> None:
    # Sin autorizador, los intrusivos deben fallar
    runner = AdbRunner(serial="EMU1234", logger=dummy_logger, intrusive_authorizer=None)

    with pytest.raises(IntrusiveCommandUnauthorizedError):
        runner.run("shell", "settings", "put", "global", "stay_on_while_plugged_in", "3")


def test_adb_runner_allows_authorized_intrusive(dummy_logger: ChainedLog) -> None:
    # Con autorizador que retorna True
    authorizer = MagicMock(return_value=True)
    runner = AdbRunner(serial="EMU1234", logger=dummy_logger, intrusive_authorizer=authorizer)

    with patch("subprocess.run") as mock_sub:
        mock_sub.return_value.returncode = 0
        mock_sub.return_value.stdout = b""
        mock_sub.return_value.stderr = b""

        cp = runner.run("shell", "settings", "put", "global", "stay_on_while_plugged_in", "3")
        assert cp.returncode == 0
        authorizer.assert_called_once()
        assert dummy_logger.current_seq == 2  # START and END


def test_adb_runner_executes_host_without_serial(dummy_logger: ChainedLog) -> None:
    runner = AdbRunner(serial="EMU1234", logger=dummy_logger)

    with patch("subprocess.run") as mock_sub:
        mock_sub.return_value.returncode = 0
        mock_sub.return_value.stdout = b"Android Debug Bridge version 1.0.41"
        mock_sub.return_value.stderr = b""

        runner.run("version")
        # HOST command no debe incluir '-s EMU1234'
        called_args = mock_sub.call_args[0][0]
        assert "-s" not in called_args
        assert called_args[-1] == "version"


def test_adb_runner_executes_read_with_serial(dummy_logger: ChainedLog) -> None:
    runner = AdbRunner(serial="EMU1234", logger=dummy_logger)

    with patch("subprocess.run") as mock_sub:
        mock_sub.return_value.returncode = 0
        mock_sub.return_value.stdout = b"Pixel 8"
        mock_sub.return_value.stderr = b""

        runner.run("shell", "getprop", "ro.product.model")
        called_args = mock_sub.call_args[0][0]
        assert "-s" in called_args
        assert "EMU1234" in called_args


def test_adb_runner_run_stream(dummy_logger: ChainedLog) -> None:
    runner = AdbRunner(serial="EMU1234", logger=dummy_logger)
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value.stdout = b"mocked stream"
        runner.run_stream("track-devices", "-l")
        mock_popen.assert_called_once()
        assert dummy_logger.current_seq == 1


def test_adb_runner_run_stream_forbidden() -> None:
    runner = AdbRunner()
    with pytest.raises(ForbiddenCommandError):
        runner.run_stream("install", "bad.apk")


def test_adb_runner_custom_path() -> None:
    runner = AdbRunner()
    # Usar la ruta ya descubierta como custom_path
    runner_custom = AdbRunner(adb_path=runner.adb_path)
    assert runner_custom.adb_path == runner.adb_path


def test_adb_runner_missing_path() -> None:
    with pytest.raises(FileNotFoundError):
        AdbRunner(adb_path="/non/existent/adb/binary/xyz")
