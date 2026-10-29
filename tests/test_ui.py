"""CLI y TUI de extremo a extremo con la entrada Ollama (siempre en dry-run)."""

from pathlib import Path

from textual.widgets import Input, ListView, RichLog

from appforge.main import main
from appforge.tui import AppForgeApp, EntryItem, RunScreen


def test_cli_list_and_dry_run(home, capsys):
    assert main(["list"]) == 0
    assert "ollama" in capsys.readouterr().out
    rc = main(
        [
            "apply",
            "ollama",
            "-n",
            "--no-input",
            "-s",
            "owner=isidro",
            "-s",
            "host=0.0.0.0:11434",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "+OLLAMA_HOST=0.0.0.0:11434" in out and "Dry-run completado" in out


def test_cli_missing_param_fails(home, capsys):
    assert main(["apply", "ollama", "-n", "--no-input"]) == 1
    assert "Faltan parámetros: owner" in capsys.readouterr().err


async def test_tui_dry_run_flow(config):
    app = AppForgeApp(config)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        await app.workers.wait_for_complete()
        await pilot.pause()
        items = list(app.query(EntryItem))
        assert [i.entry.id for i in items] == ["ollama"]
        assert (
            items[0].state is False and items[0].checked
        )  # check corrido: no aplicada

        await pilot.press("d")  # dry-run → pide parámetros
        await pilot.pause()
        owner = app.screen.query_one("#p_owner", Input)
        owner.value = "isidro"
        await pilot.click("#ok")
        for _ in range(20):
            await pilot.pause(0.05)
            if isinstance(app.screen, RunScreen):
                break
        assert isinstance(app.screen, RunScreen), app.screen
        for _ in range(50):
            await pilot.pause(0.1)
            if not app.screen.running:
                break
        log = app.screen.query_one(RichLog)
        text = "\n".join(line.text for line in log.lines)
        assert "Dry-run completado" in text, text
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen.query_one(ListView), ListView)
    assert not Path("/opt/ollama/ollama.env").exists()


async def test_tui_cancel_params(config):
    app = AppForgeApp(config)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, RunScreen)


def test_version_and_module_entry_point(home) -> None:
    import subprocess
    import sys

    from appforge import __version__

    r = subprocess.run(
        [sys.executable, "-m", "appforge", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert __version__ in r.stdout


def test_cli_show_check_remove(home, capsys) -> None:
    import pytest

    assert main(["show", "ollama"]) == 0
    assert "OLLAMA_HOST" in capsys.readouterr().out
    if not Path("/opt/ollama/bin/ollama").exists():
        assert main(["check", "ollama"]) == 1
    assert main(["remove", "ollama", "-n"]) == 0
    assert "Dry-run completado" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="No existe la entrada"):
        main(["show", "nada"])
    with pytest.raises(SystemExit, match="nombre=valor"):
        main(["apply", "ollama", "-n", "--no-input", "-s", "owner"])
