"""Localización del directorio base y lectura de ``config.toml``."""

import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from appforge.entry import insecure_reason

APP_NAME = "appforge"
CONFIG_FILE = "config.toml"
_CONFIG_KEYS = {"entries_dirs", "ui"}
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
        entries_dirs: Directorios de entradas, en orden y resueltos a rutas
            absolutas. Si un id está en varios, vale el del último.
        ui: Opciones de la TUI.
    """

    base_dir: Path
    entries_dirs: tuple[Path, ...]
    ui: UiConfig = field(default_factory=UiConfig)

    @property
    def logs_dir(self) -> Path:
        """Directorio del registro de ejecuciones: ``<base_dir>/logs``."""
        return self.base_dir / LOGS_DIR


def base_dir() -> Path:
    """Devuelve el directorio donde se busca ``config.toml``.

    El binario empaquetado (``sys.frozen``) usa su propio directorio (p. ej.
    ``/opt/appforge``, aunque se lance desde un enlace); desde el código, el
    directorio de trabajo.

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
    # Decide qué recetas se ejecutan como root: misma exigencia que las entradas.
    if path.is_symlink():
        raise ConfigError(f"{path}: no puede ser un enlace simbólico")
    if reason := insecure_reason(path):
        raise ConfigError(f"{path} no es de fiar: {reason}")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: TOML inválido: {e}") from e

    unknown = set(data) - _CONFIG_KEYS
    if unknown:
        raise ConfigError(f"{path}: claves desconocidas: {', '.join(sorted(unknown))}")
    dirs = _load_entries_dirs(data.get("entries_dirs"), base, path)
    ui = _load_ui(data.get("ui", {}), path)
    return Config(base_dir=base, entries_dirs=dirs, ui=ui)


def _load_entries_dirs(raw: Any, base: Path, path: Path) -> tuple[Path, ...]:
    """Valida ``entries_dirs``: lista no vacía de directorios existentes."""
    if raw is None:
        raise ConfigError(f"{path}: falta 'entries_dirs'")
    if (
        not isinstance(raw, list)
        or not raw
        or not all(isinstance(d, str) and d.strip() for d in raw)
    ):
        raise ConfigError(
            f"{path}: 'entries_dirs' debe ser una lista de rutas, "
            'p. ej. ["appforge-entries", "custom-entries"]'
        )
    dirs: list[Path] = []
    for item in raw:
        folder = (base / Path(item).expanduser()).resolve()
        if not folder.is_dir():
            raise ConfigError(f"El directorio de entradas no existe: {folder}")
        if folder not in dirs:
            dirs.append(folder)
    return tuple(dirs)


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
