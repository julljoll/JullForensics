# JullForensics 📱⚖️

> **Herramienta forense de extracción lógica de dispositivos Android para Kali Linux.**
> Desarrollada 100 % en Python con interfaz gráfica de diseño brutalista (PySide6), alineada rigurosamente con los estándares internacionales de informática forense **ISO/IEC 27037, 27041, 27042, 27043, 27050 y 17025**, y las mejores prácticas de ciberseguridad (**ISO/IEC 27001/27002, NIST SSDF y OWASP ASVS**).

---

## ⚡ Características Principales

- **Detección y Monitoreo en Tiempo Real**: Notificación reactiva inmediata (<1 s) de conexión/desconexión USB y estados de autorización mediante `adb track-devices -l`.
- **Capturas de Pantalla Forenses**: Adquisición directa a memoria RAM (sin shell ni archivos temporales en el móvil), cálculo de hashes SHA-256 y SHA-512 antes de persistir a disco, metadatos contextuales JSON y alerta de `FLAG_SECURE`.
- **Contenedor Forense JF-TAR**: Extracción lógica en streaming empaquetada en una sola pasada en formato `.tar` (POSIX PAX) sin dependencias de Java.
- **Integridad y Cadena de Custodia Inalterable (Tamper-Evident)**:
  - Registro cronológico continuo en formato JSONL encadenado por HMAC-SHA256 derivado con `scrypt`.
  - Firma criptográfica del manifiesto y del estado con **Ed25519**.
  - Hashes en streaming calculados tanto a nivel de artefacto individual como del archivo contenedor completo.
  - *Sidecars* externos (`.tar.sha256`, `.tar.sha512`, `.tar.sig`, `.tar.log.jsonl`) para verificación independiente inmediata con `sha256sum -c`.
- **Verificación Cero-Confianza**: Utilidad CLI independiente `jullforensics-verify` que permite a contrapartes, peritos o tribunales comprobar la autenticidad sin ejecutar la interfaz gráfica.
- **Interfaz Brutalista Optimizada**: Estilo visual funcional, crudo, de alto contraste (certificado WCAG 2.2 AA) y operable 100 % por teclado según ISO 9241-110.

---

## 🛠️ Instalación en Kali Linux

### Requisitos previos
```bash
sudo apt update
sudo apt install -y adb python3-venv python3-dev
```

### Reglas udev (Mínimo privilegio sin root)
```bash
sudo cp packaging/51-android-forensics.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
sudo usermod -aG plugdev "$USER"
```

### Instalación en entorno virtual
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## 🚀 Uso Rápido

### Lanzar la interfaz gráfica
```bash
jullforensics
```

### Verificación independiente de un caso o contenedor `.tar`
```bash
jullforensics-verify /ruta/a/caso_o_contenedor.tar
```

---

## 📜 Marco Normativo

- **ISO/IEC 27037:2012**: Directrices para la identificación, recolección, adquisición y preservación de evidencia digital.
- **ISO/IEC 27041:2015**: Seguridad en métodos de investigación y validación de herramientas.
- **ISO/IEC 27042:2015**: Análisis e interpretación de evidencia digital.
- **RFC 3227**: Orden de volatilidad en adquisición forense.
- **NIST SP 800-101 Rev.1**: Guía de informática forense en dispositivos móviles.

Para consultar la especificación completa del sistema y el mapa de desarrollo, véase [agente.md](agente.md) y [plan.md](plan.md).
