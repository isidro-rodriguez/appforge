"""Genera las capturas SVG de la TUI para la documentación.

Usa la entrada real ``ollama`` y varias entradas de demostración que solo hacen
``echo``/``sleep`` en un directorio temporal: no toca el sistema. También
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

# id: (nombre, categoría, descripción, ¿aplicada?)
DEMO = {
    "docker": (
        "Docker Engine",
        "Desarrollo",
        "Docker desde el repositorio oficial",
        False,
    ),
    "firefox": ("Firefox", "Navegadores", "Navegador web de Mozilla", True),
    "vlc": ("VLC", "Multimedia", "Reproductor multimedia", False),
    "steam": ("Steam", "Juegos", "Cliente de Steam", False),
    "wireguard": ("WireGuard", "Red", "Túnel VPN con clave propia", False),
}


def _demo_entry(entry_id: str, fields: tuple[str, str, str, bool], marks: Path) -> str:
    """TOML de una entrada de demostración inofensiva (escribe en ``marks``)."""
    name, category, description, applied = fields
    marker = marks / entry_id
    if applied:
        marks.mkdir(parents=True, exist_ok=True)
        marker.touch()
    return f'''name = "{name}"
category = "{category}"
description = "{description}"
details = "Entrada de demostración para las capturas de la documentación."
[check]
run = "test -f {marker}"
[[step]]
title = "Añadir repositorio"
run = "echo descargando clave del repositorio; sleep 0.4; echo repositorio añadido"
[[step]]
title = "Instalar paquete"
run = "echo instalando {name}; sleep 0.8; mkdir -p {marks}; touch {marker}; echo listo"
[remove]
run = "rm -f {marker}"
'''


def _make_home(base: Path, ui: bool) -> Path:
    """Directorio de AppForge con la entrada ollama y las de demostración."""
    home = base / ("ui" if ui else "plain")
    shutil.copytree(ROOT / "entries", home / "entries")
    for entry_id, fields in DEMO.items():
        text = _demo_entry(entry_id, fields, home / "marks")
        (home / "entries" / f"{entry_id}.toml").write_text(text, encoding="utf-8")
    flag = "true" if ui else "false"
    (home / "config.toml").write_text(
        f'entries_dir = "entries"\n[ui]\nsearch = {flag}\ncategories = {flag}\n',
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
    from textual.widgets import Input, ListView

    from appforge.config import load_config
    from appforge.tui import AppForgeApp, DetailScreen, ParamsScreen, ProgressScreen

    def save(app: AppForgeApp, name: str) -> None:
        app.save_screenshot(filename=f"{name}.svg", path=str(OUT))

    def highlight(app: AppForgeApp, entry_id: str) -> None:
        ids = [e.id for e in app.visible_entries()]
        app.query_one("#apps", ListView).index = ids.index(entry_id)

    app = AppForgeApp(load_config(_make_home(base, ui=True)))
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause(0.5)
        await app.workers.wait_for_complete()
        app.marked = {"docker", "vlc", "steam"}
        app._repaint()
        highlight(app, "steam")
        await pilot.pause(0.3)
        save(app, "catalogo")

        await pilot.press("v")
        await _wait(pilot, lambda: isinstance(app.screen, DetailScreen))
        await pilot.pause(0.3)
        save(app, "detalle-demo")
        await pilot.press("escape")

        highlight(app, "ollama")
        await pilot.pause(0.2)
        await pilot.press("v")
        await _wait(pilot, lambda: isinstance(app.screen, DetailScreen))
        await pilot.pause(0.3)
        save(app, "detalle")
        await pilot.press("escape")

        app.marked = {"ollama"}
        app._repaint()
        await pilot.press("d")
        await _wait(pilot, lambda: isinstance(app.screen, ParamsScreen))
        app.screen.query_one("#p_kv_cache", Input).value = "q4_0"
        await pilot.pause(0.2)
        save(app, "parametros")
        await pilot.press("escape")

        app.marked = {"docker", "vlc", "steam"}
        app._repaint()
        await pilot.press("i")
        await pilot.pause(0.3)
        save(app, "confirmar")
        await pilot.press("y")
        await _wait(pilot, lambda: isinstance(app.screen, ProgressScreen))
        await pilot.pause(2.6)
        save(app, "progreso")
        screen = app.screen
        await _wait(pilot, lambda: not getattr(screen, "running", True))
        await pilot.pause(0.2)
        save(app, "progreso-final")

    app = AppForgeApp(load_config(_make_home(base, ui=False)))
    async with app.run_test(size=(100, 26)) as pilot:
        await pilot.pause(0.5)
        await app.workers.wait_for_complete()
        await pilot.pause(0.2)
        save(app, "catalogo-simple")


# Una entrada rota para la captura de ``appforge validate``.
BROKEN = """name = "Docker Engine"
description = "Docker desde el repositorio oficial"
category = "Desarrollo"
[check]
run = "command -v docker"
[[step]]
title = "Repositorio"
copy = "docker.list"
dest = "/etc/apt/sources.list.d/docker.list"
"""


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

    # validate: la entrada ollama, git-alias y una rota en un directorio de prueba.
    entries = base / "validate" / "entries"
    shutil.copytree(ROOT / "entries", entries)
    (entries / "docker.toml").write_text(BROKEN, encoding="utf-8")
    for p in [entries.parent, *entries.parent.rglob("*")]:
        p.chmod(p.stat().st_mode & ~0o022)
    out = recorder(theme=RICH_THEME, highlight=False)
    cli.make_consoles = lambda: (out, out)  # type: ignore[assignment]
    cwd = Path.cwd()
    os.chdir(entries.parent)  # la salida muestra la ruta tal cual: "entries"
    try:
        cli.main(["validate", "--dir", "entries"])
    finally:
        os.chdir(cwd)
    out.save_svg(str(OUT / "cli-validate.svg"), title="appforge validate", theme=theme)  # type: ignore[arg-type]


def _show_installed_paths(base: Path) -> None:
    """Muestra las rutas temporales como un ``appforge/`` descomprimido en un HOME."""
    from appforge import tui

    def short(path: Path) -> str:
        text = str(path)
        for name in ("ui", "plain"):
            prefix = str(base / name)
            if text.startswith(prefix + os.sep):
                return "/home/usuario/appforge" + text[len(prefix) :]
        return text

    tui._home_short = short  # type: ignore[assignment]
    # Usuario genérico en la confirmación, sea quien sea quien genera las capturas.
    tui.invoking_user = lambda: ("usuario", "/home/usuario")  # type: ignore[assignment]


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
