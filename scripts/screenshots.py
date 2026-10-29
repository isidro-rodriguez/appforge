"""Genera las capturas SVG de la TUI para la documentación.

Usa la entrada real ``ollama`` y varias entradas de demostración que solo hacen
``echo``/``sleep`` en un directorio temporal: no toca el sistema. Las capturas
quedan en ``docs/assets/images/screenshots/``.

Uso:
    poe screenshots
    uv run python scripts/screenshots.py
"""

import asyncio
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
    "git-aliases": ("Alias de git", "Desarrollo", "Alias globales de git", True),
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
        app.screen.query_one("#p_owner", Input).value = "isidro"
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


def main() -> None:
    """Genera todas las capturas en ``docs/assets/images/screenshots/``."""
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="appforge-shots-") as tmp:
        base = Path(tmp)
        # HOME falso: las rutas se muestran como ~/.local/state/... sin datos reales.
        os.environ.update(
            HOME=str(base),
            APPFORGE_SUDO="",
            XDG_STATE_HOME=str(base / ".local" / "state"),
        )
        asyncio.run(_capture(base))
    for svg in sorted(OUT.glob("*.svg")):
        print(svg.relative_to(ROOT))


if __name__ == "__main__":
    main()
