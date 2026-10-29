"""Validación exhaustiva de un directorio de entradas (``appforge validate``).

Además de los problemas que detecta :func:`appforge.entry.load_entry` (que
impiden aplicar una entrada), revisa lo que solo se ve mirando el conjunto:

- **Errores**: sintaxis de bash en ``run``, ``[check]``, ``[remove]`` y
  scripts; referencias ``$APPFORGE_ENTRY_DIR/<fichero>`` a ficheros que no
  existen en el subdirectorio de la entrada.
- **Avisos**: ficheros del subdirectorio que nada usa, parámetros que ningún
  comando ni plantilla usa, entradas sin ``description``, ``[check]`` o
  ``[remove]``, nombres repetidos y subdirectorios sin su ``.toml``.

Nunca ejecuta las entradas: solo lee ficheros y llama a ``bash -n``.
"""

import re
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from appforge.entry import FILE_KINDS, Entry, load_entries

ENTRY_DIR_REF = re.compile(r"\$\{?APPFORGE_ENTRY_DIR\}?/([A-Za-z0-9._\-/]+)")


@dataclass
class Report:
    """Resultado de validar una entrada.

    Attributes:
        entry: La entrada validada.
        errors: Problemas que impiden aplicarla o que la harían fallar.
        warnings: Problemas que no impiden aplicarla.
    """

    entry: Entry
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class Validation:
    """Resultado de validar un directorio de entradas.

    Attributes:
        reports: Un informe por entrada, ordenados por nombre.
        errors: Errores del propio directorio.
        warnings: Avisos del propio directorio.
    """

    reports: list[Report]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        """Número total de errores."""
        return len(self.errors) + sum(len(r.errors) for r in self.reports)

    @property
    def warning_count(self) -> int:
        """Número total de avisos."""
        return len(self.warnings) + sum(len(r.warnings) for r in self.reports)


def _read_text(path: Path) -> str:
    """Contenido de ``path`` si es texto UTF-8; vacío si no."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def bash_syntax_error(code: str | None = None, path: Path | None = None) -> str | None:
    """Comprueba la sintaxis de bash sin ejecutar nada (``bash -n``).

    Args:
        code: Comando en línea.
        path: Script en disco (si no se da ``code``).

    Returns:
        La primera línea del error, o ``None`` si es correcto o no hay bash.
    """
    bash = shutil.which("bash")
    if bash is None:
        return None
    args = [bash, "-n", "-c", code] if code is not None else [bash, "-n", str(path)]
    r = subprocess.run(args, capture_output=True, text=True, check=False)
    if r.returncode == 0:
        return None
    lines = r.stderr.strip().splitlines()
    return lines[0] if lines else f"bash -n terminó con código {r.returncode}"


def _commands(entry: Entry) -> list[tuple[str, str]]:
    """``(dónde, comando)`` de cada ``run``, ``[check]`` y ``[remove]``."""
    out = [
        (f"step #{i}", s.value) for i, s in enumerate(entry.steps, 1) if s.kind == "run"
    ]
    if entry.check:
        out.append(("[check]", entry.check))
    if entry.remove:
        out.append(("[remove]", entry.remove))
    return out


def _files(entry: Entry) -> list[str]:
    """Ficheros del subdirectorio como rutas relativas POSIX."""
    if not entry.files_dir.is_dir():
        return []
    return sorted(
        p.relative_to(entry.files_dir).as_posix()
        for p in entry.files_dir.rglob("*")
        if p.is_file()
    )


def _check_syntax(entry: Entry, report: Report) -> None:
    """Errores de sintaxis de bash en comandos y scripts."""
    for where, code in _commands(entry):
        if error := bash_syntax_error(code=code):
            report.errors.append(f"{where}: error de sintaxis: {error}")
    for i, s in enumerate(entry.steps, 1):
        src = entry.files_dir / s.value
        error = (
            bash_syntax_error(path=src)
            if s.kind == "script" and src.is_file()
            else None
        )
        if error:
            report.errors.append(f"step #{i}: {s.value}: error de sintaxis: {error}")


def _check_references(entry: Entry, texts: dict[str, str], report: Report) -> None:
    """Referencias ``$APPFORGE_ENTRY_DIR/...`` a ficheros que no existen."""
    for where, text in texts.items():
        for rel in sorted(set(ENTRY_DIR_REF.findall(text))):
            rel = rel.rstrip("/.")
            if ".." in Path(rel).parts:
                report.errors.append(f"{where}: referencia con '..': {rel}")
            elif not (entry.files_dir / rel).exists():
                report.errors.append(
                    f"{where}: usa $APPFORGE_ENTRY_DIR/{rel}, "
                    f"pero no existe {entry.id}/{rel}"
                )


def _check_unused(entry: Entry, texts: dict[str, str], report: Report) -> None:
    """Ficheros y parámetros declarados que nada usa."""
    used = {s.value for s in entry.steps if s.kind in FILE_KINDS}
    corpus = "\n".join(texts.values())
    for rel in _files(entry):
        if rel not in used and rel not in corpus:
            report.warnings.append(f"fichero sin usar: {entry.id}/{rel}")
    for p in entry.params:
        if not re.search(rf"\$\{{?{re.escape(p.name)}\b", corpus):
            report.warnings.append(f"parámetro sin usar: {p.name}")


def _check_metadata(entry: Entry, report: Report) -> None:
    """Campos recomendados que faltan."""
    if not entry.description:
        report.warnings.append("sin 'description': el catálogo no la describe")
    if not entry.check:
        report.warnings.append("sin [check]: su estado siempre será desconocido")
    if not entry.remove:
        report.warnings.append("sin [remove]: no se podrá desinstalar")


def validate_entry(entry: Entry) -> Report:
    """Valida una entrada ya cargada.

    Args:
        entry: Entrada cargada con :func:`appforge.entry.load_entry`.

    Returns:
        Su informe; ``entry.problems`` cuenta como errores.
    """
    report = Report(entry=entry, errors=list(entry.problems))
    texts = dict(_commands(entry))
    for i, s in enumerate(entry.steps, 1):
        if s.kind in FILE_KINDS:
            texts[f"step #{i} ({s.value})"] = _read_text(entry.files_dir / s.value)
    _check_syntax(entry, report)
    _check_references(entry, texts, report)
    _check_unused(entry, texts, report)
    _check_metadata(entry, report)
    return report


def validate_dir(entries_dir: Path) -> Validation:
    """Valida todas las entradas de un directorio.

    Args:
        entries_dir: Directorio con los ``*.toml``.

    Returns:
        Los informes de cada entrada y los del directorio.
    """
    if not entries_dir.is_dir():
        return Validation(reports=[], errors=[f"{entries_dir}: no es un directorio"])
    entries, dir_problems = load_entries(entries_dir)
    result = Validation(reports=[validate_entry(e) for e in entries])
    result.errors.extend(dir_problems)
    # Los problemas del directorio ya se copiaron a cada entrada: no repetirlos.
    for r in result.reports:
        r.errors = [e for e in r.errors if e not in dir_problems]
    if not entries:
        result.warnings.append(f"{entries_dir}: no hay ninguna entrada (*.toml)")
    ids = {e.id for e in entries}
    for d in sorted(p for p in entries_dir.iterdir() if p.is_dir()):
        if d.name not in ids and not d.name.startswith("."):
            result.warnings.append(f"{d.name}/: subdirectorio sin {d.name}.toml")
    for name, count in Counter(e.name for e in entries).items():
        if count > 1:
            result.warnings.append(f"nombre repetido en {count} entradas: {name}")
    return result
