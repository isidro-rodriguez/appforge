"""Entrada a la aplicación: sin subcomando abre la TUI.

La TUI hace todo lo interactivo (catálogo, detalle, instalar, desinstalar,
dry-run). La CLI solo tiene lo que no cabe en ella:

- ``appforge validate``: revisa las entradas sin abrir la interfaz, para
  autores de entradas y para la CI.
- ``appforge --version``.

Todo salvo ``--help`` y ``--version`` exige ser superusuario.
"""

import os
import shlex
import sys
from pathlib import Path
from typing import Annotated, Any

import typer
import typer.rich_utils
from rich.console import Console
from rich.text import Text
from typer.core import TyperCommand, TyperGroup

from appforge import __version__
from appforge.config import Config, ConfigError, load_config
from appforge.theme import RICH_THEME, TYPER_STYLES

# Textos de la ayuda de Typer en español.
_TYPER_TEXTS = {
    "ARGUMENTS_PANEL_TITLE": "Argumentos",
    "OPTIONS_PANEL_TITLE": "Opciones",
    "COMMANDS_PANEL_TITLE": "Comandos",
    "ERRORS_PANEL_TITLE": "Error",
    "ABORTED_TEXT": "Cancelado.",
    "RICH_HELP": "Prueba [bold]'{command_path} {help_option}'[/] para ver la ayuda.",
    "DEFAULT_STRING": "[por defecto: {}]",
    "REQUIRED_LONG_STRING": "[obligatorio]",
}


def _style_typer() -> None:
    """Aplica a la ayuda de Typer los colores y textos de AppForge."""
    for name, value in {**TYPER_STYLES, **_TYPER_TEXTS}.items():
        setattr(typer.rich_utils, name, value)


def _write_usage(command: Any, ctx: Any, formatter: Any) -> None:
    """Escribe ``Uso: ...`` en lugar de ``Usage: ...``."""
    usage = " ".join(command.collect_usage_pieces(ctx))
    usage = usage.replace("[OPTIONS]", "[OPCIONES]")
    usage = usage.replace("COMMAND [ARGS]", "COMANDO [ARGS]")
    formatter.write_usage(ctx.command_path, usage, "Uso: ")


def _spanish_help(option: Any) -> Any:
    """Traduce el texto de la opción ``-h/--help``."""
    if option is not None:
        option.help = "Muestra esta ayuda y sale."
    return option


class _Group(TyperGroup):
    """Grupo de comandos con la ayuda en español."""

    def format_usage(self, ctx: Any, formatter: Any) -> None:
        """Línea de uso en español."""
        _write_usage(self, ctx, formatter)

    def get_help_option(self, ctx: Any) -> Any:
        """Opción de ayuda en español."""
        return _spanish_help(super().get_help_option(ctx))


class _Command(TyperCommand):
    """Comando con la ayuda en español."""

    def format_usage(self, ctx: Any, formatter: Any) -> None:
        """Línea de uso en español."""
        _write_usage(self, ctx, formatter)

    def get_help_option(self, ctx: Any) -> Any:
        """Opción de ayuda en español."""
        return _spanish_help(super().get_help_option(ctx))


app = typer.Typer(
    name="appforge",
    cls=_Group,
    help="Recetas de configuración repetibles. Sin comando abre la TUI.",
    add_completion=False,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
    pretty_exceptions_enable=False,
)


def make_consoles() -> tuple[Console, Console]:
    """Consolas de Rich con el tema de AppForge para stdout y stderr.

    Respetan ``NO_COLOR`` y desactivan el color fuera de una terminal.

    Returns:
        ``(salida, errores)``.
    """
    out = Console(theme=RICH_THEME, highlight=False, soft_wrap=True)
    err = Console(theme=RICH_THEME, highlight=False, soft_wrap=True, stderr=True)
    return out, err


def is_root() -> bool:
    """``True`` si el proceso se ejecuta como superusuario."""
    return os.geteuid() == 0


def _require_root() -> None:
    """Sale con código 2 y un mensaje claro si no se es superusuario."""
    if is_root():
        return
    command = shlex.join(sys.argv)
    make_consoles()[1].print(
        Text.assemble(
            ("appforge: ", "af.error"),
            ("hay que ejecutarlo como superusuario.", "af.error"),
            "\n  Prueba: ",
            (f"sudo {command}", "af.id"),
        )
    )
    raise typer.Exit(2)


def _load_config() -> Config:
    """Configuración o salida con código 2 si ``config.toml`` es inválido."""
    try:
        return load_config()
    except ConfigError as e:
        make_consoles()[1].print(Text(f"appforge: {e}", style="af.error"))
        raise typer.Exit(2) from None


def _show_version(value: bool) -> None:
    """Muestra la versión y sale (callback de ``--version``)."""
    if value:
        make_consoles()[0].print(f"appforge {__version__}", markup=False)
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def root(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="Muestra la versión y sale.",
            callback=_show_version,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Recetas de configuración repetibles. Sin comando abre la TUI.

    Args:
        ctx: Contexto de Typer.
        version: ``--version`` (lo gestiona su callback).
    """
    if ctx.invoked_subcommand is not None:
        return
    _require_root()
    config = _load_config()
    from appforge.tui import run_tui  # Textual solo se carga si hace falta

    raise typer.Exit(run_tui(config))


def _print_lines(out: Console, items: list[str], kind: str, mark: str) -> None:
    """Imprime los problemas de una entrada, sangrados."""
    for item in items:
        out.print(Text(f"    {mark} {item}", style=f"af.{kind}"))


_VALIDATE_HELP = """Revisa las entradas sin ejecutarlas.

[bold]Errores[/]: TOML, claves y seguridad; sintaxis de bash; ficheros que faltan
en el subdirectorio de la entrada (pasos y $APPFORGE_ENTRY_DIR/...).

[bold]Avisos[/]: ficheros y parámetros sin usar, sin \\[check] o \\[remove],
sin description, nombres repetidos y subdirectorios sin su .toml.

Código de salida: 0 bien · 1 errores (o avisos con --strict) · 2 uso.
"""


@app.command(cls=_Command, help=_VALIDATE_HELP)
def validate(
    ids: Annotated[
        list[str] | None,
        typer.Argument(
            metavar="ID...",
            help="Entradas a validar (nombre del .toml). Por defecto, todas.",
            show_default=False,
        ),
    ] = None,
    entries_dir: Annotated[
        Path | None,
        typer.Option(
            "--dir",
            "-d",
            help="Directorio de entradas. Por defecto, el de config.toml.",
            file_okay=False,
            metavar="DIR",
            show_default=False,
        ),
    ] = None,
    strict: Annotated[
        bool,
        typer.Option("--strict", "-s", help="Los avisos también hacen fallar."),
    ] = False,
) -> None:
    """Revisa las entradas sin ejecutarlas.

    Args:
        ids: Ids de las entradas; vacío para todas.
        entries_dir: Directorio a validar en lugar del configurado.
        strict: Tratar los avisos como errores.
    """
    from appforge.validate import validate_dir

    _require_root()
    out, err = make_consoles()
    folder = entries_dir if entries_dir is not None else _load_config().entries_dir
    result = validate_dir(folder.resolve())
    reports = result.reports
    if ids:
        known = {r.entry.id for r in reports}
        if unknown := [i for i in ids if i not in known]:
            err.print(
                Text(f"appforge: no existe la entrada: {', '.join(unknown)}"),
                style="af.error",
            )
            raise typer.Exit(2)
        reports = [r for r in reports if r.entry.id in ids]

    out.print(Text(f"Entradas en {folder}", style="af.muted"))
    for r in reports:
        if r.errors:
            mark, style = "✘", "af.error"
        elif r.warnings:
            mark, style = "!", "af.warn"
        else:
            mark, style = "✔", "af.ok"
        out.print(
            Text.assemble(
                (mark, style), " ", (f"{r.entry.id:<20}", "af.id"), " ", r.entry.name
            )
        )
        _print_lines(out, r.errors, "error", "✘")
        _print_lines(out, r.warnings, "warn", "!")

    general_errors = result.errors
    general_warnings = result.warnings if not ids else []
    if general_errors or general_warnings:
        out.print(Text("Directorio", style="af.title"))
        _print_lines(out, general_errors, "error", "✘")
        _print_lines(out, general_warnings, "warn", "!")

    errors = len(general_errors) + sum(len(r.errors) for r in reports)
    warnings = len(general_warnings) + sum(len(r.warnings) for r in reports)
    summary = f"entradas: {len(reports)} · errores: {errors} · avisos: {warnings}"
    failed = errors > 0 or (strict and warnings > 0)
    out.print(
        Text(
            ("✘ " if failed else "✔ ") + summary,
            style="af.error" if failed else "af.ok",
        )
    )
    raise typer.Exit(1 if failed else 0)


def main(argv: list[str] | None = None) -> int:
    """Función principal.

    Args:
        argv: Argumentos; ``None`` usa ``sys.argv``.

    Returns:
        Código de salida del proceso.
    """
    _style_typer()
    try:
        app(args=argv, prog_name="appforge")
    except SystemExit as e:
        if e.code is None or isinstance(e.code, int):
            return e.code or 0
        print(e.code, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
