"""Pruebas unitarias para el monitor de conexión en tiempo real (track-devices)."""

from __future__ import annotations

import io

from jullforensics.adb.device_monitor import (
    DeviceEntry,
    DeviceState,
    diff_devices,
    parse_devices,
    read_frames,
)


def test_parse_devices_payload() -> None:
    payload = (
        "R58W123ABC   device product:a54x model:SM_A546E device:a54x transport_id:1\n"
        "EMU_OLD      unauthorized transport_id:2\n"
        "OFFLINE_DEV  offline transport_id:3\n"
    )
    devices = parse_devices(payload)

    assert len(devices) == 3
    assert devices["R58W123ABC"].state == DeviceState.DEVICE
    assert devices["R58W123ABC"].model == "SM_A546E"
    assert devices["EMU_OLD"].state == DeviceState.UNAUTHORIZED
    assert devices["OFFLINE_DEV"].state == DeviceState.OFFLINE


def test_read_frames_hex_chunks() -> None:
    frame1_body = "DEV1 device\n"
    frame1_header = f"{len(frame1_body):04x}"  # 4 hex chars

    frame2_body = "DEV1 device\nDEV2 unauthorized\n"
    frame2_header = f"{len(frame2_body):04x}"

    stream = io.BytesIO(
        frame1_header.encode("ascii")
        + frame1_body.encode("utf-8")
        + frame2_header.encode("ascii")
        + frame2_body.encode("utf-8")
    )

    snapshots = list(read_frames(stream))
    assert len(snapshots) == 2
    assert "DEV1" in snapshots[0]
    assert len(snapshots[1]) == 2


def test_diff_devices_events() -> None:
    d1 = DeviceEntry(serial="S1", state=DeviceState.UNAUTHORIZED)
    d2 = DeviceEntry(serial="S2", state=DeviceState.DEVICE)

    # Estado inicial: solo S1 (unauthorized)
    prev = {"S1": d1}

    # Nuevo estado: S1 pasa a device, y se conecta S2
    d1_authed = DeviceEntry(serial="S1", state=DeviceState.DEVICE)
    cur = {"S1": d1_authed, "S2": d2}

    events = diff_devices(prev, cur)
    event_names = [ev[0] for ev in events]

    assert "DEVICE_CONNECTED" in event_names
    assert "DEVICE_STATE_CHANGED" in event_names
