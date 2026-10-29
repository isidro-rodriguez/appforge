"""TUI con Pilot: catálogo, selección, lotes, cancelación y opciones [ui]."""

import shutil
from pathlib import Path

import pytest
from textual.widgets import Input, Label, ListView, ProgressBar, RichLog

from appforge.config import Config, load_config
from appforge.tui import (
    AppForgeApp,
    AppRow,
    CategoryRow,
    ConfirmScreen,
    DetailScreen,
    ParamsScreen,
    ProgressScreen,
    entry_markdown,
)

SIZE = (100, 30)


def demo_entry(name: str, category: str, dest: Path, run: str = "true") -> str:
    return f"""
name = "{name}"
category = "{category}"
[check]
run = "test -f {dest}/{name}"
[[step]]
title = "Paso de {name}"
run = "{run}"
[[step]]
title = "Marca"
run = "mkdir -p {dest} && touch {dest}/{name}"
[remove]
run = "rm -f {dest}/{name}"
"""


@pytest.fixture(autouse=True)
def only_ollama(home: Path) -> None:
    """Deja solo la entrada de referencia: los tests no dependen de los ejemplos."""
    entries = home / "entries"
    for toml in entries.glob("*.toml"):
        if toml.stem != "ollama":
            toml.unlink()
            shutil.rmtree(entries / toml.stem, ignore_errors=True)


@pytest.fixture
def demo(config: Config, write_entry, tmp_path: Path) -> Path:
    """Dos entradas sin root que escriben en ``tmp_path/out``."""
    dest = tmp_path / "out"
    write_entry("alpha", demo_entry("alpha", "Herramientas", dest))
    write_entry("beta", demo_entry("beta", "Juegos", dest))
    return dest


def with_ui(home: Path, **ui: bool) -> Config:
    lines = "\n".join(f"{k} = {'true' if v else 'false'}" for k, v in ui.items())
    (home / "config.toml").write_text(f'entries_dir = "entries"\n[ui]\n{lines}\n')
    return load_config(home)


async def settle(app: AppForgeApp, pilot) -> None:
    await pilot.pause()
    await app.workers.wait_for_complete()
    await pilot.pause()


async def wait_for(pilot, condition, tries: int = 100) -> None:
    for _ in range(tries):
        if condition():
            return
        await pilot.pause(0.05)
    raise AssertionError("la condición no se cumplió a tiempo")


def rows(app: AppForgeApp) -> list[str]:
    return [r.entry.id for r in app.query(AppRow)]


def highlight(app: AppForgeApp, entry_id: str) -> None:
    app.query_one("#apps", ListView).index = rows(app).index(entry_id)


def log_text(screen: ProgressScreen) -> str:
    return "\n".join(line.text for line in screen.query_one(RichLog).lines)


async def test_catalog_without_ui_options(config: Config) -> None:
    app = AppForgeApp(config)
    async with app.run_test(size=SIZE) as pilot:
        await settle(app, pilot)
        assert rows(app) == ["ollama"]
        assert app.checked == {"ollama"}
        assert not app.query("#search")
        assert not app.query("#categories")
        assert app.check_action("focus_search", ()) is False
        await pilot.press("slash")  # sin buscador no hace nada


async def test_dry_run_flow_keeps_selection(config: Config) -> None:
    app = AppForgeApp(config)
    async with app.run_test(size=SIZE) as pilot:
        await settle(app, pilot)
        await pilot.press("space")
        assert app.marked == {"ollama"}
        await pilot.press("d")
        await wait_for(pilot, lambda: isinstance(app.screen, ParamsScreen))
        app.screen.query_one("#p_owner", Input).value = "isidro"
        await pilot.click("#ok")
        await wait_for(pilot, lambda: isinstance(app.screen, ProgressScreen))
        screen = app.screen
        assert isinstance(screen, ProgressScreen)
        await wait_for(pilot, lambda: not screen.running)
        assert "Dry-run completado" in log_text(screen)
        assert "[tpl ] +OLLAMA_MODELS=/opt/ollama/models" in log_text(screen)
        assert screen.query_one(ProgressBar).percentage == 1
        await pilot.press("escape")
        await wait_for(pilot, lambda: not isinstance(app.screen, ProgressScreen))
        assert app.marked == {"ollama"}  # un dry-run no consume la selección
    assert not Path("/opt/ollama/ollama.env").exists()


async def test_batch_install_and_uninstall(config: Config, demo: Path) -> None:
    app = AppForgeApp(config)
    async with app.run_test(size=SIZE) as pilot:
        await settle(app, pilot)
        assert rows(app) == ["alpha", "beta", "ollama"]
        await pilot.press("space", "down", "space")
        assert app.marked == {"alpha", "beta"}
        await pilot.press("i")
        await wait_for(pilot, lambda: isinstance(app.screen, ConfirmScreen))
        await pilot.press("y")
        await wait_for(pilot, lambda: isinstance(app.screen, ProgressScreen))
        screen = app.screen
        assert isinstance(screen, ProgressScreen)
        # Mientras corre, los atajos del catálogo no se ven ni actúan.
        assert app.check_action("run", ("apply", False)) is False
        await wait_for(pilot, lambda: not screen.running)
        assert screen.done == {"alpha", "beta"}
        assert (demo / "alpha").exists()
        assert (demo / "beta").exists()
        await pilot.press("escape")
        await settle(app, pilot)
        assert app.marked == set()
        assert app.states["alpha"] is True

        highlight(app, "alpha")
        await pilot.press("u")
        await wait_for(pilot, lambda: isinstance(app.screen, ConfirmScreen))
        await pilot.press("y")
        await wait_for(pilot, lambda: isinstance(app.screen, ProgressScreen))
        screen = app.screen
        assert isinstance(screen, ProgressScreen)
        await wait_for(pilot, lambda: not screen.running)
        assert not (demo / "alpha").exists()


async def test_cancel_stops_running_command(
    config: Config, write_entry, tmp_path: Path
) -> None:
    write_entry("slow", demo_entry("slow", "Lento", tmp_path / "out", run="sleep 30"))
    app = AppForgeApp(config)
    async with app.run_test(size=SIZE) as pilot:
        await settle(app, pilot)
        highlight(app, "slow")
        await pilot.pause()
        await pilot.press("i")
        await wait_for(pilot, lambda: isinstance(app.screen, ConfirmScreen))
        await pilot.press("y")
        await wait_for(pilot, lambda: isinstance(app.screen, ProgressScreen))
        screen = app.screen
        assert isinstance(screen, ProgressScreen)
        await wait_for(pilot, lambda: "slow: [1/2]" in log_text(screen))
        await pilot.pause(0.3)
        await pilot.press("ctrl+c")
        await wait_for(pilot, lambda: not screen.running, tries=60)
        assert screen.done == set()
        assert "Cancelado por el usuario" in log_text(screen)
        assert not (tmp_path / "out" / "slow").exists()


async def test_search_and_categories(home: Path, demo: Path) -> None:
    config = with_ui(home, search=True, categories=True)
    app = AppForgeApp(config)
    async with app.run_test(size=SIZE) as pilot:
        await settle(app, pilot)
        cats = [(c.category, c.count) for c in app.query(CategoryRow)]
        assert cats == [("Todas", 3), ("Herramientas", 1), ("IA", 1), ("Juegos", 1)]

        await pilot.press("slash")
        assert app.focused is app.query_one("#search", Input)
        await pilot.press(*"oll")
        await pilot.pause()
        assert rows(app) == ["ollama"]
        await pilot.press("escape")
        assert app.focused is app.query_one("#apps", ListView)

        app.query_one("#search", Input).value = ""
        await pilot.pause()
        categories = app.query_one("#categories", ListView)
        categories.focus()
        await pilot.press("down", "down", "down")  # Juegos
        await pilot.pause()
        assert app.category == "Juegos"
        assert rows(app) == ["beta"]


async def test_cancel_params_does_nothing(config: Config) -> None:
    app = AppForgeApp(config)
    async with app.run_test(size=SIZE) as pilot:
        await settle(app, pilot)
        await pilot.press("i")
        await wait_for(pilot, lambda: isinstance(app.screen, ParamsScreen))
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, (ParamsScreen, ProgressScreen))


async def test_repaint_before_rows_are_composed(home: Path, demo: Path) -> None:
    """Regresión: repintar justo tras reconstruir la lista reventaba (NoMatches).

    Pasaba al borrar en el buscador mientras terminaba un ``[check]``.
    """
    config = with_ui(home, search=True)
    app = AppForgeApp(config)
    async with app.run_test(size=SIZE) as pilot:
        await settle(app, pilot)
        app.search_text = "al"
        app._fill_apps()  # filas nuevas, aún sin componer
        app._repaint()  # lo que hace _set_state al terminar un check
        await pilot.pause()
        assert rows(app) == ["alpha"]
        assert app.query(AppRow).first().query_one(".tag", Label).visual


async def test_double_click_opens_detail_page(config: Config) -> None:
    app = AppForgeApp(config)
    async with app.run_test(size=SIZE) as pilot:
        await settle(app, pilot)
        row = app.query(AppRow).first()
        await pilot.click(row)
        await pilot.pause()
        assert app.marked == set()  # un clic simple ya no marca
        await pilot.click(row, times=2)
        await wait_for(pilot, lambda: isinstance(app.screen, DetailScreen))
        screen = app.screen
        assert isinstance(screen, DetailScreen)
        assert screen.entry.id == "ollama"
        await pilot.press("escape")
        await wait_for(pilot, lambda: not isinstance(app.screen, DetailScreen))
        await pilot.press("v")
        await wait_for(pilot, lambda: isinstance(app.screen, DetailScreen))


def test_entry_markdown_lists_everything(config: Config) -> None:
    from appforge.entry import load_entries

    entries, _ = load_entries(config.entries_dir)
    md = entry_markdown(entries[0], False)
    assert md.startswith("# Ollama (bajo demanda)")
    assert "### Ajustes de rendimiento" in md  # clave details
    assert "| `owner` | Usuario que ejecutará Ollama" in md
    assert "**4. Variables de entorno (optimización)** · `template`" in md
    assert "Genera `/opt/ollama/ollama.env` desde `ollama/ollama.env.tpl`" in md
    assert "## Comprobación" in md
    assert "| no aplicada | IA | sí | `ollama.toml` |" in md
