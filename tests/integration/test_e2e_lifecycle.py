"""Prueba integral de ciclo de vida forense (E2E) y validación empírica ISO/IEC 27041."""

from __future__ import annotations

import struct
from pathlib import Path
from unittest.mock import MagicMock

from cryptography.hazmat.primitives.asymmetric import ed25519

from jullforensics.acquisition.screenshot import PNG_SIGNATURE
from jullforensics.adb.runner import AdbRunner
from jullforensics.domain.case import Case, CaseStatus, Examiner, LegalBasis, LegalBasisType
from jullforensics.domain.custody import CustodyEventType
from jullforensics.domain.device import DeviceInfo
from jullforensics.integrity.chained_log import ChainedLog
from jullforensics.integrity.signing import Verifier
from jullforensics.integrity.verify import verify_case_directory, verify_tar_container
from jullforensics.services.acquisition_service import AcquisitionService, ProfileType
from jullforensics.storage.evidence_store import EvidenceStore


def _make_dummy_png(width: int = 1080, height: int = 2400) -> bytes:
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_chunk = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + b"\x00\x00\x00\x00"
    return PNG_SIGNATURE + ihdr_chunk + b"IDAT" + b"\x00" * 200 + b"IEND\x00\x00\x00\x00"


def test_e2e_forensic_acquisition_and_verification(tmp_path: Path) -> None:
    # 1. Definir caso formal bajo ISO 27037
    examiner = Examiner(
        name="Inspectora Elena Vega",
        badge_or_id="CNP-89211",
        organization="Sección de Delitos Telemáticos",
        email="evega@policia.es",
    )
    legal_basis = LegalBasis(
        type=LegalBasisType.ORDEN_JUDICIAL,
        reference="AUTO-2026-DP-912",
        authority="Juzgado Central de Instrucción 4",
        date_issued="2026-11-10",
        document_hash_sha256="e" * 64,
        notes="Autorización judicial para clonado y extracción lógica integral",
    )
    case = Case(
        case_id="JF-2026-E2E01",
        title="Diligencias Previas 912/26 - Operación Criptón",
        docket_number="DP-912-2026",
        agency="Audiencia Nacional",
        examiner=examiner,
        legal_basis=legal_basis,
        device_description="Terminal Google Pixel 8 Pro negro en funda rígida",
    )

    # 2. Inicializar subsistema de almacenamiento y auditoría
    case_dir = tmp_path / "case_storage"
    log_file = tmp_path / "chain.jsonl"
    logger = ChainedLog(log_file, key=b"e2e-hmac-key-for-test-32-bytes!!")
    store = EvidenceStore(case_dir, case, logger)

    # 3. Datos del dispositivo conectado
    device = DeviceInfo(
        serial="P8P-E2E-TEST01",
        model="Pixel 8 Pro",
        brand="Google",
        manufacturer="Google",
        android_version="14",
        sdk_version=34,
        security_patch="2026-10-01",
        build_fingerprint="google/husky:14/UQ1A.240105.004:user/release-keys",
        build_id="UQ1A.240105.004",
        battery_level_percent=92,
        clock_offset_seconds=-0.08,
        encryption_state="encrypted",
    )

    # 4. Configurar simulador de respuestas ADB
    dummy_png = _make_dummy_png()
    dummy_props = b"[ro.product.model]: [Pixel 8 Pro]\n[ro.build.version.release]: [14]\n"
    dummy_pkgs = b"package:com.google.android.apps.messaging\npackage:org.telegram.messenger\n"
    dummy_dumps = (
        b"DUMP OF SERVICE activity:\n  ActivityRecord{com.google.android.apps.messaging}\n"
    )
    dummy_contacts = b"Row: 0 _id=1, display_name=Contacto Principal, data1=+34600000000\n"

    def mock_adb_run(*args: str, **kwargs: object) -> MagicMock:
        cmd = args[0] if args else ""
        if cmd == "exec-out" and len(args) > 1 and args[1] == "screencap":
            return MagicMock(returncode=0, stdout=dummy_png, stderr=b"")
        if cmd == "shell":
            subcmd = args[1] if len(args) > 1 else ""
            if subcmd == "getprop":
                return MagicMock(returncode=0, stdout=dummy_props, stderr=b"")
            if subcmd == "pm":
                return MagicMock(returncode=0, stdout=dummy_pkgs, stderr=b"")
            if subcmd == "dumpsys":
                return MagicMock(returncode=0, stdout=dummy_dumps, stderr=b"")
            if subcmd == "content":
                return MagicMock(returncode=0, stdout=dummy_contacts, stderr=b"")
            return MagicMock(returncode=0, stdout=b"output\n", stderr=b"")
        return MagicMock(returncode=0, stdout=b"", stderr=b"")

    runner = AdbRunner(serial=device.serial)
    runner.run = MagicMock(side_effect=mock_adb_run)  # type: ignore[method-assign]

    # 5. Generar clave asimétrica Ed25519 para sellado judicial
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    # 6. Ejecutar adquisición lógica completa (Perfil ESTÁNDAR)
    service = AcquisitionService(runner=runner, store=store)
    summary = service.run_acquisition(
        case=case,
        device=device,
        profile=ProfileType.ESTANDAR,
        private_key=private_key,
    )

    # 7. Verificación del resumen pericial
    assert summary.status == "COMPLETED"
    assert summary.case_id == case.case_id
    assert summary.serial == device.serial
    assert summary.total_artifacts >= 6
    assert summary.tar_path is not None
    assert summary.tar_sha256 is not None
    assert summary.tar_sha512 is not None

    tar_path = Path(summary.tar_path)
    assert tar_path.is_file()
    assert tar_path.with_suffix(".tar.sha256").is_file()
    assert tar_path.with_suffix(".tar.sha512").is_file()
    assert tar_path.with_suffix(".tar.sig").is_file()
    assert Verifier.verify(
        public_key,
        tar_path.read_bytes(),
        tar_path.with_suffix(".tar.sig").read_bytes(),
    )

    # 8. Verificación de la cadena de custodia
    assert case.status == CaseStatus.COMPLETED
    event_types = [e.event_type for e in case.chain_of_custody]
    assert CustodyEventType.EXTRACTION_STARTED in event_types
    assert CustodyEventType.CONTAINER_SEALED in event_types

    # 9. Verificación de reportes (JSON, HTML, PDF)
    assert (store.base_dir / "reports" / "report.json").is_file()
    assert (store.base_dir / "reports" / "report.html").is_file()
    assert (store.base_dir / "reports" / "report.pdf").is_file()

    # 10. Validación independiente desde disco (verify_tar_container)
    assert verify_tar_container(tar_path) == 0

    # 11. Validación independiente del directorio del caso (verify_case_directory)
    assert verify_case_directory(store.base_dir) == 0

    # 12. Simulación de manipulación intencionada de un bit en el contenedor TAR
    tar_bytes = bytearray(tar_path.read_bytes())
    tar_bytes[len(tar_bytes) // 2] ^= 0xFF  # Invertir 8 bits en la mitad del TAR
    tampered_tar = tmp_path / "tampered.tar"
    tampered_tar.write_bytes(tar_bytes)
    # Copiar sidecar de hash original para probar la detección
    (tmp_path / "tampered.tar.sha256").write_text(
        f"{summary.tar_sha256}  tampered.tar\n", encoding="utf-8"
    )

    assert verify_tar_container(tampered_tar) != 0
