"""Ejecutor blindado de comandos ADB con auditoría continua y validación de seguridad."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from jullforensics.adb.allowlist import (
    CommandClass,
    ForbiddenCommandError,
    IntrusiveCommandUnauthorizedError,
    classify_command,
)
from jullforensics.integrity.hashing import hash_file

if TYPE_CHECKING:
    from jullforensics.integrity.chained_log import ChainedLog


def find_adb_binary(custom_path: Path | str | None = None) -> Path:
    """Localiza el binario de ADB en el sistema o rutas conocidas."""
    if custom_path:
        p = Path(custom_path)
        if p.is_file() and os.access(p, os.X_OK):
            return p
        raise FileNotFoundError(
            f"Ruta personalizada de adb inválida o no ejecutable: {custom_path}"
        )

    # 1. Buscar en PATH del sistema
    which_path = shutil.which("adb")
    if which_path:
        return Path(which_path)

    # 2. Rutas comunes en Linux / Kali
    common_paths = [
        Path.home() / ".local" / "bin" / "adb",
        Path.home() / ".local" / "platform-tools" / "adb",
        Path("/usr/bin/adb"),
        Path("/usr/lib/android-sdk/platform-tools/adb"),
    ]
    for cp in common_paths:
        if cp.is_file() and os.access(cp, os.X_OK):
            return cp

    raise FileNotFoundError(
        "No se encontró el binario 'adb'. Asegúrese de instalar android-tools-adb o platform-tools."
    )


class AdbRunner:
    """Adaptador de ejecución controlada para ADB que aplica lista blanca y auditoría."""

    def __init__(
        self,
        serial: str | None = None,
        adb_path: Path | str | None = None,
        logger: ChainedLog | None = None,
        intrusive_authorizer: Callable[[tuple[str, ...]], bool] | None = None,
    ) -> None:
        self.adb_path = find_adb_binary(adb_path)
        self.serial = serial
        self.logger = logger
        self.intrusive_authorizer = intrusive_authorizer

        # Registrar hash y versión del binario de adb para reproducibilidad forense
        self.binary_hash = hash_file(self.adb_path, ["sha256"])["sha256"]
        self.version_info = self._get_version()

    def _get_version(self) -> str:
        """Obtiene la cadena de versión del ejecutable adb."""
        try:
            res = subprocess.run(  # noqa: S603
                [str(self.adb_path), "version"],
                shell=False,
                capture_output=True,
                timeout=5,
                check=False,
            )
            return res.stdout.decode("utf-8", "replace").strip()
        except Exception:
            return "Versión desconocida"

    def run(
        self,
        *args: str,
        timeout: int = 120,
        check: bool = False,
    ) -> subprocess.CompletedProcess[bytes]:
        """Ejecuta un comando ADB de forma síncrona tras validar la lista blanca y auditar."""
        cmd_class = classify_command(args)

        # 1. Bloquear comandos prohibidos
        if cmd_class == CommandClass.FORBIDDEN:
            if self.logger:
                self.logger.append(
                    "ADB_CMD_BLOCKED",
                    "adb",
                    {"args": list(args), "reason": "Comando en lista negra FORBIDDEN"},
                )
            raise ForbiddenCommandError(
                f"Comando bloqueado por política de integridad forense: {' '.join(args)}"
            )

        # 2. Verificar autorización para comandos intrusivos
        if cmd_class == CommandClass.INTRUSIVE:
            authorized = False
            if self.intrusive_authorizer:
                authorized = self.intrusive_authorizer(args)
            if not authorized:
                if self.logger:
                    self.logger.append(
                        "ADB_CMD_BLOCKED",
                        "adb",
                        {
                            "args": list(args),
                            "reason": "Comando INTRUSIVE no autorizado por el perito",
                        },
                    )
                raise IntrusiveCommandUnauthorizedError(
                    f"Comando intrusivo no autorizado: {' '.join(args)}"
                )

        # Construir argv final con target (-s serial) si aplica
        argv: list[str] = [str(self.adb_path)]
        if self.serial and cmd_class != CommandClass.HOST:
            argv.extend(["-s", self.serial])
        argv.extend(args)

        # Registrar inicio del comando en el log encadenado
        if self.logger:
            self.logger.append(
                "ADB_CMD_START",
                "adb",
                {
                    "argv": argv,
                    "class": cmd_class.value,
                    "serial": self.serial,
                },
            )

        t0 = time.monotonic()
        cp = subprocess.run(  # noqa: S603
            argv,
            shell=False,
            capture_output=True,
            timeout=timeout,
            check=check,
        )
        duration_s = round(time.monotonic() - t0, 3)

        # Registrar fin y hashes de las salidas para auditabilidad forense
        if self.logger:
            self.logger.append(
                "ADB_CMD_END",
                "adb",
                {
                    "argv": argv,
                    "returncode": cp.returncode,
                    "duration_s": duration_s,
                    "stdout_sha256": hashlib.sha256(cp.stdout).hexdigest(),
                    "stderr_sha256": hashlib.sha256(cp.stderr).hexdigest(),
                },
            )

        return cp

    def run_stream(self, *args: str) -> subprocess.Popen[bytes]:
        """Inicia un comando ADB en streaming (Popen) para tuberías continuas."""
        cmd_class = classify_command(args)
        if cmd_class == CommandClass.FORBIDDEN:
            raise ForbiddenCommandError(f"Comando streaming bloqueado: {' '.join(args)}")

        argv: list[str] = [str(self.adb_path)]
        if self.serial and cmd_class != CommandClass.HOST:
            argv.extend(["-s", self.serial])
        argv.extend(args)

        if self.logger:
            self.logger.append(
                "ADB_CMD_START",
                "adb",
                {"argv": argv, "class": cmd_class.value, "streaming": True},
            )

        return subprocess.Popen(  # noqa: S603
            argv,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
