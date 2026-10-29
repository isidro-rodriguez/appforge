"""Construye el binario de AppForge con PyInstaller ``--onefile``.

Deja en ``dist/appforge/`` el binario, ``config.toml`` y ``entries/``, listo
para copiar a cualquier sitio. Los intermedios van a ``build/``.

Uso:
    poe build
    uv run python scripts/build.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
OUT = ROOT / "dist" / "appforge"


def _secure(path: Path) -> None:
    """Quita la escritura de grupo y otros: AppForge rechaza entradas inseguras."""
    for p in [path, *path.rglob("*")]:
        p.chmod(p.stat().st_mode & ~0o022)


def main() -> None:
    """Ejecuta PyInstaller y monta ``dist/appforge/``.

    Raises:
        subprocess.CalledProcessError: Si PyInstaller termina con error.
    """
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onefile",
            "--name",
            "appforge",
            "--clean",
            "--noconfirm",
            "--distpath",
            str(BUILD / "bin"),
            "--workpath",
            str(BUILD / "work"),
            "--specpath",
            str(BUILD),
            # Textual importa sus widgets de forma perezosa.
            "--collect-submodules",
            "textual",
            "--collect-data",
            "textual",
            "--paths",
            str(ROOT / "src"),
            str(ROOT / "src" / "appforge" / "__main__.py"),
        ],
        cwd=ROOT,
        check=True,
    )
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    shutil.copy2(BUILD / "bin" / "appforge", OUT / "appforge")
    shutil.copy2(ROOT / "config.toml", OUT / "config.toml")
    shutil.copytree(ROOT / "entries", OUT / "entries")
    _secure(OUT)
    print(f"Listo: {OUT}")


if __name__ == "__main__":
    main()
