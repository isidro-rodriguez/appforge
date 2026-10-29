"""Paleta de AppForge, sacada del icono, y temas derivados para Textual y Rich.

Los colores se muestrearon de ``resources/appforge-512.png``. Éxito y error no
aparecen en el icono: son tonos elegidos para contrastar con el fondo.
"""

from rich.theme import Theme as RichTheme
from textual.theme import Theme as TextualTheme

# --- Paleta (muestreada del icono) -------------------------------------------
BACKGROUND = "#14171b"  # fondo exterior
SURFACE = "#1a202b"  # tarjeta del icono
PANEL = "#1d232f"  # tarjeta, zona más clara
CREAM = "#f8f0e5"  # marco y prompt del terminal
SPARK = "#fea31d"  # chispas
ANVIL_LIGHT = "#b2b8c2"  # brillo del yunque
ANVIL = "#546278"  # cuerpo del yunque
ANVIL_DARK = "#37496a"  # sombra del yunque
ANVIL_DEEP = "#222e46"  # base del yunque
# --- Derivados ---------------------------------------------------------------
PRIMARY = "#6a85b0"  # azul del yunque, aclarado para bordes legibles
MUTED = "#8a94a6"  # texto secundario
SUCCESS = "#7cc47f"
ERROR = "#e5604d"

THEME_NAME = "appforge"

TEXTUAL_THEME = TextualTheme(
    name=THEME_NAME,
    primary=PRIMARY,
    secondary=ANVIL,
    accent=SPARK,
    warning=SPARK,
    error=ERROR,
    success=SUCCESS,
    foreground=CREAM,
    background=BACKGROUND,
    surface=SURFACE,
    panel=PANEL,
    dark=True,
    variables={
        "border": PRIMARY,
        "border-blurred": ANVIL_DARK,
        "block-cursor-background": ANVIL_DARK,
        "block-cursor-foreground": CREAM,
        "block-cursor-text-style": "bold",
        "block-cursor-blurred-background": ANVIL_DEEP,
        "block-cursor-blurred-foreground": CREAM,
        "footer-background": BACKGROUND,
        "footer-key-foreground": SPARK,
        "footer-description-foreground": CREAM,
        "input-cursor-background": SPARK,
        "input-selection-background": f"{ANVIL_DARK} 70%",
        "scrollbar": ANVIL_DARK,
        "scrollbar-hover": ANVIL,
        "scrollbar-active": PRIMARY,
    },
)

# Estilos con nombre: la CLI los usa a través de ``RICH_THEME`` y la TUI
# directamente (Textual no admite estilos con nombre en ``Text``).
STYLES = {
    "step": f"bold {SPARK}",
    "ok": f"bold {SUCCESS}",
    "warn": f"bold {SPARK}",
    "error": f"bold {ERROR}",
    "info": MUTED,
    "out": CREAM,
    "title": f"bold {CREAM}",
    "id": SPARK,
    "muted": MUTED,
    "applied": SUCCESS,
    "invalid": ERROR,
    "link": f"underline {PRIMARY}",
}

# Ayuda y errores de la CLI (constantes ``STYLE_*`` de ``typer.rich_utils``).
TYPER_STYLES = {
    "STYLE_OPTION": f"bold {SPARK}",
    "STYLE_SWITCH": f"bold {SPARK}",
    "STYLE_NEGATIVE_OPTION": f"bold {ERROR}",
    "STYLE_NEGATIVE_SWITCH": f"bold {ERROR}",
    "STYLE_TYPES": PRIMARY,
    "STYLE_USAGE": f"bold {SPARK}",
    "STYLE_USAGE_COMMAND": "bold",
    "STYLE_HELPTEXT": MUTED,
    "STYLE_OPTION_DEFAULT": MUTED,
    "STYLE_REQUIRED_SHORT": ERROR,
    "STYLE_REQUIRED_LONG": ERROR,
    "STYLE_OPTIONS_PANEL_BORDER": ANVIL,
    "STYLE_COMMANDS_PANEL_BORDER": ANVIL,
    "STYLE_COMMANDS_TABLE_FIRST_COLUMN": f"bold {SPARK}",
    "STYLE_ERRORS_PANEL_BORDER": ERROR,
    "STYLE_ERRORS_SUGGESTION": MUTED,
    "STYLE_ABORTED": ERROR,
}

RICH_THEME = RichTheme(
    {
        **{f"af.{name}": style for name, style in STYLES.items()},
        # En la terminal del usuario el texto normal usa su color de primer plano:
        # el crema solo tiene sentido sobre el fondo oscuro de la TUI.
        "af.out": "none",
        "af.title": "bold",
    }
)
