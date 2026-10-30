"""Genera las capturas SVG de la TUI para la documentación.

Usa solo las recetas reales del repositorio, copiadas a un directorio temporal.
Nada se instala: las capturas de progreso son *dry-run* y la confirmación se
cancela. Las comprobaciones (``[check]``) sí se ejecutan, y son de solo lectura. También
captura la ayuda y la salida de ``appforge validate``. Las capturas quedan en
``docs/assets/images/screenshots/``.

Uso:
    poe screenshots
    uv run python scripts/screenshots.py
"""

import asyncio
import io
import os
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "assets" / "images" / "screenshots"
SIZE = (120, 34)

ENTRIES = "appforge-entries"  # como en el paquete
# Receta que protagoniza la portada (escribir, revisar, aplicar): usa parámetros,
# plantilla, scripts, comprobación y eliminación.
FEATURED = "ssh-server"
BATCH = {"firewall", "incus", "docker"}


def _make_home(base: Path, ui: bool) -> Path:
    """Directorio de AppForge con las recetas reales del repositorio."""
    home = base / ("ui" if ui else "plain")
    shutil.copytree(ROOT / "entries", home / ENTRIES)
    flag = "true" if ui else "false"
    (home / "config.toml").write_text(
        f'entries_dirs = ["{ENTRIES}"]\n[ui]\nsearch = {flag}\ncategories = {flag}\n',
        encoding="utf-8",
    )
    for p in [home, *home.rglob("*")]:
        p.chmod(p.stat().st_mode & ~0o022)
    return home


async def _wait(pilot: object, condition: Callable[[], bool]) -> None:
    """Espera (hasta 10 s) a que se cumpla ``condition``."""
    for _ in range(200):
        if condition():
            return
        await pilot.pause(0.05)  # type: ignore[attr-defined]


async def _capture(base: Path) -> None:
    """Recorre la TUI y guarda cada pantalla."""
    from textual.widgets import Button, ListView, Select

    from appforge.config import load_config
    from appforge.tui import (
        AppForgeApp,
        ConfirmScreen,
        DetailScreen,
        ParamsScreen,
        ProgressScreen,
    )

    def save(app: AppForgeApp, name: str) -> None:
        app.save_screenshot(filename=f"{name}.svg", path=str(OUT))

    def highlight(app: AppForgeApp, entry_id: str) -> None:
        ids = [e.id for e in app.visible_entries()]
        app.query_one("#apps", ListView).index = ids.index(entry_id)

    async def detail(app: AppForgeApp, entry_id: str, name: str) -> None:
        highlight(app, entry_id)
        await pilot.pause(0.2)
        await pilot.press("v")
        await _wait(pilot, lambda: isinstance(app.screen, DetailScreen))
        await pilot.pause(0.3)
        save(app, name)
        await pilot.press("escape")

    async def until(app: AppForgeApp, target: type) -> None:
        """Acepta los parámetros por defecto hasta llegar a ``target``."""
        for _ in range(100):
            if isinstance(app.screen, target):
                await pilot.pause(0.3)
                return
            if isinstance(app.screen, ParamsScreen):
                app.screen.query_one("#ok", Button).press()
            await pilot.pause(0.1)
        raise RuntimeError(f"no se llegó a {target.__name__} ({app.screen})")

    async def dry_run(app: AppForgeApp, marked: set[str]) -> None:
        """Dry-run de ``marked`` con los parámetros por defecto."""
        app.marked = set(marked)
        app._repaint()
        await pilot.press("d")
        await until(app, ProgressScreen)
        screen = app.screen
        await _wait(pilot, lambda: not getattr(screen, "running", True))
        await pilot.pause(0.3)

    app = AppForgeApp(load_config(_make_home(base, ui=True)))
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause(0.5)
        await app.workers.wait_for_complete()
        app.marked = set(BATCH)
        app._repaint()
        highlight(app, FEATURED)
        await pilot.pause(0.3)
        save(app, "catalogo")

        await detail(app, FEATURED, "detalle")
        await detail(app, "ollama", "detalle-ollama")

        app.marked = {"ollama"}
        app._repaint()
        await pilot.press("d")
        await _wait(pilot, lambda: isinstance(app.screen, ParamsScreen))
        app.screen.query_one("#p_kv_cache", Select).value = "q4_0"
        await pilot.pause(0.2)
        save(app, "parametros")
        await pilot.press("escape")

        app.marked = set(BATCH)
        app._repaint()
        await pilot.press("i")
        await until(app, ConfirmScreen)
        save(app, "confirmar")
        await pilot.press("n")
        await pilot.pause(0.2)

        await dry_run(app, {FEATURED})
        save(app, "progreso")
        await pilot.press("escape")
        await pilot.pause(0.2)

        await dry_run(app, BATCH)
        save(app, "progreso-final")

    app = AppForgeApp(load_config(_make_home(base, ui=False)))
    async with app.run_test(size=(100, 26)) as pilot:
        await pilot.pause(0.5)
        await app.workers.wait_for_complete()
        await pilot.pause(0.2)
        save(app, "catalogo-simple")


def _terminal_theme() -> object:
    """Tema del SVG de Rich con el fondo y el texto de AppForge."""
    from rich.terminal_theme import DEFAULT_TERMINAL_THEME, TerminalTheme

    from appforge.theme import BACKGROUND, CREAM

    def rgb(color: str) -> tuple[int, int, int]:
        return (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))

    ansi = [tuple(c) for c in DEFAULT_TERMINAL_THEME.ansi_colors._colors]
    return TerminalTheme(rgb(BACKGROUND), rgb(CREAM), ansi[:8], ansi[8:])  # type: ignore[arg-type]


def _capture_cli(base: Path) -> None:
    """Captura ``appforge --help`` y ``appforge validate`` como SVG."""
    import typer.rich_utils
    from rich.console import Console

    from appforge import main as cli
    from appforge.theme import RICH_THEME

    theme = _terminal_theme()
    width = 88

    def recorder(**kwargs: object) -> Console:
        return Console(
            file=io.StringIO(),
            record=True,
            width=width,
            force_terminal=True,
            color_system="truecolor",
            **kwargs,  # type: ignore[arg-type]
        )

    # Ayuda: Typer crea su consola en cada llamada; se sustituye por una que graba.
    original = typer.rich_utils._get_rich_console
    holder: list[Console] = []

    def recording_console(stderr: bool = False) -> Console:
        console = original(stderr)
        console.file = io.StringIO()
        console.record = True
        console.width = width
        holder.append(console)
        return console

    typer.rich_utils.FORCE_TERMINAL = True
    typer.rich_utils.COLOR_SYSTEM = "truecolor"
    typer.rich_utils._get_rich_console = recording_console
    try:
        cli.main(["validate", "--help"])
    finally:
        typer.rich_utils._get_rich_console = original
    holder[-1].save_svg(
        str(OUT / "cli-ayuda.svg"), title="appforge validate --help", theme=theme
    )

    # validate: las recetas reales, con un script de firewall borrado a propósito.
    entries = base / "validate" / ENTRIES
    shutil.copytree(ROOT / "entries", entries)
    (entries / "firewall" / "configure-ufw.sh").unlink()
    for p in [entries.parent, *entries.parent.rglob("*")]:
        p.chmod(p.stat().st_mode & ~0o022)
    out = recorder(theme=RICH_THEME, highlight=False)
    cli.make_consoles = lambda: (out, out)  # type: ignore[assignment]
    cwd = Path.cwd()
    os.chdir(entries.parent)  # la salida muestra la ruta tal cual
    try:
        cli.main(["validate", "--dir", ENTRIES])
    finally:
        os.chdir(cwd)
    out.save_svg(str(OUT / "cli-validate.svg"), title="appforge validate", theme=theme)  # type: ignore[arg-type]


def _show_installed_paths(base: Path) -> None:
    """Muestra las rutas temporales como en una instalación en ``/opt/appforge``."""
    from appforge import tui

    def short(path: Path) -> str:
        text = str(path)
        for name in ("ui", "plain"):
            prefix = str(base / name)
            if text.startswith(prefix + os.sep):
                return "/opt/appforge" + text[len(prefix) :]
        return text

    tui._home_short = short  # type: ignore[assignment]

    # Las rutas de los scripts en el registro del dry-run, también como en /opt.
    from appforge.engine import Runner

    mask = Runner.mask

    def short_mask(self: Runner, text: str) -> str:
        for name in ("ui", "plain"):
            text = text.replace(str(base / name), "/opt/appforge")
        return mask(self, text)

    Runner.mask = short_mask  # type: ignore[method-assign]
    # Usuario genérico en la confirmación, sea quien sea quien genera las capturas.
    from appforge import engine

    generic = lambda: ("usuario", "/home/usuario")  # noqa: E731
    tui.invoking_user = generic  # type: ignore[assignment]
    engine.invoking_user = generic  # type: ignore[assignment]


def main() -> None:
    """Genera todas las capturas en ``docs/assets/images/screenshots/``."""
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="appforge-shots-") as tmp:
        base = Path(tmp)
        _show_installed_paths(base)
        asyncio.run(_capture(base))
        _capture_cli(base)
    for svg in sorted(OUT.glob("*.svg")):
        print(svg.relative_to(ROOT))


if __name__ == "__main__":
    main()
