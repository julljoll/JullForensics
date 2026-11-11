# INFORME DE ANÁLISIS ESTÁTICO DE SEGURIDAD (SAST) Y MODELADO DE AMENAZAS
## JullForensics v0.1.0 — Evaluación de Seguridad del Software (NIST SSDF & OWASP ASVS)

| Metadato de Seguridad | Especificación |
| :--- | :--- |
| **Fecha de Auditoría:** | 2026-11-11 |
| **Herramientas SAST:** | Bandit 1.9.4, Ruff AST Security Linter 0.17.4, Mypy Strict 2.4.1 |
| **Alcance Evaluado:** | 100% Código Fuente (`src/jullforensics/`, 4.763 líneas de código Python) |
| **Estándares de Referencia:** | NIST SP 800-218 (SSDF v1.1), OWASP ASVS 4.0.3 Nivel 2, CWE Top 25 |
| **Resultado Global:** | **0 Vulnerabilidades Críticas / 0 Altas / 0 Medias (Apto para Producción Judicial)** |

---

## 1. Resumen Ejecutivo de Vulnerabilidades

| Severidad | Total Detectadas | Mitigadas / Falsos Positivos Justificados | Pendientes |
| :--- | :---: | :---: | :---: |
| **CRÍTICA (Critical)** | 0 | 0 | 0 |
| **ALTA (High)** | 0 | 0 | 0 |
| **MEDIA (Medium)** | 0 | 0 | 0 |
| **BAJA / INFORMATIVA (Low)** | 5 | 5 (Uso de `subprocess` con `shell=False` y lista blanca) | 0 |

---

## 2. Análisis Detallado de Hallazgos y Mecanismos Defensivos

### 2.1 Inyección de Comandos en el Sistema Operativo (CWE-78)
- **Reglas Evaluadas:** Bandit `B404` (Import subprocess), `B602` (Subprocess shell=True), `B603` (Subprocess sin shell=True).
- **Hallazgo:** Se identificaron llamadas al módulo `subprocess` en `src/jullforensics/adb/runner.py` y `src/jullforensics/adb/device_monitor.py`.
- **Análisis de Impacto y Mitigación:**
  1. **Prohibición de `shell=True`:** Toda invocación a ADB se realiza pasando listas de argumentos discretos (`argv: list[str]`), impidiendo la interpretación de subshells de Bash/sh.
  2. **Validación Previa por Lista Blanca (`AdbAllowlist`):**
     - Cada comando pasa por una matriz canónica de validación sintáctica antes de su despacho.
     - Se prohíben explícitamente y se rechazan con excepción `DisallowedAdbCommandError` metacaracteres de inyección: `;`, `|`, `&`, `$`, `` ` ``, `>`, `<`, `\n`, `\r`.
     - Solo se autorizan subcomandos forenses de solo lectura (`devices`, `getprop`, `pm list`, `dumpsys`, `content query`, `screencap`, `pull`, `bugreportz`).
  3. **Conclusión:** Riesgo residual: **Nulo / Mitigado**.

### 2.2 Integridad y Criptografía Débil (CWE-327, CWE-328)
- **Reglas Evaluadas:** Bandit `B303` (MD5/SHA1), `B324` (Uso de funciones hash inseguras).
- **Análisis de Impacto y Mitigación:**
  - JullForensics implementa exclusivamente **SHA-256** y **SHA-512** (FIPS 180-4) para el sellado de evidencias digitales y sumas de verificación.
  - Para sellado de manifiestos y cadena de custodia se emplea **HMAC-SHA256** derivado mediante **scrypt** (RFC 7914, $N=2^{14}, r=8, p=1$).
  - Las firmas asimétricas se generan mediante **Ed25519 (RFC 8032)** a través de la biblioteca `cryptography` auditada formalmente.
  - Se prohíbe el uso de algoritmos obsoletos (MD5, SHA-1, DES).
  - **Conclusión:** Cumplimiento total de requerimientos criptográficos forenses.

### 2.3 Permisos Inseguros en Sistema de Archivos (CWE-732)
- **Reglas Evaluadas:** Bandit `B103` (Chmod permisivo).
- **Análisis de Impacto y Mitigación:**
  - Todo el árbol del caso pericial se crea bajo máscara estricta `0750` (`rwxr-x---`), impidiendo la lectura por parte de usuarios sin privilegios en la estación Kali Linux.
  - Al completar la adquisición de cada artefacto y al sellar el contenedor TAR, los archivos se marcan inmediatamente con permisos de solo lectura `0440` (`r--r-----`).
  - **Conclusión:** Resistencia contra manipulación inadvertida o accesos concurrentes no autorizados en el sistema de archivos local.

### 2.4 Control de Denegación de Servicio y Recursos (CWE-400)
- **Reglas Evaluadas:** Timeouts de ejecución en subprocesos.
- **Análisis de Impacto y Mitigación:**
  - Todas las llamadas al motor ADB imponen un parámetro `timeout` finito configurable (por defecto 30 segundos; ampliado para volcados pesados o `bugreportz`).
  - Las operaciones de cálculo de hash procesan flujos binarios en bloques de memoria (*chunks*) de 64 KB en lugar de cargar archivos completos en memoria principal, protegiendo contra agotamiento de RAM (*OOM DoS*).

---

## 3. Conformidad con Estándares Internacionales de Seguridad

### NIST Secure Software Development Framework (SSDF v1.1 - SP 800-218)
- **PO.3 (Definir criterios de seguridad del software):** Verificación continua mediante suite de 100 pruebas y cobertura > 87%.
- **PS.1 (Proteger el código fuente):** Repositorio Git firmado, inmutabilidad de commits y ramas protegidas.
- **PW.5 (Crear código seguro):** Cero llamadas dinámicas `eval()`, `exec()`, `pickle.loads()` o `os.system()`.
- **PW.8 (Configurar dependencias de terceros):** CycloneDX SBOM publicado en `docs/seguridad/sbom-v0.1.0.json`.

### OWASP Application Security Verification Standard (ASVS 4.0.3)
- **V1 (Arquitectura):** Separación de capas estricta (Dominio, Almacenamiento, Orquestación, UI, Integridad).
- **V5 (Validación y codificación):** Tipado estático total con Pydantic V2 y Mypy en modo estricto.
- **V6 (Criptografía):** Almacenamiento seguro, firmas Ed25519 y hash en streaming.
- **V8 (Gestión de errores y registros):** Trazabilidad completa sin fuga de secretos o datos sensibles en logs.

---

## 4. Certificación Final del Auditor de Seguridad

> **CERTIFICACIÓN:** El código fuente y arquitectura de **JullForensics v0.1.0** han superado con éxito las pruebas estáticas de seguridad (SAST), no presentando vulnerabilidades conocidas que comprometan la confidencialidad, integridad o disponibilidad de la estación de trabajo ni de las evidencias digitales adquiridas.

---
*Fin del Informe de Auditoría SAST — JullForensics v0.1.0.*
