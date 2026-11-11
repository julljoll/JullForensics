"""Tokens de diseño brutalista funcional (WCAG 2.2 AA / ISO 9241)."""

from __future__ import annotations

# Paleta brutalista de alto contraste
COLOR_BG = "#F4F4F0"
COLOR_SURFACE = "#FFFFFF"
COLOR_INK = "#0A0A0A"
COLOR_BORDER = "#0A0A0A"

COLOR_ACCENT = "#FFE600"  # Amarillo brutalista / advertencia
COLOR_SUCCESS = "#00873E"  # Verde forense verificado (WCAG AA >= 4.5:1)
COLOR_DANGER = "#D7261E"  # Rojo error / comando bloqueado
COLOR_WARNING = "#E65100"  # Naranja no autorizado
COLOR_MUTED = "#E0E0E0"  # Gris sutil para bordes secundarios
COLOR_DARK_SURFACE = "#1A1A1A"  # Superficie oscura para consola/logs

# Tipografía
FONT_FAMILY = "ui-monospace, 'JetBrains Mono', 'Fira Code', 'DejaVu Sans Mono', monospace"
FONT_SIZE_XS = "11px"
FONT_SIZE_SM = "12px"
FONT_SIZE_MD = "13px"
FONT_SIZE_LG = "16px"
FONT_SIZE_XL = "20px"

# Geometría y bordes
BORDER_WIDTH = "3px"
BORDER_THIN = "1px"
BORDER_STYLE = f"{BORDER_WIDTH} solid {COLOR_BORDER}"
BORDER_THIN_STYLE = f"{BORDER_THIN} solid {COLOR_BORDER}"

# Sombras duras (Hard Shadows sin difuminado)
HARD_SHADOW_OFFSET = "4px 4px 0px #0A0A0A"
HARD_SHADOW_SM_OFFSET = "2px 2px 0px #0A0A0A"
