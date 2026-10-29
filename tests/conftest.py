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
    """Copia del proyecto real (config + entries/ollama) en un directorio temporal."""
    base = tmp_path / "tool"
    base.mkdir()
    shutil.copy(ROOT / "config.toml", base / "config.toml")
    shutil.copytree(ROOT / "entries", base / "entries")
    # El icono lo aporta el usuario; para probar basta un PNG cualquiera.
    (base / "entries" / "ollama" / "ollama.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    secure(base)
    monkeypatch.setenv("APPFORGE_HOME", str(base))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    # Sin sudo real en los tests: el prefijo privilegiado queda vacío.
    monkeypatch.setenv("APPFORGE_SUDO", "")
    return base


@pytest.fixture
def config(home: Path) -> Config:
    return load_config(home)


@pytest.fixture
def write_entry(config: Config) -> WriteEntry:
    """Devuelve una función que crea ``entries/<name>.toml`` y sus ficheros."""

    def write(name: str, toml: str, files: dict[str, str] | None = None) -> Path:
        path = config.entries_dir / f"{name}.toml"
        path.write_text(toml, encoding="utf-8")
        if files:
            folder = config.entries_dir / name
            folder.mkdir(exist_ok=True)
            for filename, content in files.items():
                (folder / filename).write_text(content, encoding="utf-8")
        secure(config.entries_dir)
        return path

    return write


@pytest.fixture
def sink() -> Collector:
    return Collector()
