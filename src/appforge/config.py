"""Localización del directorio base y lectura de ``config.toml``."""

import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from acodo.utils import get_env, to_path

APP_NAME = "appforge"
CONFIG_FILE = "config.toml"
_CONFIG_KEYS = {"entries_dir", "backups_dir"}


class ConfigError(Exception):
    """Error al localizar o leer ``config.toml``."""


@dataclass(frozen=True)
class Config:
    """Configuración resuelta de la aplicación.

    Attributes:
        base_dir: Directorio donde viven el binario y ``config.toml``.
        entries_dir: Directorio de entradas, ya resuelto a ruta absoluta.
        backups_dir: Destino de las copias de seguridad.
    """

    base_dir: Path
    entries_dir: Path
    backups_dir: Path


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


def default_backups_dir() -> Path:
    """Devuelve ``$XDG_STATE_HOME/appforge/backups`` (o ``~/.local/state/...``).

    Returns:
        Ruta del directorio de copias de seguridad por defecto.
    """
    state = get_env("XDG_STATE_HOME", to_path) or Path.home() / ".local" / "state"
    return state / APP_NAME / "backups"


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
    return Config(base_dir=base, entries_dir=entries, backups_dir=backups)
