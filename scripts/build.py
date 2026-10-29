"""Construye el binario de AppForge y su paquete ``.deb``.

El binario se genera con PyInstaller ``--onefile`` en ``build/bin/``. El paquete
``dist/appforge_<versión>_<arquitectura>.deb`` instala:

======================================  ========================================
``/opt/appforge/appforge``              Binario
``/usr/bin/appforge``                   Enlace al binario
``/etc/appforge/config.toml``           Configuración (conffile)
``/etc/appforge/entries/``              Recetas de ejemplo (conffiles)
``/var/log/appforge/``                  Registro (se borra al purgar)
``/usr/share/man/man1/appforge.1.gz``   Página ``man``
``/usr/share/applications/…desktop``    Lanzador (abre una terminal con sudo)
``/usr/share/icons/hicolor/…``          Iconos
``/usr/share/doc/appforge/``            Licencia y changelog
======================================  ========================================

Todo es de ``root`` (``dpkg-deb --root-owner-group``) y nadie más puede
escribirlo. Junto al ``.deb`` deja ``SHA256SUMS``.

Uso:
    poe build
    uv run python scripts/build.py [--binary-only]
"""

import argparse
import gzip
import hashlib
import platform
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
DIST = ROOT / "dist"
STAGE = BUILD / "deb"
RESOURCES = ROOT / "src" / "appforge" / "resources"
PACKAGING = ROOT / "packaging"
ICON_SIZES = (48, 64, 128, 256, 512)
DEB_ARCH = {"x86_64": "amd64", "aarch64": "arm64"}
MAINTAINER = "isidro-rodriguez <141645287+isidro-rodriguez@users.noreply.github.com>"
HOMEPAGE = "https://github.com/isidro-rodriguez/appforge"


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


def _put(src: Path, dest: Path, mode: int) -> None:
    """Copia ``src`` a ``dest`` (en el árbol del paquete) con ``mode``."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    dest.chmod(mode)


def _gzip(src: bytes, dest: Path) -> None:
    """Escribe ``src`` comprimido (``gzip -9n``, reproducible) en ``dest``."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with (
        dest.open("wb") as raw,
        gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0
        ) as f,
    ):
        f.write(src)
    dest.chmod(0o644)


def _stage_tree(binary: Path, version: str) -> list[str]:
    """Monta el árbol del paquete en ``build/deb``.

    Returns:
        Los conffiles (rutas absolutas bajo ``/etc``).
    """
    shutil.rmtree(STAGE, ignore_errors=True)
    _put(binary, STAGE / "opt/appforge/appforge", 0o755)
    (STAGE / "usr/bin").mkdir(parents=True)
    (STAGE / "usr/bin/appforge").symlink_to("/opt/appforge/appforge")

    etc = STAGE / "etc/appforge"
    _put(ROOT / "config.toml", etc / "config.toml", 0o644)
    for src in sorted((ROOT / "entries").rglob("*")):
        if src.is_file():
            executable = src.stat().st_mode & 0o100
            _put(
                src,
                etc / "entries" / src.relative_to(ROOT / "entries"),
                0o755 if executable else 0o644,
            )
    (STAGE / "var/log/appforge").mkdir(parents=True)

    page = (PACKAGING / "appforge.1").read_text(encoding="utf-8")
    page = page.replace("@VERSION@", version)
    page = page.replace("@DATE@", time.strftime("%Y-%m-%d"))
    _gzip(page.encode(), STAGE / "usr/share/man/man1/appforge.1.gz")
    _put(
        PACKAGING / "appforge.desktop",
        STAGE / "usr/share/applications/appforge.desktop",
        0o644,
    )
    for size in ICON_SIZES:
        _put(
            RESOURCES / f"appforge-{size}.png",
            STAGE / f"usr/share/icons/hicolor/{size}x{size}/apps/appforge.png",
            0o644,
        )
    doc = STAGE / "usr/share/doc/appforge"
    _put(ROOT / "LICENSE", doc / "copyright", 0o644)
    _gzip((ROOT / "CHANGELOG.md").read_bytes(), doc / "changelog.gz")

    for d in [STAGE, *STAGE.rglob("*")]:
        if d.is_dir() and not d.is_symlink():
            d.chmod(0o755)
    return sorted(
        "/" + str(p.relative_to(STAGE)) for p in etc.rglob("*") if p.is_file()
    )


def _control(version: str, arch: str) -> str:
    """Contenido de ``DEBIAN/control``."""
    size_kib = (
        sum(
            p.stat().st_size
            for p in STAGE.rglob("*")
            if p.is_file() and not p.is_symlink()
        )
        // 1024
    )
    return (
        "Package: appforge\n"
        f"Version: {version}\n"
        f"Architecture: {arch}\n"
        f"Maintainer: {MAINTAINER}\n"
        f"Installed-Size: {size_kib}\n"
        "Depends: libc6 (>= 2.41), bash, coreutils, sudo\n"
        "Section: admin\n"
        "Priority: optional\n"
        f"Homepage: {HOMEPAGE}\n"
        "Description: recetas de configuración repetibles desde un menú de consola\n"
        " AppForge muestra un catálogo de recetas (ficheros TOML) que instalan y\n"
        " configuran software en Debian, con dry-run, comprobación y desinstalación.\n"
        " Las recetas están en /etc/appforge/entries; se ejecuta con sudo appforge.\n"
    )


def build_deb(binary: Path) -> Path:
    """Monta y empaqueta el ``.deb`` con ``dpkg-deb``.

    Args:
        binary: Binario de PyInstaller.

    Returns:
        Ruta del ``.deb``.

    Raises:
        SystemExit: Si no hay ``dpkg-deb``.
    """
    if shutil.which("dpkg-deb") is None:
        raise SystemExit("Falta dpkg-deb: construye el paquete en Debian.")
    version = _version()
    arch = DEB_ARCH.get(platform.machine(), platform.machine())
    conffiles = _stage_tree(binary, version)
    debian = STAGE / "DEBIAN"
    debian.mkdir(mode=0o755)
    (debian / "control").write_text(_control(version, arch), encoding="utf-8")
    (debian / "conffiles").write_text("\n".join(conffiles) + "\n", encoding="utf-8")
    _put(PACKAGING / "postrm", debian / "postrm", 0o755)
    for f in ("control", "conffiles"):
        (debian / f).chmod(0o644)

    DIST.mkdir(exist_ok=True)
    deb = DIST / f"appforge_{version}_{arch}.deb"
    subprocess.run(
        ["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(STAGE), str(deb)],
        check=True,
    )
    digest = hashlib.sha256(deb.read_bytes()).hexdigest()
    (DIST / "SHA256SUMS").write_text(f"{digest}  {deb.name}\n", encoding="utf-8")
    return deb


def main() -> None:
    """Construye el binario y, salvo ``--binary-only``, el ``.deb``."""
    parser = argparse.ArgumentParser(description="Construye AppForge")
    parser.add_argument(
        "--binary-only", action="store_true", help="solo el binario (build/bin/)"
    )
    args = parser.parse_args()
    binary = build_binary()
    print(f"Binario: {binary}")
    if not args.binary_only:
        print(f"Paquete: {build_deb(binary)}")


if __name__ == "__main__":
    main()
