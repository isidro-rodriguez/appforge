"""Construye AppForge: binario de PyInstaller con su configuración y sus entradas.

Deja en ``dist/``:

- ``appforge/``: el binario (``--onefile``), ``config.toml`` y ``entries/``, lista
  para copiar a ``/opt/appforge``.
- ``appforge-<versión>-linux-<arquitectura>.tar.gz``: esa carpeta empaquetada,
  con los ficheros a nombre de ``root`` y sin escritura para grupo ni otros.
- ``SHA256SUMS``: la suma del ``.tar.gz``.

Los intermedios van a ``build/``.

Uso:
    poe build
    uv run python scripts/build.py
"""

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
DIST = ROOT / "dist"
OUT = DIST / "appforge"


def _version() -> str:
    """Versión de ``pyproject.toml``."""
    with (ROOT / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)["project"]["version"]


def build_binary() -> Path:
    """Ejecuta PyInstaller.

    Returns:
        Ruta del binario.

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
    return BUILD / "bin" / "appforge"


def assemble(binary: Path) -> Path:
    """Monta ``dist/appforge/``: binario, ``config.toml`` y ``entries/``.

    Args:
        binary: Binario de PyInstaller.

    Returns:
        La carpeta montada.
    """
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    shutil.copy2(binary, OUT / "appforge")
    shutil.copy2(ROOT / "config.toml", OUT / "config.toml")
    shutil.copytree(ROOT / "entries", OUT / "entries")
    # AppForge rechaza entradas escribibles por grupo u otros.
    for p in [OUT, *OUT.rglob("*")]:
        p.chmod(p.stat().st_mode & ~0o022)
    (OUT / "appforge").chmod(0o755)
    return OUT


def _as_root(info: tarfile.TarInfo) -> tarfile.TarInfo:
    """Ficheros de ``root``: extraídos con ``sudo`` quedan a su nombre."""
    info.uid = info.gid = 0
    info.uname = info.gname = "root"
    return info


def archive(folder: Path) -> Path:
    """Empaqueta ``folder`` en ``dist/`` y escribe ``SHA256SUMS``.

    Args:
        folder: Carpeta ``dist/appforge/``.

    Returns:
        Ruta del ``.tar.gz``.
    """
    name = f"appforge-{_version()}-linux-{platform.machine()}.tar.gz"
    tar_path = DIST / name
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(folder, arcname="appforge", filter=_as_root)
    digest = hashlib.sha256(tar_path.read_bytes()).hexdigest()
    (DIST / "SHA256SUMS").write_text(f"{digest}  {name}\n", encoding="utf-8")
    return tar_path


def main() -> None:
    """Construye el binario, la carpeta y el ``.tar.gz``."""
    folder = assemble(build_binary())
    print(f"Carpeta: {folder}")
    print(f"Paquete: {archive(folder)}")


if __name__ == "__main__":
    main()
