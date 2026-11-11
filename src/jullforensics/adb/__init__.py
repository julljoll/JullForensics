"""Módulo de comunicación segura y controlada con Android Debug Bridge (ADB)."""

from .allowlist import (
    CommandClass,
    ForbiddenCommandError,
    IntrusiveCommandUnauthorizedError,
    classify_command,
    validate_argument_safety,
)
from .runner import AdbRunner

__all__ = [
    "CommandClass",
    "ForbiddenCommandError",
    "IntrusiveCommandUnauthorizedError",
    "classify_command",
    "validate_argument_safety",
    "AdbRunner",
]
