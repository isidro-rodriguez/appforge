"""Entrada a la aplicación: línea de comandos y, sin argumentos, la TUI."""

import argparse
import getpass
import sys
from dataclasses import dataclass

from rich.console import Console
from rich.text import Text

from appforge import __version__
from appforge.config import Config, ConfigError, load_config
from appforge.engine import Engine, EngineError
from appforge.entry import Entry, load_entries
from appforge.runlog import RunLog
from appforge.theme import RICH_THEME

_PREFIX = {
    "step": "==> ",
    "ok": "✔ ",
    "warn": "! ",
    "error": "✘ ",
    "info": "  ",
    "out": "  │ ",
}


def make_consoles() -> tuple[Console, Console]:
    """Consolas de Rich con el tema de AppForge para stdout y stderr.

    Respetan ``NO_COLOR`` y desactivan el color fuera de una terminal.

    Returns:
        ``(salida, errores)``.
    """
    out = Console(theme=RICH_THEME, highlight=False, soft_wrap=True)
    err = Console(theme=RICH_THEME, highlight=False, soft_wrap=True, stderr=True)
    return out, err


@dataclass
class Cli:
    """Estado compartido por los subcomandos."""

    config: Config
    entries: list[Entry]
    out: Console
    err: Console

    def sink(self, kind: str, text: str) -> None:
        """Muestra un evento del motor; los errores van a stderr.

        Args:
            kind: Tipo de evento.
            text: Texto del evento.
        """
        console = self.err if kind == "error" else self.out
        console.print(Text(_PREFIX.get(kind, "") + text, style=f"af.{kind}"))

    def engine(self, entry: Entry | None = None) -> Engine:
        """Motor que muestra la salida y, si hay entrada, la registra.

        Args:
            entry: Entrada sobre la que se va a actuar.

        Returns:
            El motor listo para usar.
        """
        if entry is None:
            return Engine(self.config, self.sink)
        runlog = RunLog(self.config)
        return Engine(self.config, runlog.tee(self.sink, f"{entry.id}: "))

    def find(self, key: str) -> Entry:
        """Entrada con id ``key``.

        Args:
            key: Id de la entrada.

        Returns:
            La entrada.

        Raises:
            SystemExit: Si no existe.
        """
        for e in self.entries:
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


def _state_mark(engine: Engine, entry: Entry) -> Text:
    """Marca de estado para ``list``."""
    if not entry.valid:
        return Text("⚠", style="af.invalid")
    state = engine.is_applied(entry)
    if state is None:
        return Text("·", style="af.muted")
    return Text("✔", style="af.applied") if state else Text(" ")


def cmd_list(cli: Cli, args: argparse.Namespace) -> int:
    """Lista las entradas con su estado.

    Args:
        cli: Estado de la CLI.
        args: Argumentos (sin uso).

    Returns:
        Código de salida 0.
    """
    engine = cli.engine()
    for e in cli.entries:
        line = Text.assemble(
            _state_mark(engine, e),
            " ",
            (f"{e.id:<20}", "af.id"),
            " ",
            e.name,
            (f"  {e.category}" if e.category else "", "af.muted"),
            (" (root)" if e.requires_root else "", "af.muted"),
        )
        cli.out.print(line)
    return 0


def cmd_show(cli: Cli, args: argparse.Namespace) -> int:
    """Muestra parámetros, pasos y problemas de una entrada.

    Args:
        cli: Estado de la CLI.
        args: Argumentos con ``entry``.

    Returns:
        0 si la entrada es válida, 1 si no.
    """
    e = cli.find(args.entry)
    p_ = cli.out.print
    p_(Text.assemble((e.name, "af.title"), "  ", (f"[{e.id}]", "af.id")))
    if e.description:
        p_(Text(f"  {e.description}"))
    if e.category:
        p_(Text(f"  categoría: {e.category}", style="af.muted"))
    p_(Text(f"  root: {'sí' if e.requires_root else 'no'}", style="af.muted"))
    if e.params:
        p_(Text("  parámetros:", style="af.title"))
        for p in e.params:
            extra = (
                " (secreto)" if p.secret else (f" = {p.default}" if p.default else "")
            )
            p_(Text(f"    - {p.name}: {p.prompt}{extra}"))
    p_(Text("  pasos:", style="af.title"))
    for i, s in enumerate(e.steps, 1):
        dest = f" → {s.dest}" if s.dest else ""
        p_(Text.assemble(f"    {i}. {s.title}  ", (f"({s.kind}{dest})", "af.muted")))
    check = "sí" if e.check else "no"
    remove = "sí" if e.remove else "no"
    p_(Text(f"  check: {check}   remove: {remove}", style="af.muted"))
    for problem in e.problems:
        p_(Text(f"  ⚠ {problem}", style="af.invalid"))
    return 0 if e.valid else 1


def cmd_check(cli: Cli, args: argparse.Namespace) -> int:
    """Ejecuta ``[check]`` de una entrada.

    Args:
        cli: Estado de la CLI.
        args: Argumentos con ``entry``.

    Returns:
        0 aplicada, 1 no aplicada, 2 sin ``[check]`` o inválida.
    """
    e = cli.find(args.entry)
    state = cli.engine().is_applied(e)
    if state is None:
        cli.out.print("sin [check]" if e.valid else "entrada inválida", markup=False)
        return 2
    cli.out.print(Text("aplicada", "af.applied") if state else Text("no aplicada"))
    return 0 if state else 1


def _ensure_root(cli: Cli, engine: Engine, entry: Entry, dry_run: bool) -> bool:
    """Pide sudo antes de aplicar si la entrada lo necesita."""
    if dry_run or not entry.requires_root:
        return True
    if engine.password_needed(entry):
        cli.out.print("Esta entrada necesita privilegios de administrador.")
    return engine.acquire_root()


def cmd_apply(cli: Cli, args: argparse.Namespace) -> int:
    """Aplica una entrada (o la simula con ``--dry-run``).

    Args:
        cli: Estado de la CLI.
        args: Argumentos con ``entry``, ``set``, ``dry_run`` y ``no_input``.

    Returns:
        0 si se aplicó, 1 si no.
    """
    e = cli.find(args.entry)
    interactive = sys.stdin.isatty() and not args.no_input
    values = _prompt_values(e, _parse_sets(args.set), interactive)
    engine = cli.engine(e)
    if not _ensure_root(cli, engine, e, args.dry_run):
        return 1
    try:
        return 0 if engine.apply(e, values, dry_run=args.dry_run) else 1
    except EngineError as ex:
        engine.sink("error", str(ex))
        return 1


def cmd_remove(cli: Cli, args: argparse.Namespace) -> int:
    """Ejecuta ``[remove]`` de una entrada.

    Args:
        cli: Estado de la CLI.
        args: Argumentos con ``entry`` y ``dry_run``.

    Returns:
        0 si se eliminó, 1 si no.
    """
    e = cli.find(args.entry)
    engine = cli.engine(e)
    if not _ensure_root(cli, engine, e, args.dry_run):
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
    out, err = make_consoles()
    try:
        config = load_config()
    except ConfigError as e:
        err.print(Text(f"appforge: {e}", style="af.error"))
        return 2

    if args.cmd is None:
        from appforge.tui import run_tui  # Textual solo se carga si hace falta

        return run_tui(config)

    entries, _ = load_entries(config.entries_dir)
    cli = Cli(config=config, entries=entries, out=out, err=err)
    try:
        return _COMMANDS[args.cmd](cli, args)
    except KeyboardInterrupt:
        err.print("\ninterrumpido")
        return 130


if __name__ == "__main__":
    sys.exit(main())
