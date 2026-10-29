"""Localización del directorio base y lectura de ``config.toml``."""

import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from acodo.utils import to_path

APP_NAME = "appforge"
CONFIG_FILE = "config.toml"
_CONFIG_KEYS = {"entries_dir", "ui"}
LOGS_DIR = "logs"
_UI_KEYS = {"search", "categories"}


class ConfigError(Exception):
    """Error al localizar o leer ``config.toml``."""


@dataclass(frozen=True)
class UiConfig:
    """Opciones de la TUI (tabla ``[ui]`` de ``config.toml``).

    Attributes:
        search: Mostrar el buscador.
        categories: Mostrar el panel de categorías.
    """

    search: bool = False
    categories: bool = False


@dataclass(frozen=True)
class Config:
    """Configuración resuelta de la aplicación.

    Attributes:
        base_dir: Directorio donde viven el binario y ``config.toml``.
        entries_dir: Directorio de entradas, ya resuelto a ruta absoluta.
        ui: Opciones de la TUI.
    """

    base_dir: Path
    entries_dir: Path
    ui: UiConfig = field(default_factory=UiConfig)

    @property
    def logs_dir(self) -> Path:
        """Directorio del registro de ejecuciones: ``<base_dir>/logs``."""
        return self.base_dir / LOGS_DIR


def base_dir() -> Path:
    """Devuelve el directorio donde se busca ``config.toml``.

    Empaquetado con PyInstaller (``sys.frozen``) es el directorio del binario;
    desde el código, el directorio de trabajo.

    Returns:
        Ruta absoluta del directorio base.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def load_config(base: Path | None = None) -> Config:
    """Lee y valida ``config.toml``.

    Args:
        base: Directorio que contiene ``config.toml``. Si es ``None`` se usa
            :func:`base_dir`.

    Returns:
        La configuración con las rutas resueltas.

    Raises:
        ConfigError: Si el fichero falta, no es TOML válido, tiene claves
            desconocidas o el directorio de entradas no existe.
    """
    base = base or base_dir()
    path = base / CONFIG_FILE
    if not path.is_file():
        raise ConfigError(f"No existe {path}")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: TOML inválido: {e}") from e

    unknown = set(data) - _CONFIG_KEYS
    if unknown:
        raise ConfigError(f"{path}: claves desconocidas: {', '.join(sorted(unknown))}")
    entries_raw = to_path(data.get("entries_dir"))
    if entries_raw is None:
        raise ConfigError(f"{path}: falta 'entries_dir'")

    entries = (base / entries_raw).resolve()
    if not entries.is_dir():
        raise ConfigError(f"El directorio de entradas no existe: {entries}")
    ui = _load_ui(data.get("ui", {}), path)
    return Config(base_dir=base, entries_dir=entries, ui=ui)


def _load_ui(raw: Any, path: Path) -> UiConfig:
    """Valida la tabla ``[ui]``."""
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: 'ui' debe ser una tabla [ui]")
    unknown = set(raw) - _UI_KEYS
    if unknown:
        raise ConfigError(
            f"{path}: claves desconocidas en [ui]: {', '.join(sorted(unknown))}"
        )
    for key, value in raw.items():
        if not isinstance(value, bool):
            raise ConfigError(f"{path}: [ui].{key} debe ser true/false")
    return UiConfig(**raw)
