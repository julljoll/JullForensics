"""Hoja de estilo Qt (QSS) brutalista para JullForensics."""

from __future__ import annotations

from jullforensics.ui.theme.tokens import (
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_DANGER,
    COLOR_DARK_SURFACE,
    COLOR_INK,
    COLOR_MUTED,
    COLOR_SUCCESS,
    COLOR_SURFACE,
    FONT_FAMILY,
)


def get_application_stylesheet() -> str:
    """Retorna la hoja de estilos global Qt 6 compilada con estética brutalista."""
    return f"""
    * {{
        font-family: {FONT_FAMILY};
        font-size: 13px;
        color: {COLOR_INK};
    }}

    QMainWindow, QWidget {{
        background-color: {COLOR_BG};
    }}

    /* Paneles y tarjetas */
    QFrame[frameShape="1"] {{
        background-color: {COLOR_SURFACE};
        border: 3px solid {COLOR_BORDER};
    }}

    /* Botones brutalistas */
    QPushButton {{
        background-color: {COLOR_SURFACE};
        border: 3px solid {COLOR_BORDER};
        padding: 8px 16px;
        font-weight: bold;
        text-transform: uppercase;
    }}

    QPushButton:hover {{
        background-color: {COLOR_ACCENT};
    }}

    QPushButton:pressed {{
        background-color: {COLOR_INK};
        color: {COLOR_SURFACE};
    }}

    QPushButton:disabled {{
        background-color: {COLOR_MUTED};
        border-color: #888888;
        color: #666666;
    }}

    QPushButton#btn_primary {{
        background-color: {COLOR_ACCENT};
    }}

    QPushButton#btn_primary:hover {{
        background-color: #FFD000;
    }}

    QPushButton#btn_danger {{
        background-color: {COLOR_DANGER};
        color: #FFFFFF;
    }}

    QPushButton#btn_success {{
        background-color: {COLOR_SUCCESS};
        color: #FFFFFF;
    }}

    /* Campos de entrada */
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {{
        background-color: {COLOR_SURFACE};
        border: 2px solid {COLOR_BORDER};
        padding: 6px 10px;
        font-family: {FONT_FAMILY};
        selection-background-color: {COLOR_ACCENT};
        selection-color: {COLOR_INK};
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
        border: 3px solid {COLOR_BORDER};
        background-color: #FFFFF8;
    }}

    /* Pestañas de navegación */
    QTabWidget::pane {{
        border: 3px solid {COLOR_BORDER};
        background-color: {COLOR_SURFACE};
        top: -3px;
    }}

    QTabBar::tab {{
        background-color: {COLOR_MUTED};
        border: 3px solid {COLOR_BORDER};
        border-bottom: none;
        padding: 10px 18px;
        font-weight: bold;
        margin-right: 4px;
        text-transform: uppercase;
    }}

    QTabBar::tab:selected {{
        background-color: {COLOR_SURFACE};
        border-bottom: 3px solid {COLOR_SURFACE};
        color: {COLOR_INK};
    }}

    QTabBar::tab:hover:!selected {{
        background-color: {COLOR_ACCENT};
    }}

    /* Tablas de evidencias */
    QTableWidget, QTableView {{
        background-color: {COLOR_SURFACE};
        border: 2px solid {COLOR_BORDER};
        gridline-color: {COLOR_BORDER};
        selection-background-color: {COLOR_ACCENT};
        selection-color: {COLOR_INK};
    }}

    QHeaderView::section {{
        background-color: #E2E2DE;
        border: 1px solid {COLOR_BORDER};
        padding: 6px;
        font-weight: bold;
        text-transform: uppercase;
    }}

    /* Barra de progreso sólida */
    QProgressBar {{
        border: 3px solid {COLOR_BORDER};
        background-color: {COLOR_SURFACE};
        text-align: center;
        font-weight: bold;
        height: 24px;
    }}

    QProgressBar::chunk {{
        background-color: {COLOR_ACCENT};
    }}

    /* Barra de estado / consola */
    QStatusBar {{
        background-color: {COLOR_DARK_SURFACE};
        color: #FFFFFF;
        border-top: 3px solid {COLOR_BORDER};
        font-family: {FONT_FAMILY};
    }}

    QStatusBar QLabel {{
        color: #FFFFFF;
    }}

    /* Barras de desplazamiento */
    QScrollBar:vertical {{
        border: 2px solid {COLOR_BORDER};
        background: {COLOR_MUTED};
        width: 14px;
        margin: 0px;
    }}

    QScrollBar::handle:vertical {{
        background: {COLOR_INK};
        min-height: 20px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {COLOR_ACCENT};
    }}

    QScrollBar:horizontal {{
        border: 2px solid {COLOR_BORDER};
        background: {COLOR_MUTED};
        height: 14px;
        margin: 0px;
    }}

    QScrollBar::handle:horizontal {{
        background: {COLOR_INK};
        min-width: 20px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: {COLOR_ACCENT};
    }}
    """
