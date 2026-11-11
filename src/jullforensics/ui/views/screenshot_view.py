"""Vista 03: Galería e interfaz de capturas de pantalla forenses en memoria (F12)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ScreenshotView(QWidget):
    """Interfaz de captura forense directa en RAM con cálculo anticipado de SHA-256."""

    capture_requested = Signal(str)  # Emite la nota pericial

    def __init__(self) -> None:
        super().__init__()
        self._screenshots: list[dict[str, Any]] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # Barra superior de control y notas
        ctrl_box = QGroupBox("CONTROL DE CAPTURA FORENSE DE PANTALLA (ISO/IEC 27037)")
        h_ctrl = QHBoxLayout(ctrl_box)

        self._in_note = QLineEdit()
        self._in_note.setPlaceholderText("Nota pericial o contexto visual de la captura...")

        self._btn_capture = QPushButton("CAPTURAR PANTALLA EN VIVO [F12]")
        self._btn_capture.setObjectName("btn_primary")
        self._btn_capture.clicked.connect(self._on_capture_click)

        h_ctrl.addWidget(QLabel("NOTA:"), stretch=0)
        h_ctrl.addWidget(self._in_note, stretch=1)
        h_ctrl.addWidget(self._btn_capture, stretch=0)
        main_layout.addWidget(ctrl_box)

        # Panel dividido: Izquierda tabla de capturas, Derecha previsualización
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Tabla de capturas
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            [
                "Nº",
                "HORA (UTC)",
                "ACTIVIDAD EN PANTALLA",
                "ESTADO DE SEGURIDAD",
                "HASH SHA-256",
            ]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self._table)
        splitter.addWidget(left_widget)

        # Panel de previsualización
        right_widget = QGroupBox("PREVISUALIZACIÓN DE IMAGEN")
        right_layout = QVBoxLayout(right_widget)

        self._lbl_preview = QLabel("Seleccione una captura de la lista")
        self._lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_preview.setStyleSheet(
            "background-color: #1A1A1A; color: #FFF; border: 2px solid #0A0A0A;"
        )
        self._lbl_preview.setMinimumSize(240, 360)
        right_layout.addWidget(self._lbl_preview)

        self._lbl_meta = QLabel()
        self._lbl_meta.setWordWrap(True)
        self._lbl_meta.setStyleSheet("font-size: 11px; padding: 4px;")
        right_layout.addWidget(self._lbl_meta)

        splitter.addWidget(right_widget)
        splitter.setSizes([600, 350])
        main_layout.addWidget(splitter)

    def _on_capture_click(self) -> None:
        note = self._in_note.text().strip()
        self.capture_requested.emit(note)
        self._in_note.clear()

    def add_screenshot(self, meta: dict[str, Any], base_path: Path | None = None) -> None:
        self._screenshots.append(meta)
        row = self._table.rowCount()
        self._table.insertRow(row)

        seq_str = f"#{len(self._screenshots):04d}"
        ts_str = str(meta.get("ts_before_utc", ""))[:19]
        act_str = str(meta.get("foreground_activity", "Desconocida"))
        warn = bool(meta.get("security_warning", False))
        warn_str = "⚠ FLAG_SECURE / NEGRA" if warn else "✓ VÁLIDA"
        sha_str = str(meta.get("sha256", ""))

        it_seq = QTableWidgetItem(seq_str)
        it_ts = QTableWidgetItem(ts_str)
        it_act = QTableWidgetItem(act_str)
        it_warn = QTableWidgetItem(warn_str)
        it_sha = QTableWidgetItem(sha_str)

        if warn:
            it_warn.setForeground(Qt.GlobalColor.red)
        else:
            it_warn.setForeground(Qt.GlobalColor.darkGreen)

        self._table.setItem(row, 0, it_seq)
        self._table.setItem(row, 1, it_ts)
        self._table.setItem(row, 2, it_act)
        self._table.setItem(row, 3, it_warn)
        self._table.setItem(row, 4, it_sha)

        self._table.selectRow(row)

    def _on_selection_changed(self) -> None:
        selected_rows = self._table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if row < len(self._screenshots):
            meta = self._screenshots[row]
            png_file = meta.get("png_file")
            if png_file and Path(png_file).is_file():
                pix = QPixmap(str(png_file))
                self._lbl_preview.setPixmap(
                    pix.scaled(
                        self._lbl_preview.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                self._lbl_preview.setText(
                    f"Archivo: {png_file}\n(Resolución: {meta.get('width')}x{meta.get('height')})"
                )

            info_text = (
                f"DIMENSIONES: {meta.get('width')}x{meta.get('height')} px | "
                f"TAMAÑO: {meta.get('size_bytes')} B\n"
                f"SHA-256: {meta.get('sha256')}\n"
                f"NOTA: {meta.get('note', '')}"
            )
            self._lbl_meta.setText(info_text)
