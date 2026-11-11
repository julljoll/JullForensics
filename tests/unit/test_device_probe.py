"""Pruebas unitarias para DeviceProbe y parseo de getprop."""

from __future__ import annotations

from unittest.mock import MagicMock

from jullforensics.adb.device_probe import DeviceProbe, parse_getprop_output
from jullforensics.adb.runner import AdbRunner


def test_parse_getprop_output() -> None:
    sample = (
        "[ro.product.model]: [SM-A546E]\n"
        "[ro.product.manufacturer]: [samsung]\n"
        "[ro.build.version.release]: [14]\n"
        "[ro.build.version.sdk]: [34]\n"
        "[ro.serialno]: [R58W123ABC]\n"
    )
    props = parse_getprop_output(sample)
    assert props["ro.product.model"] == "SM-A546E"
    assert props["ro.build.version.release"] == "14"
    assert props["ro.build.version.sdk"] == "34"


def test_device_probe_identify() -> None:
    runner = AdbRunner(serial="R58W123ABC")
    probe = DeviceProbe(runner)

    def mock_run(*args: object, **kwargs: object) -> MagicMock:
        if "getprop" in args:
            output = (
                b"[ro.product.model]: [Pixel 8]\n"
                b"[ro.product.manufacturer]: [Google]\n"
                b"[ro.build.version.release]: [14]\n"
                b"[ro.build.version.sdk]: [34]\n"
                b"[ro.build.fingerprint]: [google/shiba/shiba:14/...]\n"
            )
            return MagicMock(returncode=0, stdout=output)
        elif "date" in args:
            return MagicMock(returncode=0, stdout=b"1700000000\n")
        elif "battery" in args:
            return MagicMock(returncode=0, stdout=b"  level: 88\n")
        return MagicMock(returncode=0, stdout=b"")

    runner.run = MagicMock(side_effect=mock_run)  # type: ignore[method-assign]
    info = probe.identify_device()

    assert info.serial == "R58W123ABC"
    assert info.model == "Pixel 8"
    assert info.manufacturer == "Google"
    assert info.sdk_version == 34
    assert info.battery_level_percent == 88
