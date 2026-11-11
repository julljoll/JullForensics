"""Vista 06: Generación y exportación de dictámenes periciales (ISO 27042 / 27050)."""

from __future__ import annotations

import subprocess  # nosec B404
from typing import TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from jullforensics.storage.evidence_store import EvidenceStore


class ReportView(QWidget):
    """Interfaz para inspeccionar y exportar dictámenes periciales (PDF, HTML, JSON)."""

    generate_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._store: EvidenceStore | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Barra de estado y acciones
        grp_ctrl = QGroupBox("DICTÁMENES PERICIALES GENERADOS (ISO/IEC 27042 / 27050)")
        v_ctrl = QVBoxLayout(grp_ctrl)

        self._lbl_info = QLabel(
            "Dictámenes aún no generados. Ejecute una adquisición o pulse Generar."
        )
        self._lbl_info.setStyleSheet("font-weight: bold;")
        v_ctrl.addWidget(self._lbl_info)

        h_btns = QHBoxLayout()
        self._btn_gen = QPushButton("GENERAR DICTÁMENES (PDF / HTML / JSON)")
        self._btn_gen.setObjectName("btn_primary")
        self._btn_gen.clicked.connect(self.generate_requested.emit)

        self._btn_open_html = QPushButton("ABRIR REPORTE HTML")
        self._btn_open_html.setEnabled(False)
        self._btn_open_html.clicked.connect(self._open_html)

        self._btn_open_pdf = QPushButton("ABRIR DICTAMEN PDF")
        self._btn_open_pdf.setEnabled(False)
        self._btn_open_pdf.clicked.connect(self._open_pdf)

        h_btns.addWidget(self._btn_gen)
        h_btns.addWidget(self._btn_open_html)
        h_btns.addWidget(self._btn_open_pdf)
        v_ctrl.addLayout(h_btns)
        layout.addWidget(grp_ctrl)

        # Visor integrado de HTML
        grp_preview = QGroupBox("PREVISUALIZACIÓN DEL DICTAMEN PERICIAL")
        v_prev = QVBoxLayout(grp_preview)

        self._browser = QTextBrowser()
        self._browser.setStyleSheet("background-color: #FFFFFF; border: 2px solid #0A0A0A;")
        v_prev.addWidget(self._browser)
        layout.addWidget(grp_preview)

    def update_reports(self, store: EvidenceStore | None) -> None:
        self._store = store
        if store is None:
            self._lbl_info.setText("Sin caso activo.")
            self._btn_open_html.setEnabled(False)
            self._btn_open_pdf.setEnabled(False)
            self._browser.clear()
            return

        html_file = store.base_dir / "reports" / "report.html"
        pdf_file = store.base_dir / "reports" / "report.pdf"
        json_file = store.base_dir / "reports" / "report.json"

        has_html = html_file.is_file()
        has_pdf = pdf_file.is_file()

        self._btn_open_html.setEnabled(has_html)
        self._btn_open_pdf.setEnabled(has_pdf)

        if has_html and has_pdf:
            self._lbl_info.setText(
                f"✓ DICTÁMENES DISPONIBLES EN: {store.base_dir / 'reports'}\n"
                f"PDF: {pdf_file.name} | HTML: {html_file.name} | JSON: {json_file.name}"
            )
            self._lbl_info.setStyleSheet("font-weight: bold; color: #00873E;")
            self._browser.setHtml(html_file.read_text(encoding="utf-8"))
        else:
            self._lbl_info.setText("● Dictámenes pendientes de generación.")
            self._lbl_info.setStyleSheet("font-weight: bold; color: #E65100;")

    def _open_html(self) -> None:
        if self._store:
            html_file = self._store.base_dir / "reports" / "report.html"
            if html_file.is_file():
                subprocess.Popen(["xdg-open", str(html_file)])  # noqa: S603, S607 # nosec B603 B607

    def _open_pdf(self) -> None:
        if self._store:
            pdf_file = self._store.base_dir / "reports" / "report.pdf"
            if pdf_file.is_file():
                subprocess.Popen(["xdg-open", str(pdf_file)])  # noqa: S603, S607 # nosec B603 B607
