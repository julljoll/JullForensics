# Política de Seguridad — JullForensics

## Compromiso de Seguridad

JullForensics es una herramienta forense diseñada para su uso en investigaciones judiciales, policiales y corporativas de alta criticidad. La integridad de la evidencia, la privacidad de los datos bajo custodia y la inalterabilidad de los registros técnicos son prioridades absolutas del proyecto.

## Reporte de Vulnerabilidades

Si descubres una vulnerabilidad o debilidad de seguridad en el código de JullForensics, agradecemos tu reporte responsable:

1. **No abras un issue público** en GitHub.
2. Envía los detalles técnicos a través de la vía de contacto de seguridad del proyecto o del mantenedor.
3. Incluye:
   - Descripción detallada de la vulnerabilidad y vector de ataque (CWE).
   - Pasos para reproducir (PoC).
   - Evaluación del impacto en la evidencia digital o en el sistema operativo anfitrión.
4. Recibirás un acuse de recibo en un plazo no mayor a 48 horas con el plan de remediación.

## Directrices de Desarrollo Seguro Aplicadas

- **Prohibición de `shell=True`**: Ningún comando de sistema o de ADB se ejecuta a través de un intérprete de comandos (`/bin/sh` o `cmd.exe`).
- **Lista blanca estricta (Allowlist)**: Solo los comandos clasificados previamente como seguros para lectura son permitidos. Comandos de instalación, desinstalación, borrado o flasheo están prohibidos a nivel de adaptador.
- **Protección contra Tar-Slip (CWE-22)**: Validación rigurosa de nombres de archivo y miembros del contenedor `.tar` para impedir la escritura fuera del directorio de destino.
- **Principio de Mínimo Privilegio**: La herramienta está concebida para ejecutarse sin privilegios de `root` o `sudo`, utilizando el grupo de sistema `plugdev` y reglas `udev` para acceder al bus USB.
- **Criptografía Robusta**: Uso exclusivo de algoritmos recomendados por NIST/FIPS (SHA-256, SHA-512, HMAC-SHA256, Ed25519 y scrypt). Algoritmos obsoletos como MD5 o SHA-1 se restringen a consulta histórica de compatibilidad y nunca se usan para sellar evidencia nueva.
