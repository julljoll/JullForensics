"""Pruebas unitarias para cálculo de hashes en streaming (MultiHasher)."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from jullforensics.integrity.hashing import MultiHasher, hash_bytes, hash_file, tee_stream


def test_hash_bytes_standard() -> None:
    data = b"JullForensics Digital Forensics Evidence"
    hashes = hash_bytes(data, ["sha256", "sha512"])

    assert "sha256" in hashes
    assert "sha512" in hashes
    assert len(hashes["sha256"]) == 64
    assert len(hashes["sha512"]) == 128


def test_multi_hasher_chunked_matches_single() -> None:
    data = b"A" * 5000 + b"B" * 5000
    mh1 = MultiHasher(["sha256", "sha512"])
    mh1.update(data)

    mh2 = MultiHasher(["sha256", "sha512"])
    mh2.update(b"A" * 5000)
    mh2.update(b"B" * 5000)

    assert mh1.hexdigests() == mh2.hexdigests()
    assert mh2.size == 10000


def test_unsupported_algo_raises() -> None:
    with pytest.raises(ValueError, match="no soportado"):
        MultiHasher(["rot13"])


def test_hash_file(tmp_path: Path) -> None:
    test_file = tmp_path / "sample.bin"
    content = b"Evidencia ISO 27037"
    test_file.write_bytes(content)

    file_hashes = hash_file(test_file, ["sha256"])
    mem_hashes = hash_bytes(content, ["sha256"])

    assert file_hashes["sha256"] == mem_hashes["sha256"]


def test_tee_stream() -> None:
    src_data = b"Streaming data directly from adb source to disk"
    src = io.BytesIO(src_data)
    dst = io.BytesIO()

    hasher = MultiHasher(["sha256"])
    bytes_copied = tee_stream(src, dst, hasher, chunk_size=16)

    assert bytes_copied == len(src_data)
    assert dst.getvalue() == src_data
    assert hasher.hexdigests()["sha256"] == hash_bytes(src_data, ["sha256"])["sha256"]
