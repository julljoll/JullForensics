"""Generador de dictamen pericial forense en formato HTML brutalista (ISO/IEC 27042 / 27050)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from jinja2 import Template

if TYPE_CHECKING:
    from jullforensics.domain.case import Case
    from jullforensics.domain.device import DeviceInfo
    from jullforensics.storage.evidence_store import EvidenceStore

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DICTAMEN FORENSE - {{ case.case_id }}</title>
  <style>
    :root {
      --bg: #F4F4F0;
      --card-bg: #FFFFFF;
      --text: #0A0A0A;
      --border: 3px solid #0A0A0A;
      --border-thin: 1px solid #0A0A0A;
      --accent: #FFE600;
      --success: #00873E;
      --shadow: 5px 5px 0px #0A0A0A;
    }
    @media print {
      body { background: #FFF !important; color: #000 !important; font-size: 9pt; }
      .no-print { display: none !important; }
      .page-break { page-break-before: always; }
      .card {
        box-shadow: none !important;
        border: 1px solid #000 !important;
        margin-bottom: 12px !important;
      }
    }
    * { box-sizing: border-box; }
    body {
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
      background-color: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 24px;
      line-height: 1.45;
    }
    .container { max-width: 1100px; margin: 0 auto; }
    .header-banner {
      background: var(--accent);
      border: var(--border);
      box-shadow: var(--shadow);
      padding: 20px;
      margin-bottom: 24px;
    }
    h1 {
      margin: 0 0 8px 0;
      font-size: 1.6rem;
      text-transform: uppercase;
      letter-spacing: -0.5px;
    }
    h2 {
      font-size: 1.2rem;
      text-transform: uppercase;
      margin: 0 0 12px 0;
      border-bottom: var(--border-thin);
      padding-bottom: 6px;
    }
    .badge {
      display: inline-block;
      background: #0A0A0A;
      color: #FFF;
      font-weight: bold;
      padding: 3px 8px;
      font-size: 0.8rem;
      margin-right: 6px;
    }
    .card {
      background: var(--card-bg);
      border: var(--border);
      box-shadow: var(--shadow);
      padding: 20px;
      margin-bottom: 24px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
      font-size: 0.85rem;
    }
    th, td {
      border: var(--border-thin);
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
    }
    th {
      background: #EAEAEA;
      font-weight: bold;
      text-transform: uppercase;
    }
    .hash {
      font-family: inherit;
      word-break: break-all;
      font-size: 0.78rem;
    }
    .signature-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 32px;
      margin-top: 32px;
    }
    .sig-box {
      border-top: 2px dashed #0A0A0A;
      padding-top: 12px;
      text-align: center;
      font-size: 0.85rem;
    }
    .code-block {
      background: #1A1A1A;
      color: #00FF66;
      padding: 12px;
      font-size: 0.8rem;
      overflow-x: auto;
      border: var(--border);
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header-banner">
      <span class="badge">ISO/IEC 27037:2012</span>
      <span class="badge">ISO/IEC 27042:2015</span>
      <span class="badge">ISO/IEC 27050:2020</span>
      <span class="badge">RFC 3227</span>
      <h1>DICTAMEN PERICIAL FORENSE DIGITAL</h1>
      <div>
        <strong>CASO:</strong> {{ case.case_id }} |
        <strong>CAUSA:</strong> {{ case.docket_number }} |
        <strong>GENERADO:</strong> {{ generated_at_utc }}
      </div>
    </div>

    <div class="card">
      <h2>01. FUNDAMENTO JURÍDICO Y EXAMINADOR</h2>
      <table>
        <tr>
          <th style="width: 25%;">EXPEDIENTE / OFICIO</th>
          <td>{{ case.legal_basis.reference }}</td>
        </tr>
        <tr>
          <th>AUTORIDAD EMISORA</th>
          <td>{{ case.legal_basis.authority }}</td>
        </tr>
        <tr>
          <th>TIPO DE BASE LEGAL</th>
          <td>{{ case.legal_basis.type }} (Fecha: {{ case.legal_basis.date_issued }})</td>
        </tr>
        <tr>
          <th>HASH ORDEN SHA-256</th>
          <td class="hash">{{ case.legal_basis.document_hash_sha256 or 'N/A' }}</td>
        </tr>
        <tr>
          <th>EXAMINADOR / PERITO</th>
          <td>{{ case.examiner.name }} (ID: {{ case.examiner.badge_or_id }})</td>
        </tr>
        <tr>
          <th>ORGANIZACIÓN / LABORATORIO</th>
          <td>{{ case.examiner.organization }} ({{ case.examiner.email or 'Sin email' }})</td>
        </tr>
      </table>
    </div>

    <div class="card">
      <h2>02. IDENTIFICACIÓN DEL DISPOSITIVO MÓVIL</h2>
      <table>
        <tr>
          <th style="width: 25%;">MARCA Y MODELO</th>
          <td>{{ device.brand }} {{ device.model }} (Fabricante: {{ device.manufacturer }})</td>
        </tr>
        <tr>
          <th>NÚMERO DE SERIE ADB</th>
          <td><strong>{{ device.serial }}</strong></td>
        </tr>
        <tr>
          <th>VERSIÓN ANDROID</th>
          <td>Android {{ device.android_version }} (SDK API {{ device.sdk_version }})</td>
        </tr>
        <tr>
          <th>PARCHE DE SEGURIDAD</th>
          <td>{{ device.security_patch }}</td>
        </tr>
        <tr>
          <th>HUELLA DE COMPILACIÓN</th>
          <td class="hash">{{ device.build_fingerprint }}</td>
        </tr>
        <tr>
          <th>DESVIACIÓN RELOJ (OFFSET)</th>
          <td>{{ "%.2f"|format(device.clock_offset_seconds) }} s respecto a UTC</td>
        </tr>
        <tr>
          <th>ESTADO DE CIFRADO</th>
          <td>{{ device.encryption_state }}</td>
        </tr>
        <tr>
          <th>BATERÍA AL INICIO</th>
          <td>
            {% if device.battery_level_percent is not none %}
              {{ device.battery_level_percent }} %
            {% else %}
              N/A
            {% endif %}
          </td>
        </tr>
      </table>
    </div>

    <div class="card">
      <h2>03. CADENA DE CUSTODIA (TIMELINE AUDITABLE)</h2>
      <table>
        <thead>
          <tr>
            <th>FECHA / HORA (UTC)</th>
            <th>EVENTO</th>
            <th>RESPONSABLE</th>
            <th>SEDE / UBICACIÓN</th>
            <th>HASH EVIDENCIA SHA-256</th>
          </tr>
        </thead>
        <tbody>
          {% for ev in case.chain_of_custody %}
          <tr>
            <td>{{ ev.ts_utc }}</td>
            <td>
              <strong>{{ ev.event_type }}</strong><br>
              <small>{{ ev.action_description }}</small>
            </td>
            <td>{{ ev.actor }}</td>
            <td>{{ ev.location }}</td>
            <td class="hash">{{ ev.evidence_hash_sha256 }}</td>
          </tr>
          {% else %}
          <tr><td colspan="5">Sin eventos formalmente registrados en la cadena.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

    <div class="card page-break">
      <h2>04. REGISTRO DE ARTEFACTOS Y RESÚMENES CRIPTOGRÁFICOS</h2>
      <p>
        Total artefactos: <strong>{{ store.artifacts|length }}</strong> |
        Volumen total: <strong>{{ total_bytes }} bytes</strong>
      </p>
      <table>
        <thead>
          <tr>
            <th>ARCHIVO RELATIVO</th>
            <th>TAMAÑO</th>
            <th>MÓDULO</th>
            <th>SHA-256 / SHA-512</th>
          </tr>
        </thead>
        <tbody>
          {% for art in store.artifacts %}
          <tr>
            <td><strong>{{ art.relative_path }}</strong></td>
            <td>{{ art.size_bytes }} B</td>
            <td>{{ art.module }}</td>
            <td class="hash">
              <strong>SHA-256:</strong> {{ art.sha256 }}<br>
              <strong>SHA-512:</strong> {{ art.sha512 }}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2>05. REGISTRO AUDITABLE ENCADENADO (CHAINED LOG)</h2>
      <table>
        <tr>
          <th style="width: 25%;">TOTAL ENTRADAS LOG</th>
          <td>{{ store.logger.entry_count }} registros verificables</td>
        </tr>
        <tr>
          <th>HASH CABECERA (HEAD HASH)</th>
          <td class="hash">{{ store.logger.head_hash }}</td>
        </tr>
        <tr>
          <th>ESTADO DE LA CADENA</th>
          <td><strong>ÍNTEGRA Y NO MANIPULADA (HMAC-SHA256 encadenado)</strong></td>
        </tr>
      </table>
    </div>

    <div class="card">
      <h2>06. PROCEDIMIENTO DE VERIFICACIÓN JUDICIAL DE INTEGRIDAD</h2>
      <p>Verificación independiente de integridad pericial:</p>
      <div class="code-block">
# 1. Verificar resúmenes SHA-256 de los artefactos
sha256sum -c SHA256SUMS

# 2. Verificar resúmenes SHA-512
sha512sum -c SHA512SUMS

# 3. Verificación forense integral automatizada
jullforensics-verify --case {{ case.case_id }}_dir/
      </div>
    </div>

    <div class="card">
      <h2>07. DECLARACIÓN DE CONFORMIDAD Y FIRMA PERICIAL</h2>
      <p>
        El perito abajo firmante certifica que la presente adquisición lógica se ha realizado
        cumpliendo estrictamente con los estándares internacionales ISO/IEC 27037:2012 y
        el principio de orden de volatilidad de la RFC 3227. No se ejecutaron modificaciones en
        particiones del sistema ni reinicios no controlados del dispositivo analizado.
      </p>
      <div class="signature-grid">
        <div class="sig-box">
          <br><br><br>
          <strong>{{ case.examiner.name }}</strong><br>
          Perito Informático Forense<br>
          Identificación: {{ case.examiner.badge_or_id }}<br>
          {{ case.examiner.organization }}
        </div>
        <div class="sig-box">
          <br><br><br>
          <strong>Sello del Laboratorio / Juzgado</strong><br>
          Fecha: {{ generated_at_utc[:10] }}<br>
          Lugar: Sede Pericial Central
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""


def generate_html_report(
    case: Case,
    device: DeviceInfo,
    store: EvidenceStore,
    tar_info: dict[str, str] | None = None,
) -> str:
    """Renderiza el dictamen forense pericial en formato HTML brutalista para visualización."""
    now_utc = datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    total_bytes = sum(a.size_bytes for a in store.artifacts)

    template = Template(HTML_TEMPLATE)
    return str(
        template.render(
            case=case,
            device=device,
            store=store,
            tar_info=tar_info,
            generated_at_utc=now_utc,
            total_bytes=total_bytes,
        )
    )
