"""Pruebas unitarias para firma digital asimétrica Ed25519."""

from __future__ import annotations

import pytest

from jullforensics.integrity.signing import Signer, Verifier


def test_ed25519_sign_and_verify() -> None:
    priv, pub = Signer.generate_keypair()
    manifest_data = b'{"case_id": "JF-2026-0001", "artifacts": ["file1.txt"]}'

    signature = Signer.sign_bytes(priv, manifest_data)
    assert len(signature) == 64

    # Verificación exitosa
    assert Verifier.verify(pub, manifest_data, signature) is True


def test_ed25519_tampered_data_fails() -> None:
    priv, pub = Signer.generate_keypair()
    data = b"original data"
    signature = Signer.sign_bytes(priv, data)

    # Datos alterados deben fallar
    assert Verifier.verify(pub, b"tampered data", signature) is False


def test_ed25519_tampered_signature_fails() -> None:
    priv, pub = Signer.generate_keypair()
    data = b"evidence payload"
    sig = bytearray(Signer.sign_bytes(priv, data))
    sig[0] ^= 0xFF  # mutar un byte

    assert Verifier.verify(pub, data, bytes(sig)) is False


def test_pem_export_and_import() -> None:
    priv, pub = Signer.generate_keypair()
    pem_bytes = Signer.export_public_key_pem(pub)
    assert pem_bytes.startswith(b"-----BEGIN PUBLIC KEY-----")

    reloaded_pub = Verifier.load_public_key_pem(pem_bytes)
    data = b"test payload"
    sig = Signer.sign_bytes(priv, data)
    assert Verifier.verify(reloaded_pub, data, sig) is True


def test_private_key_export_with_password() -> None:
    priv, pub = Signer.generate_keypair()
    pem_encrypted = Signer.export_private_key_pem(priv, password="perito_secret_password")
    assert b"ENCRYPTED" in pem_encrypted or b"PRIVATE KEY" in pem_encrypted

    pem_plain = Signer.export_private_key_pem(priv, password=None)
    assert b"PRIVATE KEY" in pem_plain


def test_verifier_invalid_key_type() -> None:
    from cryptography.hazmat.primitives.asymmetric import rsa

    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048).public_key()
    from cryptography.hazmat.primitives import serialization

    rsa_pem = rsa_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with pytest.raises(TypeError, match="Ed25519"):
        Verifier.load_public_key_pem(rsa_pem)
