# ADR-001: Selección del Stack Tecnológico y Arquitectura de JullForensics

## Estado
Aceptado

## Contexto
Se requiere construir una aplicación forense para **Kali Linux** destinada a la extracción lógica de dispositivos móviles Android. La herramienta debe garantizar la estricta integridad de la prueba digital según las normas **ISO/IEC 27037, 27041 y 27042**, contar con una interfaz gráfica con diseño brutalista accesible (WCAG 2.2 AA) y estar construida íntegramente en **Python**.

## Decisión

1. **Lenguaje Base:** Python 3.11+. Provee soporte nativo para manipulación de streams, biblioteca estándar de criptografía y archivado, y compatibilidad oficial con las versiones modernas de Debian / Kali Linux.
2. **Framework de Interfaz Gráfica:** **PySide6 (Qt 6)** bajo licencia LGPL. Permite un control tipográfico y de diseño absoluto para el estilo brutalista, soporta sombras duras sin degradados (`QGraphicsDropShadowEffect`), renderizado veloz de miniaturas y desacoplamiento de hilos mediante el sistema de Señales y Ranuras (Signals & Slots).
3. **Criptografía e Integridad:**
   - Biblioteca estándar `hashlib` y `hmac` para cálculo en streaming de SHA-256, SHA-512 y HMAC.
   - `cryptography` para firma asimétrica **Ed25519** del manifiesto y cifrado de contenedores para transporte.
   - `scrypt` para derivación de claves seguras a partir de frases de paso.
4. **Almacenamiento y Empaquetado:**
   - Formato estándar **POSIX PAX** para contenedores `.tar` mediante el módulo nativo `tarfile`.
   - Se prescinde de dependencias externas como Java o `abe.jar` para simplificar la cadena de suministro y auditoría.
5. **Comunicación con Dispositivos Móviles:**
   - Binario oficial `adb` de Android provisto en Kali Linux / platform-tools, invocado mediante `subprocess.run` con listas de argumentos sin intérprete de comandos (`shell=False`).
   - Monitor push basado en `adb track-devices -l` para descartar polling innecesario.
6. **Validación de Modelos:** `pydantic` v2 para asegurar la validación estricta en tiempo de ejecución de esquemas de metadatos, evidencias y registros de custodia.

## Consecuencias
- **Positivas:** Reducción drástica de la superficie de ataque, total portabilidad en Kali Linux, ausencia de dependencias pesadas de JVM, auditabilidad completa del código fuente e inalterabilidad comprobable de la evidencia.
- **Riesgos controlados:** PySide6 requiere dependencias de bibliotecas X11/Wayland en Linux, las cuales están presentes en la instalación de escritorio habitual de Kali. En modo headless o verificación rápida, la utilidad `jullforensics-verify` funciona con la biblioteca estándar sin requerir Qt.
