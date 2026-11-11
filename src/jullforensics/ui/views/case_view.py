"""Vista 01: Identificación del Caso, Perito y Fundamento Jurídico (ISO/IEC 27037)."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import ValidationError
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from jullforensics.domain.case import Case, CaseStatus, Examiner, LegalBasis, LegalBasisType


class CaseView(QWidget):
    """Formulario estricto de captura de metadatos procesales y legitimación forense."""

    case_saved = Signal(object)  # Emite Case validado

    def __init__(self) -> None:
        super().__init__()
        self._current_case: Case | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)

        # 1. Metadatos del Caso
        grp_case = QGroupBox("DATOS DE LA ACTUACIÓN JUDICIAL / CASO")
        fl_case = QFormLayout(grp_case)

        self._in_case_id = QLineEdit("JF-2026-0001")
        self._in_title = QLineEdit("Operación de Extracción Forense")
        self._in_docket = QLineEdit("DP-001/2026")
        self._in_agency = QLineEdit("Policía Judicial / Laboratorio Forense")
        self._in_desc = QTextEdit()
        self._in_desc.setMaximumHeight(60)
        self._in_desc.setPlaceholderText("Descripción física del terminal, funda, golpes, etc.")

        fl_case.addRow("IDENTIFICADOR DEL CASO:", self._in_case_id)
        fl_case.addRow("TÍTULO / ASUNTO:", self._in_title)
        fl_case.addRow("SUMARIO / CAUSA JUDICIAL:", self._in_docket)
        fl_case.addRow("ORGANISMO SOLICITANTE:", self._in_agency)
        fl_case.addRow("DESCRIPCIÓN DEL TERMINAL:", self._in_desc)
        layout.addWidget(grp_case)

        # 2. Datos del Perito / Examinador
        grp_exam = QGroupBox("FILIACIÓN DEL EXAMINADOR / PERITO FORENSE")
        fl_exam = QFormLayout(grp_exam)

        self._in_exam_name = QLineEdit("Perito Judicial")
        self._in_exam_badge = QLineEdit("PER-001")
        self._in_exam_org = QLineEdit("Laboratorio Central de Evidencias Digitales")
        self._in_exam_email = QLineEdit("perito@forense.local")

        fl_exam.addRow("NOMBRE DEL PERITO:", self._in_exam_name)
        fl_exam.addRow("CARNET / PLACA / ID:", self._in_exam_badge)
        fl_exam.addRow("LABORATORIO / CUERPO:", self._in_exam_org)
        fl_exam.addRow("EMAIL INSTITUCIONAL:", self._in_exam_email)
        layout.addWidget(grp_exam)

        # 3. Fundamento Jurídico (Mandato / Orden)
        grp_legal = QGroupBox("LEGITIMACIÓN JURÍDICA (ISO/IEC 27037 / DEFENSA PROCESAL)")
        fl_legal = QFormLayout(grp_legal)

        self._cb_legal_type = QComboBox()
        for lt in LegalBasisType:
            self._cb_legal_type.addItem(lt.value, lt)

        self._in_legal_ref = QLineEdit("AUTO-2026-ORD-01")
        self._in_legal_auth = QLineEdit("Juzgado de Instrucción de Guardia")
        self._in_legal_date = QLineEdit(datetime.now(UTC).strftime("%Y-%m-%d"))
        self._in_legal_hash = QLineEdit()
        self._in_legal_hash.setPlaceholderText("Hash SHA-256 del oficio u orden digital (opcional)")

        fl_legal.addRow("TIPO DE BASE LEGAL:", self._cb_legal_type)
        fl_legal.addRow("EXPEDIENTE / OFICIO:", self._in_legal_ref)
        fl_legal.addRow("AUTORIDAD EMISORA:", self._in_legal_auth)
        fl_legal.addRow("FECHA DE EMISIÓN:", self._in_legal_date)
        fl_legal.addRow("HASH ORDEN (SHA-256):", self._in_legal_hash)
        layout.addWidget(grp_legal)

        # Barra de estado de validación y botón
        bottom_bar = QHBoxLayout()
        self._lbl_status = QLabel("● ESTADO: CASO PENDIENTE DE VALIDACIÓN")
        self._lbl_status.setStyleSheet("font-weight: bold; color: #666666;")

        self._btn_save = QPushButton("VALIDAR Y REGISTRAR CASO")
        self._btn_save.setObjectName("btn_primary")
        self._btn_save.clicked.connect(self._validate_and_save)

        bottom_bar.addWidget(self._lbl_status, stretch=1)
        bottom_bar.addWidget(self._btn_save, stretch=0)
        layout.addLayout(bottom_bar)

        scroll.setWidget(container)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _validate_and_save(self) -> None:
        try:
            examiner = Examiner(
                name=self._in_exam_name.text().strip(),
                badge_or_id=self._in_exam_badge.text().strip(),
                organization=self._in_exam_org.text().strip(),
                email=self._in_exam_email.text().strip() or None,
            )
            legal = LegalBasis(
                type=LegalBasisType(self._cb_legal_type.currentText()),
                reference=self._in_legal_ref.text().strip(),
                authority=self._in_legal_auth.text().strip(),
                date_issued=self._in_legal_date.text().strip(),
                document_hash_sha256=self._in_legal_hash.text().strip() or None,
            )
            case = Case(
                case_id=self._in_case_id.text().strip(),
                title=self._in_title.text().strip(),
                docket_number=self._in_docket.text().strip(),
                agency=self._in_agency.text().strip(),
                examiner=examiner,
                legal_basis=legal,
                device_description=self._in_desc.toPlainText().strip(),
                status=CaseStatus.OPEN,
            )
            self._current_case = case
            self._lbl_status.setText("✓ CASO VALIDADO Y AUTORIZADO (ISO 27037)")
            self._lbl_status.setStyleSheet("font-weight: bold; color: #00873E;")
            self.case_saved.emit(case)
        except (ValidationError, ValueError) as err:
            self._current_case = None
            self._lbl_status.setText(f"⚠ ERROR DE VALIDACIÓN: {err}")
            self._lbl_status.setStyleSheet("font-weight: bold; color: #D7261E;")

    def get_case(self) -> Case | None:
        if self._current_case is None:
            self._validate_and_save()
        return self._current_case

    def set_case(self, case: Case) -> None:
        self._current_case = case
        self._in_case_id.setText(case.case_id)
        self._in_title.setText(case.title)
        self._in_docket.setText(case.docket_number)
        self._in_agency.setText(case.agency)
        self._in_desc.setPlainText(case.device_description)
        self._in_exam_name.setText(case.examiner.name)
        self._in_exam_badge.setText(case.examiner.badge_or_id)
        self._in_exam_org.setText(case.examiner.organization)
        self._in_exam_email.setText(case.examiner.email or "")
        idx = self._cb_legal_type.findText(case.legal_basis.type.value)
        if idx >= 0:
            self._cb_legal_type.setCurrentIndex(idx)
        self._in_legal_ref.setText(case.legal_basis.reference)
        self._in_legal_auth.setText(case.legal_basis.authority)
        self._in_legal_date.setText(case.legal_basis.date_issued)
        self._in_legal_hash.setText(case.legal_basis.document_hash_sha256 or "")
        self._lbl_status.setText("✓ CASO CARGADO Y AUTORIZADO (ISO 27037)")
        self._lbl_status.setStyleSheet("font-weight: bold; color: #00873E;")
