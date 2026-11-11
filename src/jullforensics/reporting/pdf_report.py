"""Generador de dictamen pericial forense en formato PDF judicial (ISO/IEC 27042 / 27050)."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

if TYPE_CHECKING:
    from jullforensics.domain.case import Case
    from jullforensics.domain.device import DeviceInfo
    from jullforensics.storage.evidence_store import EvidenceStore


class NumberedCanvas(canvas.Canvas):  # type: ignore[misc]
    """Canvas de dos pasadas para calcular y numerar páginas dinámicamente."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int) -> None:
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#0A0A0A"))

        # Encabezado en páginas posteriores a la primera
        if self._pageNumber > 1:
            self.drawString(
                54,
                800,
                "DICTAMEN PERICIAL FORENSE DIGITAL - EVIDENCIA RESERVADA (ISO/IEC 27037)",
            )
            self.setStrokeColor(colors.HexColor("#0A0A0A"))
            self.setLineWidth(1)
            self.line(54, 794, 541, 794)

        # Pie de página en todas las páginas
        self.setFont("Helvetica", 8)
        self.setStrokeColor(colors.HexColor("#0A0A0A"))
        self.setLineWidth(1)
        self.line(54, 45, 541, 45)

        self.drawString(54, 32, "JullForensics v0.1.0 | Sistema de Extracción Forense Android")
        page_str = f"Página {self._pageNumber} de {total_pages}"
        self.drawRightString(541, 32, page_str)
        self.restoreState()


def generate_pdf_report(
    case: Case,
    device: DeviceInfo,
    store: EvidenceStore,
    tar_info: dict[str, str] | None = None,
) -> bytes:
    """Compila y genera el dictamen forense pericial judicial en formato PDF (A4)."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#0A0A0A"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#333333"),
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=colors.white,
        backColor=colors.HexColor("#0A0A0A"),
        spaceBefore=10,
        spaceAfter=6,
        leftIndent=6,
        rightIndent=6,
    )
    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#0A0A0A"),
    )
    mono_style = ParagraphStyle(
        "DocMono",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7,
        leading=9,
        wordWrap="CJK",
    )

    story: list[Any] = []

    # Título principal
    story.append(Paragraph("DICTAMEN PERICIAL FORENSE DIGITAL", title_style))
    story.append(
        Paragraph(
            "EXTRACCIÓN LÓGICA DE DISPOSITIVO ANDROID | "
            "CONFORMIDAD ISO/IEC 27037:2012 / 27042:2015",
            subtitle_style,
        )
    )

    now_utc = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Resumen del caso (Banner superior)
    case_summary_data = [
        [
            Paragraph("<b>EXPEDIENTE CASO:</b>", body_style),
            Paragraph(f"<b>{case.case_id}</b>", body_style),
            Paragraph("<b>CAUSA JUDICIAL:</b>", body_style),
            Paragraph(case.docket_number, body_style),
        ],
        [
            Paragraph("<b>ORGANISMO:</b>", body_style),
            Paragraph(case.agency, body_style),
            Paragraph("<b>FECHA EMISIÓN:</b>", body_style),
            Paragraph(now_utc, body_style),
        ],
    ]
    t_case = Table(case_summary_data, colWidths=[100, 140, 100, 147])
    t_case.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFEFEF")),
                ("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor("#0A0A0A")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t_case)
    story.append(Spacer(1, 8))

    # Sección 1: Fundamento Jurídico y Examinador
    story.append(Paragraph("1. FUNDAMENTO JURÍDICO Y EXAMINADOR PERICIAL", h2_style))
    legal_data = [
        [
            Paragraph("<b>Base Legal:</b>", body_style),
            Paragraph(f"{case.legal_basis.type} ({case.legal_basis.reference})", body_style),
        ],
        [
            Paragraph("<b>Autoridad Emisora:</b>", body_style),
            Paragraph(case.legal_basis.authority, body_style),
        ],
        [
            Paragraph("<b>Perito Designado:</b>", body_style),
            Paragraph(f"{case.examiner.name} (Carnet: {case.examiner.badge_or_id})", body_style),
        ],
        [
            Paragraph("<b>Organización:</b>", body_style),
            Paragraph(f"{case.examiner.organization} ({case.examiner.email or ''})", body_style),
        ],
    ]
    t_legal = Table(legal_data, colWidths=[130, 357])
    t_legal.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0A0A0A")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t_legal)
    story.append(Spacer(1, 8))

    # Sección 2: Identificación del Dispositivo Móvil
    story.append(Paragraph("2. IDENTIFICACIÓN Y ESTADO TÉCNICO DEL DISPOSITIVO", h2_style))
    dev_data = [
        [
            Paragraph("<b>Marca / Modelo:</b>", body_style),
            Paragraph(f"{device.brand} {device.model} ({device.manufacturer})", body_style),
        ],
        [
            Paragraph("<b>Número Serie ADB:</b>", body_style),
            Paragraph(f"<b>{device.serial}</b>", body_style),
        ],
        [
            Paragraph("<b>Android OS / SDK:</b>", body_style),
            Paragraph(f"Android {device.android_version} (API {device.sdk_version})", body_style),
        ],
        [
            Paragraph("<b>Parche de Seguridad:</b>", body_style),
            Paragraph(device.security_patch, body_style),
        ],
        [
            Paragraph("<b>Huella Compilación:</b>", body_style),
            Paragraph(device.build_fingerprint, mono_style),
        ],
        [
            Paragraph("<b>Desviación Reloj:</b>", body_style),
            Paragraph(f"{device.clock_offset_seconds:.2f} segundos respecto a UTC", body_style),
        ],
    ]
    t_dev = Table(dev_data, colWidths=[130, 357])
    t_dev.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0A0A0A")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t_dev)
    story.append(Spacer(1, 8))

    # Sección 3: Cadena de Custodia
    story.append(Paragraph("3. REGISTRO DE CADENA DE CUSTODIA (ISO/IEC 27037)", h2_style))
    custody_rows = [
        [
            Paragraph("<b>Fecha/Hora UTC</b>", body_style),
            Paragraph("<b>Evento</b>", body_style),
            Paragraph("<b>Responsable</b>", body_style),
            Paragraph("<b>Hash SHA-256</b>", body_style),
        ]
    ]
    for ev in case.chain_of_custody:
        custody_rows.append(
            [
                Paragraph(ev.ts_utc[:19], mono_style),
                Paragraph(f"<b>{ev.event_type}</b>", body_style),
                Paragraph(f"{ev.actor} ({ev.location})", body_style),
                Paragraph(ev.evidence_hash_sha256[:20] + "...", mono_style),
            ]
        )
    if len(custody_rows) == 1:
        custody_rows.append(
            [Paragraph("Sin registros adicionales de custodia", body_style), "", "", ""]
        )

    t_cust = Table(custody_rows, colWidths=[95, 125, 145, 122])
    t_cust.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCDCDC")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0A0A0A")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t_cust)
    story.append(Spacer(1, 8))

    # Sección 4: Artefactos y Resúmenes Criptográficos
    story.append(Paragraph("4. ARTEFACTOS FORENSES Y RESÚMENES SHA-256", h2_style))
    art_rows = [
        [
            Paragraph("<b>Archivo Relativo</b>", body_style),
            Paragraph("<b>Módulo</b>", body_style),
            Paragraph("<b>Bytes</b>", body_style),
            Paragraph("<b>Hash SHA-256</b>", body_style),
        ]
    ]
    for art in store.artifacts:
        art_rows.append(
            [
                Paragraph(art.relative_path, body_style),
                Paragraph(art.module, body_style),
                Paragraph(str(art.size_bytes), body_style),
                Paragraph(art.sha256, mono_style),
            ]
        )
    t_art = Table(art_rows, colWidths=[150, 80, 50, 207])
    t_art.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCDCDC")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0A0A0A")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t_art)
    story.append(Spacer(1, 8))

    # Sección 5: Registro Chained Log e Integridad
    story.append(Paragraph("5. AUDITORÍA INALTERABLE Y DECLARACIÓN JURADA", h2_style))
    audit_data = [
        [
            Paragraph("<b>Entradas en Chained Log:</b>", body_style),
            Paragraph(f"{store.logger.entry_count} eventos secuenciales protegidos", body_style),
        ],
        [
            Paragraph("<b>Head Hash Encadenado:</b>", body_style),
            Paragraph(store.logger.head_hash, mono_style),
        ],
    ]
    if tar_info:
        audit_data.append(
            [
                Paragraph("<b>Contenedor JF-TAR:</b>", body_style),
                Paragraph(
                    f"{tar_info.get('file', '')} (SHA-256: {tar_info.get('sha256', '')})",
                    mono_style,
                ),
            ]
        )
    t_audit = Table(audit_data, colWidths=[150, 337])
    t_audit.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0A0A0A")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t_audit)
    story.append(Spacer(1, 10))

    # Declaración jurada y firmas
    statement = (
        "El perito informático forense abajo firmante certifica haber practicado la extracción "
        "lógica en estricto cumplimiento con los principios de mínima intrusión y reproducibilidad "
        "establecidos en la norma ISO/IEC 27037:2012 y el Código Procesal Penal. "
        "Todas las operaciones fueron registradas en el libro diario inalterable y "
        "selladas con firma digital."
    )
    story.append(Paragraph(statement, body_style))
    story.append(Spacer(1, 20))

    sig_data = [
        [
            Paragraph(
                f"<br/><br/><br/>___________________________________<br/>"
                f"<b>{case.examiner.name}</b><br/>"
                f"Perito Informático Forense<br/>Carnet/Reg: {case.examiner.badge_or_id}",
                ParagraphStyle("Sig1", parent=body_style, alignment=1),
            ),
            Paragraph(
                "<br/><br/><br/>___________________________________<br/>"
                "<b>Sello del Laboratorio / Juzgado</b><br/>"
                "Conformidad de Recepción",
                ParagraphStyle("Sig2", parent=body_style, alignment=1),
            ),
        ]
    ]
    t_sig = Table(sig_data, colWidths=[243, 244])
    t_sig.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(KeepTogether(t_sig))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()
