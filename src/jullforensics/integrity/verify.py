"""Utilidad CLI independiente para verificación forense de casos y contenedores JF-TAR.

Permite verificar la integridad sin requerir entorno gráfico ni credenciales del sistema.
"""

from __future__ import annotations

import argparse
import sys
import tarfile
from pathlib import Path

from jullforensics.integrity.chained_log import verify_chain
from jullforensics.integrity.hashing import hash_bytes, hash_file
from jullforensics.integrity.signing import Verifier


def verify_tar_container(tar_path: Path) -> int:
    """Verifica un contenedor .tar generado por JullForensics.

    Comprueba:
      1. Sidecars externos (.sha256 / .sha512) si existen.
      2. Miembros internos contra SHA256SUMS interno.
      3. Manifiesto y firma Ed25519 si existen dentro del archivo.
    """
    print(f"[*] Analizando contenedor forense: {tar_path}")
    if not tar_path.is_file():
        print(f"[!] Error: El archivo {tar_path} no existe.", file=sys.stderr)
        return 1

    # 1. Verificar sidecar SHA-256 externo si existe
    sidecar_sha256 = tar_path.with_suffix(".tar.sha256")
    if sidecar_sha256.is_file():
        expected_line = sidecar_sha256.read_text(encoding="utf-8").strip()
        expected_hash = expected_line.split()[0].lower()
        actual_hashes = hash_file(tar_path, ["sha256"])
        actual_hash = actual_hashes["sha256"].lower()
        if expected_hash == actual_hash:
            print(f"[✓] Sidecar SHA-256 verificado: {actual_hash}")
        else:
            print(
                f"[✗] Discrepancia en sidecar SHA-256: "
                f"esperado {expected_hash}, actual {actual_hash}",
                file=sys.stderr,
            )
            return 2

    # 2. Inspeccionar contenido interno del .tar
    try:
        with tarfile.open(tar_path, "r:*") as tar:
            members = tar.getmembers()
            print(f"[*] Total de entradas en el contenedor: {len(members)}")

            # Buscar hashes/SHA256SUMS
            sha256sums_member = next(
                (m for m in members if m.name.endswith("hashes/SHA256SUMS")), None
            )
            if sha256sums_member:
                f_sums = tar.extractfile(sha256sums_member)
                if f_sums:
                    sums_content = f_sums.read().decode("utf-8")
                    checked = 0
                    mismatches = 0
                    for line in sums_content.splitlines():
                        parts = line.strip().split(maxsplit=1)
                        if len(parts) == 2:
                            expected_digest, rel_path = parts[0].lower(), parts[1].lstrip("* ")
                            # Buscar miembro en el tar
                            matched_member = next(
                                (m for m in members if m.name.endswith(rel_path)), None
                            )
                            if matched_member:
                                f_member = tar.extractfile(matched_member)
                                if f_member:
                                    member_bytes = f_member.read()
                                    actual_digest = hash_bytes(member_bytes, ["sha256"])["sha256"]
                                    if actual_digest != expected_digest:
                                        print(
                                            f"[✗] Archivo corrupto en tar: {rel_path}",
                                            file=sys.stderr,
                                        )
                                        mismatches += 1
                                    checked += 1
                    if mismatches == 0:
                        print(
                            f"[✓] Integridad interna verificada: {checked} "
                            "artefactos validados contra SHA256SUMS."
                        )
                    else:
                        print(
                            f"[✗] Se encontraron {mismatches} discrepancias "
                            "de hash dentro del contenedor.",
                            file=sys.stderr,
                        )
                        return 3

            # Buscar log encadenado dentro del tar
            chain_member = next((m for m in members if m.name.endswith("logs/chain.jsonl")), None)
            if chain_member:
                f_chain = tar.extractfile(chain_member)
                if f_chain:
                    temp_chain = tar_path.parent / f".tmp_chain_{tar_path.stem}.jsonl"
                    temp_chain.write_bytes(f_chain.read())
                    ok, msg, count = verify_chain(temp_chain)
                    temp_chain.unlink(missing_ok=True)
                    if ok:
                        print(f"[✓] Log encadenado interno: {msg}")
                    else:
                        print(f"[✗] Fallo en log encadenado interno: {msg}", file=sys.stderr)
                        return 4

    except Exception as e:
        print(f"[!] Error leyendo estructura TAR: {e}", file=sys.stderr)
        return 5

    print("[★] El contenedor forense es íntegro y auténtico.")
    return 0


def verify_case_directory(case_dir: Path) -> int:
    """Verifica una carpeta de caso local."""
    print(f"[*] Analizando directorio de caso: {case_dir}")
    if not case_dir.is_dir():
        print(f"[!] Error: {case_dir} no es un directorio.", file=sys.stderr)
        return 1

    # 1. Verificar log encadenado
    chain_log = case_dir / "logs" / "chain.jsonl"
    if chain_log.is_file():
        ok, msg, count = verify_chain(chain_log)
        if ok:
            print(f"[✓] Registro de auditoría (logs/chain.jsonl): {msg}")
        else:
            print(f"[✗] Falla en registro de auditoría: {msg}", file=sys.stderr)
            return 2
    else:
        print("[!] Advertencia: No se encontró logs/chain.jsonl")

    # 2. Verificar manifest.json y firma
    manifest_path = case_dir / "manifest.json"
    manifest_sig = case_dir / "manifest.sig"
    pubkey_path = case_dir / "signing_pubkey.pem"

    if manifest_path.is_file() and manifest_sig.is_file() and pubkey_path.is_file():
        manifest_bytes = manifest_path.read_bytes()
        sig_bytes = manifest_sig.read_bytes()
        pubkey_pem = pubkey_path.read_bytes()
        try:
            pubkey = Verifier.load_public_key_pem(pubkey_pem)
            if Verifier.verify(pubkey, manifest_bytes, sig_bytes):
                print("[✓] Firma digital Ed25519 del manifiesto: VÁLIDA")
            else:
                print("[✗] Firma digital Ed25519 INVÁLIDA para manifest.json", file=sys.stderr)
                return 3
        except Exception as e:
            print(f"[!] Error validando firma digital: {e}", file=sys.stderr)
            return 4

    print("[★] Verificación de carpeta de caso completada con éxito.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="jullforensics-verify",
        description="Verificador forense independiente de integridad de evidencias y registros.",
    )
    parser.add_argument(
        "target",
        type=Path,
        help="Ruta al archivo contenedor (.tar) o al directorio de caso a verificar.",
    )
    args = parser.parse_args(argv)

    target_path = args.target.resolve()
    if not target_path.exists():
        print(f"[!] Error: La ruta especificada no existe: {target_path}", file=sys.stderr)
        return 1

    if target_path.is_file() and target_path.suffix == ".tar":
        return verify_tar_container(target_path)
    elif target_path.is_file() and target_path.name.endswith(".jsonl"):
        ok, msg, count = verify_chain(target_path)
        print(f"[{'✓' if ok else '✗'}] {msg}")
        return 0 if ok else 2
    elif target_path.is_dir():
        return verify_case_directory(target_path)
    else:
        print(f"[!] Formato no reconocido para verificación: {target_path}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
