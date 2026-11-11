"""Módulo de generación de dictámenes periciales y reportes forenses."""

from .html_report import generate_html_report
from .json_report import generate_json_report
from .pdf_report import generate_pdf_report
from .report_generator import ReportGenerator

__all__ = [
    "generate_json_report",
    "generate_html_report",
    "generate_pdf_report",
    "ReportGenerator",
]
