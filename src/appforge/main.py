"""Entrada a la aplicación: línea de comandos y, sin argumentos, la TUI."""

import argparse
import getpass
import sys

from appforge import __version__
from appforge.config import ConfigError, load_config
from appforge.engine import Engine, EngineError
from appforge.entry import Entry, load_entries

_COLORS = {"step": "1;36", "ok": "1;32", "warn": "1;33", "error": "1;31", "info": "2"}
_PREFIX = {
    "step": "==> ",
    "ok": "✔ ",
    "warn": "! ",
    "error": "✘ ",
    "info": "  ",
    "out": "  │ ",
}


class _ConsoleSink:
    """Imprime la salida del motor con prefijos y, en terminal, colores."""

    def __init__(self, color: bool) -> None:
        """Crea el sink; ``color`` activa las secuencias ANSI."""
        self.color = color

    def __call__(self, kind: str, text: str) -> None:
        """Imprime una línea; los errores van a stderr."""
        line = _PREFIX.get(kind, "") + text
        code = _COLORS.get(kind)
        if self.color and code:
            line = f"\033[{code}m{line}\033[0m"
        print(line, file=sys.stderr if kind == "error" else sys.stdout, flush=True)


def _find(entries: list[Entry], key: str) -> Entry:
    """Entrada con id ``key`` o salida con error."""
    for e in entries:
        if e.id == key:
            return e
    raise SystemExit(f"No existe la entrada '{key}'. Usa 'appforge list'.")


def _parse_sets(items: list[str]) -> dict[str, str]:
    """Convierte ``["a=1", "b=2"]`` en un diccionario."""
    out = {}
    for item in items:
        key, sep, value = item.partition("=")
        if not sep:
            raise SystemExit(f"--set espera nombre=valor, no '{item}'")
        out[key] = value
    return out


def _prompt_values(
    entry: Entry, given: dict[str, str], interactive: bool
) -> dict[str, str]:
    """Pregunta los parámetros que no se dieron con ``--set``."""
    values = dict(given)
    if not interactive:
        return values  # resolve_values usará los defaults o fallará
    for p in entry.params:
        if p.name in values:
            continue
        if p.default:
            hint = " [por defecto]" if p.secret else f" [{p.default}]"
        else:
            hint = ""
        question = f"{p.prompt}{hint}: "
        values[p.name] = getpass.getpass(question) if p.secret else input(question)
    return values


def _state_mark(engine: Engine, entry: Entry) -> str:
    """Marca de estado para ``list``."""
    if not entry.valid:
        return "⚠"
    state = engine.is_applied(entry)
    return {True: "✔", False: " ", None: "·"}[state]


def cmd_list(engine: Engine, entries: list[Entry], args: argparse.Namespace) -> int:
    """Lista las entradas con su estado.

    Args:
        engine: Motor.
        entries: Entradas cargadas.
        args: Argumentos (sin uso).

    Returns:
        Código de salida 0.
    """
    for e in entries:
        root = " (root)" if e.requires_root else ""
        print(f"{_state_mark(engine, e)} {e.id:<20} {e.name}{root}")
    return 0


def cmd_show(engine: Engine, entries: list[Entry], args: argparse.Namespace) -> int:
    """Muestra parámetros, pasos y problemas de una entrada.

    Args:
        engine: Motor (sin uso).
        entries: Entradas cargadas.
        args: Argumentos con ``entry``.

    Returns:
        0 si la entrada es válida, 1 si no.
    """
    e = _find(entries, args.entry)
    print(f"{e.name}  [{e.id}]")
    if e.description:
        print(f"  {e.description}")
    print(f"  root: {'sí' if e.requires_root else 'no'}")
    if e.params:
        print("  parámetros:")
        for p in e.params:
            extra = (
                " (secreto)" if p.secret else (f" = {p.default}" if p.default else "")
            )
            print(f"    - {p.name}: {p.prompt}{extra}")
    print("  pasos:")
    for i, s in enumerate(e.steps, 1):
        dest = f" → {s.dest}" if s.dest else ""
        print(f"    {i}. {s.title}  ({s.kind}{dest})")
    print(
        f"  check: {'sí' if e.check else 'no'}   remove: {'sí' if e.remove else 'no'}"
    )
    for problem in e.problems:
        print(f"  ⚠ {problem}")
    return 0 if e.valid else 1


def cmd_check(engine: Engine, entries: list[Entry], args: argparse.Namespace) -> int:
    """Ejecuta ``[check]`` de una entrada.

    Args:
        engine: Motor.
        entries: Entradas cargadas.
        args: Argumentos con ``entry``.

    Returns:
        0 aplicada, 1 no aplicada, 2 sin ``[check]`` o inválida.
    """
    e = _find(entries, args.entry)
    state = engine.is_applied(e)
    if state is None:
        print("sin [check]" if e.valid else "entrada inválida")
        return 2
    print("aplicada" if state else "no aplicada")
    return 0 if state else 1


def _ensure_root(engine: Engine, entry: Entry, dry_run: bool) -> bool:
    """Pide sudo antes de aplicar si la entrada lo necesita."""
    if dry_run or not entry.requires_root:
        return True
    if engine.password_needed(entry):
        print("Esta entrada necesita privilegios de administrador.")
    return engine.acquire_root()


def cmd_apply(engine: Engine, entries: list[Entry], args: argparse.Namespace) -> int:
    """Aplica una entrada (o la simula con ``--dry-run``).

    Args:
        engine: Motor.
        entries: Entradas cargadas.
        args: Argumentos con ``entry``, ``set``, ``dry_run`` y ``no_input``.

    Returns:
        0 si se aplicó, 1 si no.
    """
    e = _find(entries, args.entry)
    interactive = sys.stdin.isatty() and not args.no_input
    values = _prompt_values(e, _parse_sets(args.set), interactive)
    if not _ensure_root(engine, e, args.dry_run):
        return 1
    try:
        return 0 if engine.apply(e, values, dry_run=args.dry_run) else 1
    except EngineError as ex:
        engine.sink("error", str(ex))
        return 1


def cmd_remove(engine: Engine, entries: list[Entry], args: argparse.Namespace) -> int:
    """Ejecuta ``[remove]`` de una entrada.

    Args:
        engine: Motor.
        entries: Entradas cargadas.
        args: Argumentos con ``entry`` y ``dry_run``.

    Returns:
        0 si se eliminó, 1 si no.
    """
    e = _find(entries, args.entry)
    if not _ensure_root(engine, e, args.dry_run):
        return 1
    return 0 if engine.remove(e, dry_run=args.dry_run) else 1


_COMMANDS = {
    "list": cmd_list,
    "show": cmd_show,
    "check": cmd_check,
    "apply": cmd_apply,
    "remove": cmd_remove,
}


def build_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos.

    Returns:
        El parser con los subcomandos.
    """
    ap = argparse.ArgumentParser(
        prog="appforge", description="Lanzador de recetas de configuración"
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list", help="lista las entradas y su estado")
    for name, help_text in (
        ("show", "muestra una entrada"),
        ("check", "ejecuta [check] de una entrada"),
    ):
        sub.add_parser(name, help=help_text).add_argument("entry")
    a = sub.add_parser("apply", help="aplica una entrada")
    a.add_argument("entry")
    a.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="muestra qué haría sin cambiar nada",
    )
    a.add_argument("-s", "--set", action="append", default=[], metavar="NOMBRE=VALOR")
    a.add_argument(
        "--no-input", action="store_true", help="no preguntar; usar --set y defaults"
    )
    r = sub.add_parser("remove", help="ejecuta [remove] de una entrada")
    r.add_argument("entry")
    r.add_argument("-n", "--dry-run", action="store_true")
    return ap


def main(argv: list[str] | None = None) -> int:
    """Función principal.

    Args:
        argv: Argumentos; ``None`` usa ``sys.argv``.

    Returns:
        Código de salida del proceso.
    """
    args = build_parser().parse_args(argv)
    try:
        config = load_config()
    except ConfigError as e:
        print(f"appforge: {e}", file=sys.stderr)
        return 2

    if args.cmd is None:
        from appforge.tui import run_tui  # Textual solo se carga si hace falta

        return run_tui(config)

    engine = Engine(config, _ConsoleSink(sys.stdout.isatty()))
    entries, _ = load_entries(config.entries_dir)
    try:
        return _COMMANDS[args.cmd](engine, entries, args)
    except KeyboardInterrupt:
        print("\ninterrumpido", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
