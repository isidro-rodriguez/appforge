"""Actualización de AppForge instalado (``appforge update``).

El paquete trae un manifiesto (``.manifest.json``) con la suma SHA-256 de cada
fichero que instala. Comparando el manifiesto instalado, el del paquete nuevo y
lo que hay en disco se sabe qué cambió el usuario:

=================================  =============================================
Situación del fichero               Qué hace la actualización
=================================  =============================================
Sin tocar por el usuario            Se sustituye por el del paquete nuevo
Modificado por el usuario           Se conserva; el nuevo queda en ``<fichero>.new``
                                    (si el paquete también lo cambió)
Borrado por el usuario              No se vuelve a crear
Nuevo en el paquete                 Se añade
Quitado del paquete                 Se borra si no se tocó; si se tocó, se conserva
Fuera del paquete (tus recetas)     No se toca
=================================  =============================================

El binario se sustituye siempre. ``custom-entries/`` y ``logs/`` no se tocan.
"""

import hashlib
import json
import platform
import re
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

REPO = "isidro-rodriguez/appforge"
MANIFEST = ".manifest.json"
BINARY = "appforge"
CUSTOM_DIR = "custom-entries"
NEW_SUFFIX = ".new"
TIMEOUT = 60


class UpdateError(Exception):
    """Fallo al obtener, verificar o aplicar una actualización."""


@dataclass
class Plan:
    """Qué hará una actualización con cada fichero del paquete.

    Attributes:
        version: Versión del paquete nuevo.
        replace: Ficheros sin tocar que se sustituyen.
        add: Ficheros nuevos que se añaden.
        keep: Ficheros modificados que se conservan; el nuevo va a ``.new``.
        remove: Ficheros que el paquete ya no trae y no se tocaron: se borran.
        orphan: Ficheros que el paquete ya no trae pero se modificaron: se
            conservan.
        skip: Ficheros que el usuario borró: no se vuelven a crear.
    """

    version: str
    replace: list[str] = field(default_factory=list)
    add: list[str] = field(default_factory=list)
    keep: list[str] = field(default_factory=list)
    remove: list[str] = field(default_factory=list)
    orphan: list[str] = field(default_factory=list)
    skip: list[str] = field(default_factory=list)


def sha256(path: Path) -> str:
    """Suma SHA-256 de un fichero.

    Args:
        path: Fichero.

    Returns:
        La suma en hexadecimal.
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_manifest(base: Path) -> dict[str, str]:
    """Ficheros y sumas del manifiesto de ``base`` (vacío si no hay).

    Args:
        base: Carpeta de AppForge.

    Returns:
        ``{ruta relativa: sha256}``.
    """
    path = base / MANIFEST
    if not path.is_file():
        return {}
    try:
        files = json.loads(path.read_text(encoding="utf-8"))["files"]
    except (ValueError, KeyError, TypeError) as e:
        raise UpdateError(f"{path}: manifiesto ilegible: {e}") from e
    return {str(k): str(v) for k, v in files.items()}


def manifest_version(base: Path) -> str:
    """Versión del manifiesto de ``base``.

    Args:
        base: Carpeta de un paquete extraído.

    Returns:
        La versión.

    Raises:
        UpdateError: Si no hay manifiesto o no tiene versión.
    """
    try:
        data = json.loads((base / MANIFEST).read_text(encoding="utf-8"))
        return str(data["version"])
    except (OSError, ValueError, KeyError) as e:
        raise UpdateError("el paquete no tiene manifiesto: ¿es de AppForge?") from e


def plan_update(installed: Path, staged: Path) -> Plan:
    """Decide qué hacer con cada fichero.

    Args:
        installed: Carpeta de AppForge instalada.
        staged: Carpeta del paquete nuevo, ya extraída.

    Returns:
        El plan.
    """
    old = read_manifest(installed)
    new = read_manifest(staged)
    plan = Plan(version=manifest_version(staged))
    for rel, new_sum in sorted(new.items()):
        if rel == BINARY:
            continue
        current = installed / rel
        old_sum = old.get(rel)
        if not current.is_file():
            (plan.skip if old_sum is not None else plan.add).append(rel)
            continue
        cur_sum = sha256(current)
        if cur_sum == new_sum:
            continue
        if old_sum is not None and cur_sum == old_sum:
            plan.replace.append(rel)
        elif old_sum != new_sum:
            plan.keep.append(rel)  # tuyo y el paquete también lo cambió
    for rel, old_sum in sorted(old.items()):
        current = installed / rel
        if rel in new or rel == BINARY or not current.is_file():
            continue
        (plan.remove if sha256(current) == old_sum else plan.orphan).append(rel)
    return plan


def _install(src: Path, dest: Path) -> None:
    """Coloca ``src`` en ``dest`` de forma atómica (mismo sistema de ficheros)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".{dest.name}.tmp")
    shutil.copy2(src, tmp)
    tmp.chmod(src.stat().st_mode & 0o755)
    tmp.replace(dest)


def apply_update(installed: Path, staged: Path, plan: Plan) -> None:
    """Aplica ``plan``: binario, ficheros del paquete y manifiesto.

    Args:
        installed: Carpeta de AppForge instalada.
        staged: Carpeta del paquete nuevo, ya extraída.
        plan: Resultado de :func:`plan_update`.
    """
    for rel in [*plan.replace, *plan.add]:
        _install(staged / rel, installed / rel)
    for rel in plan.keep:
        _install(staged / rel, installed / f"{rel}{NEW_SUFFIX}")
    for rel in plan.remove:
        (installed / rel).unlink(missing_ok=True)
        _prune_empty(installed / rel, installed)
    (installed / CUSTOM_DIR).mkdir(exist_ok=True)
    _install(staged / MANIFEST, installed / MANIFEST)
    _install(
        staged / BINARY, installed / BINARY
    )  # el último: si algo falla, sigue el viejo


def _prune_empty(path: Path, stop: Path) -> None:
    """Borra los directorios vacíos de ``path`` hacia arriba, sin pasar de ``stop``."""
    for parent in path.parents:
        if parent == stop or not parent.is_relative_to(stop):
            return
        try:
            parent.rmdir()
        except OSError:
            return


# --------------------------------------------------------------------------- #
# Obtener el paquete
# --------------------------------------------------------------------------- #
def asset_name(version: str) -> str:
    """Nombre del paquete de una versión para esta arquitectura.

    Args:
        version: Versión, sin ``v``.

    Returns:
        P. ej. ``appforge-0.9.0-linux-x86_64.tar.gz``.
    """
    return f"appforge-{version}-linux-{platform.machine()}.tar.gz"


def _get(url: str, dest: Path | None = None) -> bytes:
    """Descarga ``url`` (a memoria o a ``dest``)."""
    req = urllib.request.Request(url, headers={"User-Agent": "appforge-update"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            if dest is None:
                return r.read()
            with dest.open("wb") as f:
                shutil.copyfileobj(r, f)
            return b""
    except (urllib.error.URLError, OSError) as e:
        raise UpdateError(f"No se pudo descargar {url}: {e}") from e


def latest_release() -> tuple[str, dict[str, str]]:
    """Última Release publicada en GitHub.

    Returns:
        ``(versión sin v, {nombre de fichero: URL de descarga})``.

    Raises:
        UpdateError: Si no se puede consultar.
    """
    url = f"https://api.github.com/repos/{REPO}/releases/latest"
    try:
        data = json.loads(_get(url))
        tag = str(data["tag_name"])
        assets = {a["name"]: a["browser_download_url"] for a in data["assets"]}
    except (ValueError, KeyError, TypeError) as e:
        raise UpdateError(f"Respuesta inesperada de {url}: {e}") from e
    return tag.removeprefix("v"), assets


def check_sum(package: Path, sums: Path) -> None:
    """Comprueba ``package`` contra su línea en ``SHA256SUMS``.

    Args:
        package: El ``.tar.gz``.
        sums: Fichero ``SHA256SUMS``.

    Raises:
        UpdateError: Si no está en la lista o la suma no coincide.
    """
    for line in sums.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == package.name:
            if parts[0].lower() != sha256(package):
                raise UpdateError(f"{package.name}: la suma SHA-256 no coincide")
            return
    raise UpdateError(f"{sums.name} no incluye {package.name}")


def download(version: str, assets: dict[str, str], dest: Path) -> Path:
    """Descarga el paquete de ``version`` y su ``SHA256SUMS`` y lo verifica.

    Args:
        version: Versión, sin ``v``.
        assets: Ficheros de la Release (de :func:`latest_release`).
        dest: Directorio donde dejarlos.

    Returns:
        Ruta del ``.tar.gz`` verificado.

    Raises:
        UpdateError: Si falta algo o la suma no coincide.
    """
    name = asset_name(version)
    if name not in assets or "SHA256SUMS" not in assets:
        raise UpdateError(f"La Release {version} no publica {name} y SHA256SUMS")
    package, sums = dest / name, dest / "SHA256SUMS"
    _get(assets["SHA256SUMS"], sums)
    _get(assets[name], package)
    check_sum(package, sums)
    return package


def extract(package: Path, workdir: Path) -> Path:
    """Extrae el paquete de forma segura.

    Args:
        package: El ``.tar.gz``.
        workdir: Directorio vacío donde extraerlo.

    Returns:
        La carpeta ``appforge/`` extraída.

    Raises:
        UpdateError: Si no es un paquete de AppForge.
    """
    try:
        with tarfile.open(package, "r:gz") as tar:
            names = tar.getnames()
            if not names or any(
                n != "appforge" and not n.startswith("appforge/") for n in names
            ):
                raise UpdateError(f"{package.name} no es un paquete de AppForge")
            tar.extractall(workdir, filter="data")
    except (tarfile.TarError, OSError) as e:
        raise UpdateError(f"No se pudo extraer {package.name}: {e}") from e
    staged = workdir / "appforge"
    if not (staged / BINARY).is_file():
        raise UpdateError(f"{package.name} no trae el programa")
    manifest_version(staged)
    return staged


def staging_dir(installed: Path) -> Path:
    """Directorio temporal junto a la instalación (mismo sistema de ficheros).

    Args:
        installed: Carpeta de AppForge instalada.

    Returns:
        Un directorio nuevo y vacío.
    """
    return Path(tempfile.mkdtemp(prefix=".appforge-update-", dir=installed.parent))


VERSION_RE = re.compile(r"^\d+(\.\d+)*$")


def version_key(version: str) -> tuple[int, ...]:
    """Clave para comparar versiones ``X.Y.Z``.

    Args:
        version: Versión.

    Returns:
        Tupla de enteros (vacía si no es una versión numérica).

    Examples:
        >>> version_key("0.10.0") > version_key("0.9.1")
        True
    """
    if not VERSION_RE.match(version):
        return ()
    return tuple(int(p) for p in version.split("."))
