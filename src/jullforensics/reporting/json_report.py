"""Generación de dictamen pericial en formato estructurado JSON (ISO/IEC 27050-3)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jullforensics.domain.case import Case
    from jullforensics.domain.device import DeviceInfo
    from jullforensics.storage.evidence_store import EvidenceStore


def generate_json_report(
    case: Case,
    device: DeviceInfo,
    store: EvidenceStore,
    tar_info: dict[str, str] | None = None,
) -> str:
    """Genera el contenido del reporte forense en JSON legible por máquina."""
    now_utc = datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")

    total_bytes = sum(a.size_bytes for a in store.artifacts)

    report_dict: dict[str, Any] = {
        "$schema": "https://jullforensics.local/schemas/report-v1.json",
        "standard": "ISO/IEC 27050-3:2020 / ISO/IEC 27037:2012",
        "generator": "JullForensics 0.1.0",
        "generated_at_utc": now_utc,
        "case": {
            "case_id": case.case_id,
            "title": case.title,
            "docket_number": case.docket_number,
            "agency": case.agency,
            "device_description": case.device_description,
            "created_at_utc": case.created_at_utc,
            "status": str(case.status),
            "examiner": case.examiner.model_dump(),
            "legal_basis": case.legal_basis.model_dump(),
        },
        "device": device.model_dump(),
        "chain_of_custody": [e.model_dump() for e in case.chain_of_custody],
        "integrity": {
            "total_artifacts": len(store.artifacts),
            "total_bytes": total_bytes,
            "chain_log_entries": store.logger.entry_count,
            "chain_log_head_hash": store.logger.head_hash,
        },
        "artifacts": [a.model_dump() for a in store.artifacts],
    }

    if tar_info:
        report_dict["tar_container"] = tar_info

    return json.dumps(report_dict, indent=2, ensure_ascii=False)
