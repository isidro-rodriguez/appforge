"""Modelo y validación de entradas (un fichero TOML por opción del menú).

Cargar una entrada nunca lanza excepción: los fallos se acumulan en
``Entry.problems`` para que el menú pueda mostrarla marcada como inválida.
"""

import os
import re
import stat
import string
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

STEP_KINDS = ("run", "template", "copy", "script")
FILE_KINDS = ("template", "copy", "script")
TOP_KEYS = {
    "name",
    "description",
    "category",
    "requires_root",
    "param",
    "check",
    "step",
    "remove",
}
PARAM_KEYS = {"name", "prompt", "default", "secret"}
STEP_KEYS = {"title", "dest", "mode", *STEP_KINDS}
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MODE = re.compile(r"0?[0-7]{3,4}")
# Nombres que romperían el entorno de los comandos si un parámetro los pisara.
RESERVED = {
    "PATH",
    "HOME",
    "USER",
    "SHELL",
    "IFS",
    "PWD",
    "LANG",
    "TERM",
    "LD_PRELOAD",
    "LD_LIBRARY_PATH",
    "BASH_ENV",
    "ENV",
}
RESERVED_PREFIX = "APPFORGE_"


@dataclass(frozen=True)
class Param:
    """Parámetro que se pide al usuario antes de aplicar una entrada.

    Attributes:
        name: Identificador; llega a los pasos como variable de entorno.
        prompt: Texto de la pregunta.
        default: Valor por defecto, o ``None`` si es obligatorio.
        secret: Si es ``True`` la entrada se oculta y el valor se enmascara.
    """

    name: str
    prompt: str
    default: str | None = None
    secret: bool = False


@dataclass(frozen=True)
class Step:
    """Paso de una entrada.

    Attributes:
        title: Texto que se muestra al ejecutarlo.
        kind: ``run``, ``template``, ``copy`` o ``script`` (``remove`` para el
            paso sintético de :meth:`Engine.remove`).
        value: Comando (``run``) o fichero relativo al subdirectorio.
        dest: Ruta absoluta de destino (``template`` y ``copy``).
        mode: Permisos del destino, o ``None`` para el valor por defecto.
    """

    title: str
    kind: str
    value: str
    dest: str | None = None
    mode: int | None = None


@dataclass
class Entry:
    """Entrada del menú cargada desde ``entries/<id>.toml``.

    Attributes:
        id: Nombre del fichero sin extensión.
        path: Ruta del fichero TOML.
        name: Nombre que se muestra en el menú.
        description: Descripción de una línea.
        category: Categoría para el panel de categorías; vacía si no tiene.
        requires_root: Si los pasos se ejecutan con privilegios.
        params: Parámetros que se piden antes de aplicar.
        check: Comando que indica si ya está aplicada (código 0).
        steps: Pasos en orden.
        remove: Comando para deshacerla.
        problems: Errores de validación; vacía si la entrada es válida.
    """

    id: str
    path: Path
    name: str
    description: str = ""
    category: str = ""
    requires_root: bool = False
    params: list[Param] = field(default_factory=list)
    check: str | None = None
    steps: list[Step] = field(default_factory=list)
    remove: str | None = None
    problems: list[str] = field(default_factory=list)

    @property
    def files_dir(self) -> Path:
        """Subdirectorio con los ficheros adicionales de la entrada."""
        return self.path.parent / self.id

    @property
    def valid(self) -> bool:
        """``True`` si la entrada no tiene problemas de validación."""
        return not self.problems


# --------------------------------------------------------------------------- #
# Seguridad: las entradas ejecutan comandos, así que se tratan como código.
# --------------------------------------------------------------------------- #
def insecure_reason(path: Path) -> str | None:
    """Indica por qué ``path`` no es de fiar para cargar código de él.

    Un fichero es inseguro si pertenece a otro usuario distinto de root o del
    usuario actual, o si es escribible por el grupo o por otros.

    Args:
        path: Fichero o directorio a comprobar.

    Returns:
        El motivo en texto, o ``None`` si es seguro.
    """
    try:
        st = path.stat()
    except OSError as e:
        return f"{path}: {e.strerror}"
    if st.st_uid not in (0, os.getuid()):
        return f"{path}: propietario ajeno (uid {st.st_uid})"
    if st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        return f"{path}: escribible por grupo u otros ({stat.filemode(st.st_mode)})"
    return None


def _check_tree(root: Path) -> list[str]:
    """Problemas de seguridad de ``root`` y todo lo que contiene."""
    out = []
    if reason := insecure_reason(root):
        out.append(reason)
    if root.is_dir():
        for p in sorted(root.rglob("*")):
            if p.is_symlink():
                out.append(f"{p}: enlace simbólico no permitido")
            elif reason := insecure_reason(p):
                out.append(reason)
    return out


# --------------------------------------------------------------------------- #
# Parseo
# --------------------------------------------------------------------------- #
class _Parser:
    """Convierte el TOML de una entrada en objetos, acumulando problemas."""

    def __init__(self, entry: Entry) -> None:
        """Prepara el parseo de ``entry``."""
        self.entry = entry
        self.problems = entry.problems

    def text(
        self, d: dict[str, Any], key: str, where: str, *, required: bool = False
    ) -> str | None:
        """Lee ``d[key]`` si es texto; registra el problema si no."""
        value = d.get(key)
        if value is None:
            if required:
                self.problems.append(f"{where}: falta '{key}'")
            return None
        if not isinstance(value, str):
            self.problems.append(f"{where}: '{key}' debe ser texto")
            return None
        return value

    def flag(self, d: dict[str, Any], key: str, where: str) -> bool:
        """Lee ``d[key]`` como booleano (por defecto ``False``)."""
        value = d.get(key, False)
        if not isinstance(value, bool):
            self.problems.append(f"{where}: '{key}' debe ser true/false")
            return False
        return value

    def unknown(self, d: dict[str, Any], allowed: set[str], where: str) -> None:
        """Registra las claves de ``d`` que no están en ``allowed``."""
        extra = set(d) - allowed
        if extra:
            self.problems.append(
                f"{where}: claves desconocidas: {', '.join(sorted(extra))}"
            )

    def table_list(self, raw: Any, key: str) -> list[dict[str, Any]]:
        """Valida que ``raw`` sea una lista de tablas ``[[key]]``."""
        if raw is None:
            return []
        if not isinstance(raw, list) or not all(isinstance(t, dict) for t in raw):
            self.problems.append(f"'{key}' debe ser [[{key}]]")
            return []
        return raw

    # -- secciones ------------------------------------------------------- #
    def params(self, raw: Any) -> list[Param]:
        """Parsea ``[[param]]``."""
        params: list[Param] = []
        seen: set[str] = set()
        for i, p in enumerate(self.table_list(raw, "param"), 1):
            where = f"param #{i}"
            self.unknown(p, PARAM_KEYS, where)
            name = self.text(p, "name", where, required=True)
            if name is None or not self._valid_name(name, seen, where):
                continue
            seen.add(name)
            default = p.get("default")
            if default is not None and not isinstance(default, (str, int, float, bool)):
                self.problems.append(f"{where}: 'default' debe ser escalar")
                default = None
            params.append(
                Param(
                    name=name,
                    prompt=self.text(p, "prompt", where) or name,
                    default=None if default is None else str(default),
                    secret=self.flag(p, "secret", where),
                )
            )
        return params

    def _valid_name(self, name: str, seen: set[str], where: str) -> bool:
        """Comprueba que el nombre de un parámetro sea usable."""
        if not IDENT.match(name):
            self.problems.append(f"{where}: nombre inválido '{name}'")
        elif name.upper() in RESERVED or name.startswith(RESERVED_PREFIX):
            self.problems.append(f"{where}: nombre reservado '{name}'")
        elif name in seen:
            self.problems.append(f"{where}: nombre duplicado '{name}'")
        else:
            return True
        return False

    def steps(self, raw: Any) -> list[Step]:
        """Parsea ``[[step]]``."""
        if raw is None:
            self.problems.append("la entrada no tiene ningún [[step]]")
            return []
        steps = []
        for i, s in enumerate(self.table_list(raw, "step"), 1):
            step = self._step(s, f"step #{i}")
            if step is not None:
                steps.append(step)
        return steps

    def _step(self, s: dict[str, Any], where: str) -> Step | None:
        """Parsea y valida un único paso."""
        self.unknown(s, STEP_KEYS, where)
        kinds = [k for k in STEP_KINDS if k in s]
        if len(kinds) != 1:
            self.problems.append(
                f"{where}: necesita exactamente uno de {', '.join(STEP_KINDS)}"
            )
            return None
        kind = kinds[0]
        value = self.text(s, kind, where, required=True)
        if value is None:
            return None
        title = self.text(s, "title", where) or f"{kind}: {value}"
        dest = self.text(s, "dest", where)

        if kind in FILE_KINDS and not self._source_ok(value, where):
            return None
        mode = None
        if kind in ("template", "copy"):
            if not self._dest_ok(kind, dest, where):
                return None
            mode = self._mode(s.get("mode"), where)
        elif dest is not None or "mode" in s:
            self.problems.append(f"{where}: 'dest'/'mode' solo valen en template/copy")
        if kind == "template":
            self._check_template(value, where)
        return Step(title=title, kind=kind, value=value, dest=dest, mode=mode)

    def _source_ok(self, value: str, where: str) -> bool:
        """Valida un fichero de origen relativo al subdirectorio."""
        rel = Path(value)
        if rel.is_absolute() or ".." in rel.parts or not value.strip():
            self.problems.append(
                f"{where}: '{value}' debe ser relativo a {self.entry.id}/ y sin '..'"
            )
            return False
        if not (self.entry.files_dir / value).is_file():
            self.problems.append(f"{where}: falta el fichero {self.entry.id}/{value}")
        return True

    def _dest_ok(self, kind: str, dest: str | None, where: str) -> bool:
        """Valida el destino de un paso ``template`` o ``copy``."""
        if dest is None:
            self.problems.append(f"{where}: '{kind}' necesita 'dest'")
            return False
        if not Path(dest).is_absolute():
            self.problems.append(f"{where}: 'dest' debe ser ruta absoluta")
            return False
        return True

    def _mode(self, raw: Any, where: str) -> int | None:
        """Convierte ``mode = "0644"`` a entero."""
        if raw is None:
            return None
        if isinstance(raw, str) and MODE.fullmatch(raw):
            return int(raw, 8)
        self.problems.append(f"{where}: 'mode' debe ser texto octal, p. ej. \"0644\"")
        return None

    def _check_template(self, value: str, where: str) -> None:
        """Comprueba que la plantilla solo use parámetros declarados."""
        src = self.entry.files_dir / value
        if not src.is_file():
            return
        try:
            tpl = string.Template(src.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            self.problems.append(f"{where}: la plantilla no es UTF-8")
            return
        if not tpl.is_valid():
            self.problems.append(
                f"{where}: plantilla con '$' mal formado (usa $$ para un $ literal)"
            )
        missing = set(tpl.get_identifiers()) - {p.name for p in self.entry.params}
        if missing:
            self.problems.append(
                f"{where}: la plantilla usa parámetros inexistentes: "
                f"{', '.join(sorted(missing))}"
            )

    def run_table(self, raw: Any, key: str) -> str | None:
        """Parsea ``[check]`` o ``[remove]`` (una tabla con ``run``)."""
        if raw is None:
            return None
        if not isinstance(raw, dict):
            self.problems.append(f"'{key}' debe ser una tabla [{key}]")
            return None
        self.unknown(raw, {"run"}, f"[{key}]")
        return self.text(raw, "run", f"[{key}]", required=True)


def load_entry(path: Path) -> Entry:
    """Carga y valida una entrada.

    Args:
        path: Ruta a ``entries/<id>.toml``.

    Returns:
        La entrada. Si hay errores quedan en ``problems`` y ``valid`` es
        ``False``.
    """
    entry = Entry(id=path.stem, path=path, name=path.stem)
    if reason := insecure_reason(path):
        entry.problems.append(reason)
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
        entry.problems.append(f"TOML inválido: {e}")
        return entry

    parser = _Parser(entry)
    parser.unknown(data, TOP_KEYS, "entrada")
    entry.name = parser.text(data, "name", "entrada", required=True) or path.stem
    entry.description = parser.text(data, "description", "entrada") or ""
    entry.category = (parser.text(data, "category", "entrada") or "").strip()
    entry.requires_root = parser.flag(data, "requires_root", "entrada")
    entry.params = parser.params(data.get("param"))
    entry.check = parser.run_table(data.get("check"), "check")
    entry.remove = parser.run_table(data.get("remove"), "remove")
    if entry.files_dir.exists():
        entry.problems.extend(_check_tree(entry.files_dir))
    entry.steps = parser.steps(data.get("step"))
    return entry


def load_entries(entries_dir: Path) -> tuple[list[Entry], list[str]]:
    """Carga todas las entradas de un directorio.

    Args:
        entries_dir: Directorio con los ``*.toml``.

    Returns:
        Las entradas ordenadas por nombre y los problemas del propio
        directorio (que también se añaden a cada entrada).
    """
    dir_problems = []
    if reason := insecure_reason(entries_dir):
        dir_problems.append(reason)
    entries = [load_entry(p) for p in sorted(entries_dir.glob("*.toml")) if p.is_file()]
    for e in entries:
        e.problems.extend(dir_problems)
    entries.sort(key=lambda e: e.name.lower())
    return entries, dir_problems
