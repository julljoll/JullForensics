"""Firma digital asimétrica Ed25519 (RFC 8032) para sellado pericial de manifiestos."""

from __future__ import annotations

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


class Signer:
    """Generador de claves y firmante digital Ed25519."""

    @staticmethod
    def generate_keypair() -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
        """Genera un nuevo par de claves asimétricas Ed25519."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        return private_key, private_key.public_key()

    @staticmethod
    def sign_bytes(private_key: ed25519.Ed25519PrivateKey, data: bytes) -> bytes:
        """Firma un bloque de bytes y retorna la firma en crudo (64 bytes)."""
        return private_key.sign(data)

    @staticmethod
    def export_public_key_pem(public_key: ed25519.Ed25519PublicKey) -> bytes:
        """Exporta la clave pública en formato PEM estándar (SubjectPublicKeyInfo)."""
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    @staticmethod
    def export_private_key_pem(
        private_key: ed25519.Ed25519PrivateKey,
        password: str | None = None,
    ) -> bytes:
        """Exporta la clave privada en formato PEM (opcionalmente cifrada con PKCS#8)."""
        encryption: serialization.KeySerializationEncryption
        if password:
            encryption = serialization.BestAvailableEncryption(password.encode("utf-8"))
        else:
            encryption = serialization.NoEncryption()

        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption,
        )


class Verifier:
    """Verificador de firmas digitales Ed25519."""

    @staticmethod
    def load_public_key_pem(pem_bytes: bytes) -> ed25519.Ed25519PublicKey:
        """Carga una clave pública Ed25519 desde su representación PEM."""
        key = serialization.load_pem_public_key(pem_bytes)
        if not isinstance(key, ed25519.Ed25519PublicKey):
            raise TypeError("La clave PEM provista no corresponde a un algoritmo Ed25519.")
        return key

    @staticmethod
    def verify(public_key: ed25519.Ed25519PublicKey, data: bytes, signature: bytes) -> bool:
        """Verifica si la firma provista es válida para los datos dados.

        Retorna True si es válida, False en caso de discrepancia o manipulación.
        """
        try:
            public_key.verify(signature, data)
            return True
        except InvalidSignature:
            return False
