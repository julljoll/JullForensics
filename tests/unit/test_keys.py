"""Pruebas unitarias para derivación y gestión de claves seguras."""

from __future__ import annotations

import pytest

from jullforensics.integrity.keys import derive_case_key, generate_salt, wipe_memory


def test_salt_generation() -> None:
    s1 = generate_salt(16)
    s2 = generate_salt(16)
    assert len(s1) == 16
    assert s1 != s2


def test_salt_too_short_raises() -> None:
    with pytest.raises(ValueError, match="16 bytes"):
        generate_salt(8)


def test_scrypt_derivation_deterministic() -> None:
    salt = generate_salt(16)
    k1 = derive_case_key("passphrase_pericial_123", salt)
    k2 = derive_case_key("passphrase_pericial_123", salt)
    assert k1 == k2
    assert len(k1) == 32


def test_different_passphrase_different_key() -> None:
    salt = generate_salt(16)
    k1 = derive_case_key("clave_uno", salt)
    k2 = derive_case_key("clave_dos", salt)
    assert k1 != k2


def test_empty_passphrase_raises() -> None:
    salt = generate_salt(16)
    with pytest.raises(ValueError, match="no puede estar vacía"):
        derive_case_key("", salt)


def test_short_salt_in_derive_raises() -> None:
    with pytest.raises(ValueError, match="al menos 16 bytes"):
        derive_case_key("valid_pass", b"short_salt")


def test_wipe_memory() -> None:
    buf = bytearray(b"secreto_en_memoria_12345")
    assert any(b != 0 for b in buf)
    wipe_memory(buf)
    assert all(b == 0 for b in buf)
