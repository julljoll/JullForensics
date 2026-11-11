"""Sanitizador de nombres de archivo y miembros TAR para prevenir Tar-Slip (CWE-22)."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

INVALID_CHARS_PATTERN = re.compile(r"[\x00-\x1f\x7f\\]")


class PathTraversalSecurityError(Exception):
    """Lanzada cuando una ruta entrante del teléfono intenta un escape de directorio."""


def sanitize_relative_path(device_path: str) -> str:
    """Sanitiza una ruta proveniente de un dispositivo móvil para uso seguro en disco y TAR.

    Elimina barras iniciales, descarta componentes vacíos y prohíbe terminantemente '..'.
    """
    if not device_path:
        raise ValueError("La ruta del artefacto no puede estar vacía.")

    if INVALID_CHARS_PATTERN.search(device_path):
        raise PathTraversalSecurityError(
            f"Ruta con caracteres de control o barras invertidas: {device_path!r}"
        )

    # Normalizar usando PurePosixPath
    posix_path = PurePosixPath(device_path)

    # Comprobar componentes
    parts: list[str] = []
    for part in posix_path.parts:
        if part in ("/", "\\", ""):
            continue
        if part == "..":
            raise PathTraversalSecurityError(
                f"Intento de salto de directorio (Tar-Slip / CWE-22) detectado: {device_path!r}"
            )
        parts.append(part)

    if not parts:
        raise ValueError(f"Ruta no produce componentes válidos tras sanitización: {device_path!r}")

    return "/".join(parts)
