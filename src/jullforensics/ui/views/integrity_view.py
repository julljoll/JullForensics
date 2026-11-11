"""Vista 05: Panel de control criptográfico e integridad pericial (ISO/IEC 27037 / 27042)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from jullforensics.domain.artifact import Artifact
    from jullforensics.storage.evidence_store import EvidenceStore


class IntegrityView(QWidget):
    """Muestra la tabla de resúmenes criptográficos SHA-256/512 y el estado del contenedor."""

    def __init__(self) -> None:
        super().__init__()
        self._all_artifacts: list[Artifact] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Panel superior de estado general
        grp_summary = QGroupBox("ESTADO CRIPTOGRÁFICO DE LA EVIDENCIA (ISO/IEC 27037)")
        h_sum = QHBoxLayout(grp_summary)

        self._lbl_counts = QLabel("ARTEFACTOS: 0 | TAMAÑO: 0 B | LOG HEAD: N/A")
        self._lbl_counts.setStyleSheet("font-weight: bold;")

        self._lbl_tar_status = QLabel("● TAR: PENDIENTE DE EXTRACCIÓN")
        self._lbl_tar_status.setStyleSheet("font-weight: bold; color: #666666;")

        h_sum.addWidget(self._lbl_counts, stretch=1)
        h_sum.addWidget(self._lbl_tar_status, stretch=0)
        layout.addWidget(grp_summary)

        # Barra de filtrado
        h_filter = QHBoxLayout()
        h_filter.addWidget(QLabel("FILTRAR ARTEFACTOS:"), stretch=0)
        self._in_filter = QLineEdit()
        self._in_filter.setPlaceholderText("Buscar por ruta, nombre o extensión...")
        self._in_filter.textChanged.connect(self._apply_filter)
        h_filter.addWidget(self._in_filter, stretch=1)

        self._btn_refresh = QPushButton("RE-VERIFICAR SUMAS")
        h_filter.addWidget(self._btn_refresh, stretch=0)
        layout.addLayout(h_filter)

        # Tabla de artefactos
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            [
                "RUTA RELATIVA",
                "TAMAÑO",
                "MÓDULO",
                "ESTADO",
                "SHA-256",
                "SHA-512",
            ]
        )
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

    def update_store(
        self,
        store: EvidenceStore | None,
        tar_path: str | None = None,
        tar_sha256: str | None = None,
    ) -> None:
        if store is None:
            self._table.setRowCount(0)
            self._all_artifacts = []
            return

        self._all_artifacts = list(store.artifacts)
        total_bytes = sum(a.size_bytes for a in self._all_artifacts)
        head_short = store.logger.head_hash[:16] + "..."

        self._lbl_counts.setText(
            f"ARTEFACTOS: {len(self._all_artifacts)} | "
            f"TAMAÑO: {total_bytes} B | "
            f"LOG HEAD: {head_short}"
        )

        if tar_path and tar_sha256:
            self._lbl_tar_status.setText(f"✓ JF-TAR SELLADO: {tar_sha256[:16]}...")
            self._lbl_tar_status.setStyleSheet("font-weight: bold; color: #00873E;")
        else:
            self._lbl_tar_status.setText("● TAR: EN PROCESO / NO SELLADO")
            self._lbl_tar_status.setStyleSheet("font-weight: bold; color: #E65100;")

        self._apply_filter()

    def _apply_filter(self) -> None:
        query = self._in_filter.text().strip().lower()
        filtered = [
            a
            for a in self._all_artifacts
            if query in a.relative_path.lower() or query in a.module.lower()
        ]

        self._table.setRowCount(len(filtered))
        for row, art in enumerate(filtered):
            it_path = QTableWidgetItem(art.relative_path)
            it_size = QTableWidgetItem(f"{art.size_bytes} B")
            it_mod = QTableWidgetItem(art.module)
            it_status = QTableWidgetItem(str(art.status))
            it_status.setForeground(Qt.GlobalColor.darkGreen)
            it_sha256 = QTableWidgetItem(art.sha256)
            it_sha512 = QTableWidgetItem(art.sha512[:32] + "...")

            self._table.setItem(row, 0, it_path)
            self._table.setItem(row, 1, it_size)
            self._table.setItem(row, 2, it_mod)
            self._table.setItem(row, 3, it_status)
            self._table.setItem(row, 4, it_sha256)
            self._table.setItem(row, 5, it_sha512)
