"""Construye el binario de AppForge con PyInstaller ``--onefile``.

Deja en ``dist/appforge/`` el binario, ``config.toml``, ``entries/`` y el icono
(``appforge.png``, para un lanzador de escritorio), listo para copiar a
cualquier sitio. Los intermedios van a ``build/``.

Con ``--archive`` además empaqueta esa carpeta en
``dist/appforge-<versión>-linux-<arquitectura>.tar.gz`` (con su ``.sha256``),
que es lo que publica la CI en cada versión.

Uso:
    poe build
    uv run python scripts/build.py [--archive]
"""

import argparse
import hashlib
import platform
import shutil
import subprocess
import sys
import tarfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
OUT = ROOT / "dist" / "appforge"
ICON = ROOT / "src" / "appforge" / "resources" / "appforge-256.png"


def _secure(path: Path) -> None:
    """Quita la escritura de grupo y otros: AppForge rechaza entradas inseguras."""
    for p in [path, *path.rglob("*")]:
        p.chmod(p.stat().st_mode & ~0o022)


def _version() -> str:
    """Versión de ``pyproject.toml``."""
    with (ROOT / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)["project"]["version"]


def _anonymous(info: tarfile.TarInfo) -> tarfile.TarInfo:
    """Sin usuario ni grupo de quien construye: al extraer, son de quien extrae."""
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    return info


def archive(folder: Path) -> Path:
    """Empaqueta ``folder`` en un ``.tar.gz`` junto a él, con su ``.sha256``.

    Args:
        folder: Carpeta ``dist/appforge/`` ya montada.

    Returns:
        Ruta del ``.tar.gz``.
    """
    name = f"appforge-{_version()}-linux-{platform.machine()}.tar.gz"
    tar_path = folder.parent / name
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(folder, arcname="appforge", filter=_anonymous)
    digest = hashlib.sha256(tar_path.read_bytes()).hexdigest()
    sha_path = tar_path.with_name(f"{name}.sha256")
    sha_path.write_text(f"{digest}  {name}\n", encoding="utf-8")
    return tar_path


def main() -> None:
    """Ejecuta PyInstaller, monta ``dist/appforge/`` y, si se pide, el ``.tar.gz``.

    Raises:
        subprocess.CalledProcessError: Si PyInstaller termina con error.
    """
    parser = argparse.ArgumentParser(description="Construye el binario de AppForge")
    parser.add_argument(
        "--archive", action="store_true", help="crea también el .tar.gz en dist/"
    )
    args = parser.parse_args()
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
    shutil.copy2(ICON, OUT / "appforge.png")
    _secure(OUT)
    print(f"Listo: {OUT}")
    if args.archive:
        print(f"Paquete: {archive(OUT)}")


if __name__ == "__main__":
    main()
