# Modelo de Amenazas (STRIDE) — JullForensics

El presente documento analiza los vectores de amenaza para la herramienta JullForensics bajo la metodología **STRIDE** de Microsoft, enfocado en el ecosistema forense y de respuesta a incidentes en Kali Linux.

---

## 1. Suplantación de Identidad (Spoofing)

- **Amenaza:** Un usuario malintencionado ejecuta la herramienta haciéndose pasar por un examinador o perito acreditado.
- **Mitigación:** 
  - La herramienta exige de forma obligatoria en la creación de cada caso la identificación formal del examinador y la base legal habilitante.
  - El manifiesto final de adquisición es firmado digitalmente mediante clave asimétrica **Ed25519** generada bajo control del examinador.

---

## 2. Manipulación (Tampering)

- **Amenaza:** Modificación deliberada o inadvertida de los artefactos adquiridos, metadatos, marcas de tiempo o archivos de registro (*logs*).
- **Mitigación:**
  - Hashes criptográficos duales obligatorios (**SHA-256** y **SHA-512**) calculados en streaming en memoria antes y durante la persistencia en disco.
  - Registro de auditoría encadenado (*Chained Log*) en formato JSONL: cada entrada incluye el hash de la entrada anterior y un código **HMAC-SHA256** derivado de una clave efímera de caso con `scrypt`.
  - Re-verificación automática del contenedor `.tar` leyendo desde el disco inmediatamente tras su sellado.
  - Protección contra escritura en el sistema de archivos del anfitrión (`chmod 0440`) al concluir la sesión de adquisición.

---

## 3. Repudio (Repudiation)

- **Amenaza:** Un perito o contraparte impugna la autenticidad del procedimiento alegando que la herramienta alteró el dispositivo o que el informe fue fabricado.
- **Mitigación:**
  - Registro cronológico inalterable con marcas de tiempo en UTC (ISO 8601 con microsegundos).
  - Trazabilidad técnica total: se registra la versión exacta del binario de JullForensics, su hash, la versión de Python, la versión del ejecutable `adb` y los parámetros exactos enviados al dispositivo.
  - Utilidad pública de verificación independiente `jullforensics-verify` que recalcula y valida la cadena criptográfica completa sin depender de la UI.

---

## 4. Fuga de Información (Information Disclosure)

- **Amenaza:** Exposición de evidencia privada, datos personales o claves de cifrado en registros temporales o volcados de memoria.
- **Mitigación:**
  - Los logs técnicos (`tool_debug.log`) filtran y enmascaran cualquier contenido sensible de la evidencia (ISO/IEC 27001 control 8.11).
  - Las claves criptográficas en memoria se manejan en búferes `bytearray` que se sobrescriben con ceros al cerrar la sesión.
  - Modo offline forzado: la herramienta no realiza conexiones de red salientes durante el ciclo de adquisición.

---

## 5. Denegación de Servicio (Denial of Service)

- **Amenaza:** Agotamiento del almacenamiento en el host o bloqueo de la aplicación ante desconexiones intempestivas del cable USB o buffers masivos.
- **Mitigación:**
  - Pre-chequeo estricto de capacidad libre en disco antes de iniciar adquisiciones masivas, exigiendo un margen mínimo de seguridad del 10 %.
  - Procesamiento desacoplado en hilos de trabajo independientes (`QThread` / `concurrent.futures`) para mantener la interfaz siempre reactiva.
  - Manejo de excepciones en la tubería de ADB que renombra contenedores incompletos a `.part` / `.INCOMPLETE` preservando los hashes de lo ya recibido.

---

## 6. Elevación de Privilegios (Elevation of Privilege)

- **Amenaza:** Ataques de salto de directorio (*Tar-Slip* / CWE-22) o inyección de comandos en el shell del host (CWE-78) a través de nombres maliciosos presentes en el teléfono analizado.
- **Mitigación:**
  - Prohibición tajante de `shell=True` en cualquier llamada `subprocess`.
  - Sanitizador estricto de rutas (`name_sanitizer.py`) que normaliza las entradas, rechaza componentes relativos (`..`), bytes nulos y caracteres no imprimibles.
  - Ejecución bajo el usuario sin privilegios `antigravity`, delegando la comunicación USB al grupo `plugdev` vía reglas `udev`.
