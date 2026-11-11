"""Cálculo de resúmenes criptográficos (hashes) en streaming y multi-algoritmo.

Alineado con FIPS 180-4, NIST SP 800-131A e ISO/IEC 27037.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path
from typing import IO, BinaryIO

CHUNK_SIZE = 1024 * 1024  # 1 MiB
DEFAULT_ALGOS: tuple[str, ...] = ("sha256", "sha512")
SUPPORTED_ALGOS: set[str] = {"sha256", "sha512", "sha3_256", "sha384", "md5", "sha1"}


class MultiHasher:
    """Calculador simultáneo de múltiples algoritmos de hash en un único recorrido de datos."""

    def __init__(self, algos: Iterable[str] = DEFAULT_ALGOS) -> None:
        self._algos = tuple(algos)
        for algo in self._algos:
            if algo not in SUPPORTED_ALGOS:
                raise ValueError(f"Algoritmo de hash no soportado: {algo}")

        self._hasher_instances = {algo: hashlib.new(algo) for algo in self._algos}
        self.size: int = 0

    def update(self, data: bytes) -> None:
        """Actualiza todos los algoritmos con el bloque de datos provisto."""
        if not data:
            return
        self.size += len(data)
        for h in self._hasher_instances.values():
            h.update(data)

    def hexdigests(self) -> dict[str, str]:
        """Retorna {nombre_algoritmo: valor_hex} con los hashes calculados."""
        return {algo: h.hexdigest() for algo, h in self._hasher_instances.items()}


def hash_bytes(data: bytes, algos: Iterable[str] = DEFAULT_ALGOS) -> dict[str, str]:
    """Calcula los resúmenes criptográficos de una secuencia de bytes en memoria."""
    mh = MultiHasher(algos)
    mh.update(data)
    return mh.hexdigests()


def hash_file(path: Path | str, algos: Iterable[str] = DEFAULT_ALGOS) -> dict[str, str]:
    """Calcula los resúmenes criptográficos de un archivo en disco mediante lectura en streaming."""
    target_path = Path(path)
    if not target_path.is_file():
        raise FileNotFoundError(f"Archivo no encontrado para cálculo de hash: {path}")

    mh = MultiHasher(algos)
    with target_path.open("rb") as fh:
        while chunk := fh.read(CHUNK_SIZE):
            mh.update(chunk)
    return mh.hexdigests()


def tee_stream(
    src: BinaryIO | IO[bytes],
    dst: BinaryIO | IO[bytes],
    hasher: MultiHasher,
    chunk_size: int = CHUNK_SIZE,
) -> int:
    """Copia datos de src a dst mientras actualiza simultáneamente el hasher en una sola pasada.

    Retorna la cantidad total de bytes copiados.
    """
    total_bytes = 0
    while chunk := src.read(chunk_size):
        dst.write(chunk)
        hasher.update(chunk)
        total_bytes += len(chunk)
    dst.flush()
    return total_bytes
