"""Punto de entrada principal para la aplicación JullForensics."""

from __future__ import annotations

import argparse
import os
import sys

from PySide6.QtWidgets import QApplication

from jullforensics import __version__
from jullforensics.ui.main_window import MainWindow
from jullforensics.ui.theme.qss import get_application_stylesheet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="jullforensics",
        description="JullForensics - Extracción lógica forense Android para Kali Linux",
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "-d",
        "--base-dir",
        type=str,
        default=None,
        help="Directorio base para almacenamiento de casos",
    )
    parser.add_argument(
        "--adb-path", type=str, default=None, help="Ruta personalizada al ejecutable adb"
    )
    parser.add_argument(
        "--offscreen", action="store_true", help="Forzar modo offscreen (sin servidor X11/Wayland)"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Detectar si no hay display gráfico disponible en Linux y aplicar fallback offscreen
    if args.offscreen or (not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY")):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication(sys.argv)
    app.setApplicationName("JullForensics")
    app.setApplicationVersion(__version__)
    app.setStyleSheet(get_application_stylesheet())

    window = MainWindow(base_dir=args.base_dir, adb_path=args.adb_path)
    window.show()

    # Si se ejecutó forzadamente offscreen para pruebas, cerrar inmediatamente
    if args.offscreen:
        window.close()
        return 0

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
