"""Entrada a la aplicación: sin subcomando abre la TUI.

La TUI hace todo lo interactivo (catálogo, detalle, instalar, desinstalar,
dry-run). La CLI solo tiene lo que no cabe en ella:

- ``appforge validate``: revisa las entradas sin abrir la interfaz, para
  autores de entradas y para la CI.
- ``appforge update``: actualiza la instalación sin perder los cambios del usuario.
- ``appforge --version``.

La TUI y ``update`` exigen ser superusuario; ``validate`` (solo lee ficheros),
``update --dry-run``, ``--help`` y ``--version`` no.
"""

import os
import shlex
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
import typer.rich_utils
from rich.console import Console
from rich.text import Text
from typer.core import TyperCommand, TyperGroup

from appforge import __version__
from appforge.config import Config, ConfigError, load_config
from appforge.theme import RICH_THEME, TYPER_STYLES

if TYPE_CHECKING:
    from appforge.update import Plan

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


def sudo_command() -> list[str] | None:
    """Orden para volver a lanzar AppForge con ``sudo`` desde el código.

    Solo en desarrollo (no empaquetado), con una terminal para pedir la
    contraseña y con ``sudo`` instalado. Se relanza el mismo intérprete del
    entorno con ``-m appforge``; ``sudo`` conserva el directorio de trabajo, que
    es donde se busca ``config.toml``.

    Returns:
        La orden, o ``None`` si no procede.
    """
    if getattr(sys, "frozen", False) or not sys.stdin.isatty():
        return None
    sudo = shutil.which("sudo")
    if sudo is None:
        return None
    return [sudo, "--", sys.executable, "-m", "appforge", *sys.argv[1:]]


def _require_root() -> None:
    """Exige superusuario.

    Desde el código pide la contraseña de ``sudo`` y se relanza; empaquetado,
    sale con código 2 y un mensaje claro.
    """
    if is_root():
        return
    _, err = make_consoles()
    if (command := sudo_command()) is not None:
        err.print(
            Text(
                "AppForge necesita superusuario: pidiendo la contraseña de sudo…",
                style="af.muted",
            )
        )
        os.execv(command[0], command)
    err.print(
        Text.assemble(
            ("appforge: ", "af.error"),
            ("hay que ejecutarlo como superusuario.", "af.error"),
            "\n  Prueba: ",
            (f"sudo {shlex.join(sys.argv)}", "af.id"),
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
    entries_dirs: Annotated[
        list[Path] | None,
        typer.Option(
            "--dir",
            "-d",
            help="Directorio de entradas (repetible). Por defecto, los de config.toml.",
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
        entries_dirs: Directorios a validar en lugar de los configurados.
        strict: Tratar los avisos como errores.
    """
    from appforge.validate import validate_dirs

    out, err = make_consoles()
    folders = list(entries_dirs or _load_config().entries_dirs)
    result = validate_dirs([f.resolve() for f in folders])
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

    out.print(
        Text(f"Entradas en {', '.join(str(f) for f in folders)}", style="af.muted")
    )
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
        out.print(Text("Directorios", style="af.title"))
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


_UPDATE_HELP = """Actualiza AppForge instalado sin perder tus cambios.

Descarga la última Release de GitHub y la verifica con SHA256SUMS (o usa el
paquete de [bold]--from[/]). Sustituye el programa y los ficheros del paquete que no
has tocado. Los que modificaste se conservan y la versión nueva queda junto a
ellos como [bold].new[/]; los que borraste no vuelven. custom-entries/ y logs/ no
se tocan.

Código de salida: 0 bien o ya al día · 1 error · 2 uso.
"""


def installed_dir() -> Path | None:
    """Carpeta de AppForge instalada, o ``None`` si se ejecuta desde el código."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return None


def _print_plan(out: Console, plan: "Plan") -> None:
    """Muestra qué hará la actualización con cada fichero."""
    sections = (
        ("Se actualizan", plan.replace, "ok"),
        ("Nuevos", plan.add, "ok"),
        (
            "Modificados por ti: se conservan; la versión nueva queda en .new",
            plan.keep,
            "warn",
        ),
        ("Retirados del paquete", plan.remove, "muted"),
        ("Retirados del paquete pero modificados: se conservan", plan.orphan, "warn"),
        ("Borrados por ti: no se vuelven a crear", plan.skip, "muted"),
    )
    for title, files, style in sections:
        if files:
            out.print(Text(f"{title} ({len(files)}):", style=f"af.{style}"))
            for rel in files:
                out.print(Text(f"    {rel}"))
    if not any(files for _, files, _ in sections):
        out.print(Text("Recetas y configuración: sin cambios", style="af.muted"))


@app.command(cls=_Command, help=_UPDATE_HELP)
def update(
    package: Annotated[
        Path | None,
        typer.Option(
            "--from",
            help="Paquete .tar.gz local (se verifica con el SHA256SUMS de su carpeta).",
            dir_okay=False,
            exists=True,
            metavar="FICHERO",
            show_default=False,
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", "-n", help="Muestra qué cambiaría, sin cambiar nada."
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", help="Instala aunque sea la misma versión o anterior."),
    ] = False,
) -> None:
    """Actualiza AppForge instalado.

    Args:
        package: Paquete local en lugar de descargarlo.
        dry_run: Solo mostrar el plan.
        force: Permitir la misma versión o una anterior.
    """
    from appforge import update as up

    out, err = make_consoles()
    installed = installed_dir()
    if installed is None:
        err.print(
            Text(
                "appforge: update actualiza el AppForge instalado (el binario del "
                "paquete). Desde el código usa git pull.",
                style="af.error",
            )
        )
        raise typer.Exit(2)
    if not dry_run:
        _require_root()

    work = up.staging_dir(installed)
    try:
        if package is not None:
            sums = package.parent / "SHA256SUMS"
            if sums.is_file():
                up.check_sum(package, sums)
                out.print(
                    Text(f"✔ {package.name}: suma SHA-256 correcta", style="af.ok")
                )
            else:
                out.print(
                    Text(
                        f"! Sin SHA256SUMS junto a {package.name}: no se verifica",
                        style="af.warn",
                    )
                )
        else:
            out.print(Text("Consultando la última versión…", style="af.muted"))
            latest, assets = up.latest_release()
            if not force and up.version_key(latest) <= up.version_key(__version__):
                out.print(
                    Text(
                        f"✔ Ya tienes la última versión ({__version__})", style="af.ok"
                    )
                )
                raise typer.Exit(0)
            out.print(Text(f"Descargando {up.asset_name(latest)}…", style="af.muted"))
            package = up.download(latest, assets, work)
            out.print(Text("✔ Suma SHA-256 correcta", style="af.ok"))

        staged = up.extract(package, work)
        new_version = up.manifest_version(staged)
        if not force and up.version_key(new_version) <= up.version_key(__version__):
            out.print(
                Text(
                    f"El paquete es la {new_version} y tienes la {__version__}: "
                    "usa --force para instalarlo igualmente.",
                    style="af.warn",
                )
            )
            raise typer.Exit(0)
        out.print(Text(f"Programa: {__version__} → {new_version}", style="af.title"))
        plan = up.plan_update(installed, staged)
        _print_plan(out, plan)
        if dry_run:
            out.print(Text("Dry-run: no se ha cambiado nada", style="af.muted"))
            raise typer.Exit(0)
        up.apply_update(installed, staged, plan)
        out.print(Text(f"✔ AppForge actualizado a {new_version}", style="af.ok"))
    except up.UpdateError as e:
        err.print(Text(f"appforge: {e}", style="af.error"))
        raise typer.Exit(1) from None
    finally:
        shutil.rmtree(work, ignore_errors=True)


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
