"""Gestión segura y derivación criptográfica de claves de sesión de caso.

Alineado con NIST SP 800-132 y RFC 7914 (scrypt).
"""

from __future__ import annotations

import hashlib
import os


def generate_salt(length: int = 16) -> bytes:
    """Genera una sal criptográficamente segura."""
    if length < 16:
        raise ValueError("La longitud mínima segura para la sal es de 16 bytes.")
    return os.urandom(length)


def derive_case_key(passphrase: str | bytes, salt: bytes, length: int = 32) -> bytes:
    """Deriva una clave de 256 bits mediante scrypt para HMAC o cifrado simétrico.

    Parámetros endurecidos:
      - N = 32768 (2^15)
      - r = 8
      - p = 1
    """
    if not passphrase:
        raise ValueError("La frase de paso del examinador no puede estar vacía.")
    if len(salt) < 16:
        raise ValueError("La sal debe tener al menos 16 bytes.")

    pw_bytes = passphrase.encode("utf-8") if isinstance(passphrase, str) else bytes(passphrase)

    return hashlib.scrypt(
        pw_bytes,
        salt=salt,
        n=32768,
        r=8,
        p=1,
        maxmem=64 * 1024 * 1024,
        dklen=length,
    )


def wipe_memory(buf: bytearray) -> None:
    """Sobrescribe de forma destructiva un búfer de memoria con ceros."""
    for i in range(len(buf)):
        buf[i] = 0
