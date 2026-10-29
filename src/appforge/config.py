"""Localización del directorio base y lectura de ``config.toml``."""

import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from acodo.utils import get_env, to_path

APP_NAME = "appforge"
CONFIG_FILE = "config.toml"
_CONFIG_KEYS = {"entries_dir", "backups_dir", "ui"}
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
        backups_dir: Destino de las copias de seguridad.
        logs_dir: Destino del registro de ejecuciones.
        ui: Opciones de la TUI.
    """

    base_dir: Path
    entries_dir: Path
    backups_dir: Path
    ui: UiConfig = field(default_factory=UiConfig)
    logs_dir: Path = field(default_factory=lambda: state_dir() / "logs")


def base_dir() -> Path:
    """Devuelve el directorio donde se busca ``config.toml``.

    Orden de prioridad: variable ``APPFORGE_HOME``, directorio del binario
    cuando se ejecuta empaquetado con PyInstaller (``sys.frozen``) y, por
    último, el directorio de trabajo.

    Returns:
        Ruta absoluta del directorio base.
    """
    env = get_env("APPFORGE_HOME", to_path)
    if env is not None:
        return env.resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def state_dir() -> Path:
    """Devuelve ``$XDG_STATE_HOME/appforge`` (o ``~/.local/state/appforge``).

    Returns:
        Directorio de estado de la aplicación (copias y registro).
    """
    state = get_env("XDG_STATE_HOME", to_path) or Path.home() / ".local" / "state"
    return state / APP_NAME


def default_backups_dir() -> Path:
    """Devuelve el directorio de copias de seguridad por defecto.

    Returns:
        ``state_dir() / "backups"``.
    """
    return state_dir() / "backups"


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
    backups = to_path(data.get("backups_dir")) or default_backups_dir()
    ui = _load_ui(data.get("ui", {}), path)
    return Config(base_dir=base, entries_dir=entries, backups_dir=backups, ui=ui)


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
