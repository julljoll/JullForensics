"""Lista blanca estricta (Allowlist) y clasificación de seguridad de comandos ADB.

Previene CWE-78 (OS Command Injection) y asegura el principio de mínima intervención
conforme a ISO/IEC 27037.
"""

from __future__ import annotations

import re
from enum import StrEnum


class CommandClass(StrEnum):
    HOST = (
        "HOST"  # Comandos de servidor / host (no interactúan con el sistema de archivos del móvil)
    )
    READ = "READ"  # Lectura pura sin alteración de estado del dispositivo
    READ_HEAVY = "READ_HEAVY"  # Lectura intensiva con potencial impacto de rendimiento o espera
    INTRUSIVE = "INTRUSIVE"  # Modifica transitoriamente el estado (requiere autorización explícita)
    FORBIDDEN = "FORBIDDEN"  # Bloqueado tajantemente (riesgo de alteración permanente o exploit)


class AdbSecurityError(Exception):
    """Excepción base para violaciones de seguridad en el adaptador ADB."""


class ForbiddenCommandError(AdbSecurityError):
    """Lanzada cuando un comando pertenece a la clase FORBIDDEN."""


class IntrusiveCommandUnauthorizedError(AdbSecurityError):
    """Lanzada cuando se intenta ejecutar un comando INTRUSIVE sin autorización del perito."""


class CommandArgumentInjectionError(AdbSecurityError):
    """Lanzada cuando un argumento contiene metacaracteres peligrosos."""


DANGEROUS_METACHARS_PATTERN = re.compile(r"[;&|`$<>\n\r\x00]")


def validate_argument_safety(arg: str) -> None:
    """Verifica que un argumento no contenga metacaracteres de inyección de comandos o control."""
    if DANGEROUS_METACHARS_PATTERN.search(arg):
        raise CommandArgumentInjectionError(
            f"Argumento contiene caracteres peligrosos prohibidos: {arg!r}"
        )


def classify_command(args: list[str] | tuple[str, ...]) -> CommandClass:
    """Clasifica un vector de argumentos ADB en su categoría de seguridad correspondiente."""
    if not args:
        return CommandClass.FORBIDDEN

    # Validar seguridad básica de cada token
    for a in args:
        validate_argument_safety(a)

    first = args[0]

    # 1. Comandos de HOST
    if first in ("version", "start-server", "kill-server", "devices", "track-devices"):
        return CommandClass.HOST

    # 2. Comandos FORBIDDEN inmediatos
    forbidden_verbs = {
        "install",
        "uninstall",
        "rm",
        "reboot",
        "root",
        "remount",
        "flash",
        "sideload",
        "sync",
        "tcpip",
        "connect",
        "disconnect",
        "forward",
        "reverse",
        "push",
    }
    if first in forbidden_verbs:
        return CommandClass.FORBIDDEN

    # 3. Comandos READ_HEAVY
    if first in ("bugreportz", "bugreport"):
        return CommandClass.READ_HEAVY
    if first == "backup":
        return CommandClass.READ_HEAVY

    # 4. Invocaciones exec-out (streaming directo a stdout en host)
    if first == "exec-out":
        if len(args) < 2:
            return CommandClass.FORBIDDEN
        sub = args[1]
        if sub == "screencap" and args[2:] in (["-p"], ("-p",)):
            return CommandClass.READ
        if sub == "cat":
            return CommandClass.READ
        if sub == "tar" and "-cf" in args and "-" in args:
            # Solo permitir empaquetado a stdout (tar -cf -)
            if "-x" in args or "--extract" in args:
                return CommandClass.FORBIDDEN
            return CommandClass.READ
        if sub == "find":
            return CommandClass.READ
        return CommandClass.FORBIDDEN

    # 5. Descarga de archivos (pull)
    if first == "pull":
        # pull siempre es lectura hacia el host
        return CommandClass.READ

    # 6. logcat
    if first == "logcat":
        # Solo lectura si incluye volcado (-d)
        if "-d" in args or "-g" in args:
            return CommandClass.READ
        return CommandClass.READ_HEAVY

    # 7. Subcomandos bajo "shell"
    if first == "shell":
        if len(args) < 2:
            return CommandClass.FORBIDDEN
        shell_verb = args[1]

        # Comandos prohibidos dentro del shell
        if shell_verb in (
            "rm",
            "mv",
            "cp",
            "mkdir",
            "chmod",
            "chown",
            "touch",
            "dd",
            "su",
            "sh",
            "mkfs",
        ):
            return CommandClass.FORBIDDEN

        # Lecturas puras
        if shell_verb in ("getprop", "ls", "stat", "find", "df", "date", "uptime"):
            return CommandClass.READ

        # Gestores de paquetes (pm)
        if shell_verb == "pm":
            if len(args) >= 3 and args[2] in ("list", "path", "dump"):
                return CommandClass.READ
            return CommandClass.FORBIDDEN

        # Dumpsys
        if shell_verb == "dumpsys":
            return CommandClass.READ

        # Proveedores de contenido (content query)
        if shell_verb == "content":
            if len(args) >= 3 and args[2] == "query":
                return CommandClass.READ
            return CommandClass.FORBIDDEN

        # Window Manager (wm)
        if shell_verb == "wm":
            if len(args) == 3 and args[2] in ("size", "density"):
                # Solo lectura de tamaño/densidad sin modificar
                return CommandClass.READ
            return CommandClass.FORBIDDEN

        # Settings
        if shell_verb == "settings":
            if len(args) >= 3:
                sub_action = args[2]
                if sub_action in ("get", "list"):
                    return CommandClass.READ
                if sub_action == "put":
                    # Modificaciones transitorias clasificadas como INTRUSIVE
                    # Ej: settings put global stay_on_while_plugged_in
                    return CommandClass.INTRUSIVE
            return CommandClass.FORBIDDEN

        # Simulación de gestos (input swipe para scroll de capturas)
        if shell_verb == "input":
            if len(args) >= 3 and args[2] in ("swipe", "keyevent", "tap"):
                return CommandClass.INTRUSIVE
            return CommandClass.FORBIDDEN

        # Screencap escribiendo en el teléfono (prohibido; usar exec-out screencap -p)
        if shell_verb in ("screencap", "screenrecord"):
            return CommandClass.FORBIDDEN

    return CommandClass.FORBIDDEN
