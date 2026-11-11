"""Coordinador maestro de generación y persistencia de dictámenes periciales."""

from __future__ import annotations

from typing import TYPE_CHECKING

from jullforensics.reporting.html_report import generate_html_report
from jullforensics.reporting.json_report import generate_json_report
from jullforensics.reporting.pdf_report import generate_pdf_report

if TYPE_CHECKING:
    from jullforensics.domain.case import Case
    from jullforensics.domain.device import DeviceInfo
    from jullforensics.storage.evidence_store import EvidenceStore


class ReportGenerator:
    """Genera y archiva dictámenes periciales en JSON, HTML y PDF en el almacén de evidencias."""

    def __init__(self, case: Case, device: DeviceInfo, store: EvidenceStore) -> None:
        self.case = case
        self.device = device
        self.store = store

    def generate_all(self, tar_info: dict[str, str] | None = None) -> dict[str, dict[str, str]]:
        """Genera los 3 formatos periciales y los persiste en el EvidenceStore con hashes en vuelo.

        Retorna un diccionario:
            {
                "json": {"path": "reports/report.json", "sha256": "...", ...},
                "html": {"path": "reports/report.html", "sha256": "...", ...},
                "pdf":  {"path": "reports/report.pdf",  "sha256": "...", ...},
            }
        """
        results: dict[str, dict[str, str]] = {}

        # 1. Reporte JSON estructurado
        json_content = generate_json_report(self.case, self.device, self.store, tar_info=tar_info)
        json_digests = self.store.put_bytes(
            "reports/report.json",
            json_content.encode("utf-8"),
            module="reporting_json",
        )
        results["json"] = {"path": "reports/report.json", **json_digests}

        # 2. Reporte HTML brutalista para visualización web / impresión
        html_content = generate_html_report(self.case, self.device, self.store, tar_info=tar_info)
        html_digests = self.store.put_bytes(
            "reports/report.html",
            html_content.encode("utf-8"),
            module="reporting_html",
        )
        results["html"] = {"path": "reports/report.html", **html_digests}

        # 3. Dictamen Judicial PDF firmado digitalmente
        pdf_bytes = generate_pdf_report(self.case, self.device, self.store, tar_info=tar_info)
        pdf_digests = self.store.put_bytes(
            "reports/report.pdf",
            pdf_bytes,
            module="reporting_pdf",
        )
        results["pdf"] = {"path": "reports/report.pdf", **pdf_digests}

        self.store.logger.append(
            "REPORTS_GENERATED",
            "reporting",
            {
                "json_sha256": json_digests.get("sha256"),
                "html_sha256": html_digests.get("sha256"),
                "pdf_sha256": pdf_digests.get("sha256"),
            },
        )
        return results
