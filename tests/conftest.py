"""Fixtures compartidas: copia aislada del proyecto y utilidades de entradas."""

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from appforge.config import Config, load_config

ROOT = Path(__file__).resolve().parent.parent

type WriteEntry = Callable[..., Path]


def secure(path: Path) -> None:
    """Quita la escritura de grupo y otros (las entradas inseguras se rechazan)."""
    for p in [path, *path.rglob("*")]:
        p.chmod(p.stat().st_mode & ~0o022)


class Collector:
    """Sink que guarda los eventos del motor."""

    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []

    def __call__(self, kind: str, text: str) -> None:
        self.events.append((kind, text))

    def text(self, kind: str | None = None) -> str:
        return "\n".join(t for k, t in self.events if kind is None or k == kind)


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Copia de las recetas reales (entries/) con un config.toml por defecto."""
    base = tmp_path / "tool"
    base.mkdir()
    # config.toml propio y con los valores por defecto: el del repositorio es
    # configuración del usuario (p. ej. [ui]) y no debe cambiar los tests.
    (base / "config.toml").write_text('entries_dirs = ["entries"]\n', encoding="utf-8")
    shutil.copytree(ROOT / "entries", base / "entries")
    secure(base)
    # Desde el código, config.toml se busca en el directorio de trabajo.
    monkeypatch.chdir(base)
    # La app exige superusuario; los tests corren como usuario normal.
    monkeypatch.setattr("appforge.main.is_root", lambda: True)
    return base


@pytest.fixture
def config(home: Path) -> Config:
    return load_config(home)


@pytest.fixture
def write_entry(config: Config) -> WriteEntry:
    """Devuelve una función que crea ``entries/<name>.toml`` y sus ficheros."""

    def write(name: str, toml: str, files: dict[str, str] | None = None) -> Path:
        path = config.entries_dirs[0] / f"{name}.toml"
        path.write_text(toml, encoding="utf-8")
        if files:
            folder = config.entries_dirs[0] / name
            folder.mkdir(exist_ok=True)
            for filename, content in files.items():
                (folder / filename).write_text(content, encoding="utf-8")
        secure(config.entries_dirs[0])
        return path

    return write


@pytest.fixture
def sink() -> Collector:
    return Collector()
