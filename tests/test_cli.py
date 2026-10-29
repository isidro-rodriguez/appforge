"""CLI de extremo a extremo con la entrada Ollama (siempre en dry-run)."""

import subprocess
import sys
from pathlib import Path

import pytest

from appforge import __version__
from appforge.main import main


def test_list_and_dry_run(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "ollama" in out
    assert "IA" in out  # categoría
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
    assert "+OLLAMA_HOST=0.0.0.0:11434" in out
    assert "Dry-run completado" in out


def test_apply_writes_run_log(home: Path, config, capsys) -> None:
    assert main(["apply", "ollama", "-n", "--no-input", "-s", "owner=isidro"]) == 0
    log = (config.logs_dir / "appforge.log").read_text(encoding="utf-8")
    assert "ollama: [1/7] Dependencias" in log
    assert "Dry-run completado" in log


def test_missing_param_fails(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["apply", "ollama", "-n", "--no-input"]) == 1
    assert "Faltan parámetros: owner" in capsys.readouterr().err


def test_show_check_remove(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["show", "ollama"]) == 0
    out = capsys.readouterr().out
    assert "OLLAMA_HOST" in out
    assert "categoría: IA" in out
    if not Path("/opt/ollama/bin/ollama").exists():
        assert main(["check", "ollama"]) == 1
    assert main(["remove", "ollama", "-n"]) == 0
    assert "Dry-run completado" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="No existe la entrada"):
        main(["show", "nada"])
    with pytest.raises(SystemExit, match="nombre=valor"):
        main(["apply", "ollama", "-n", "--no-input", "-s", "owner"])


def test_bad_config_exits_2(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (home / "config.toml").write_text('entries_dir = "entries"\n[ui]\nsearch = 1\n')
    assert main(["list"]) == 2
    assert "[ui].search" in capsys.readouterr().err


def test_version_and_module_entry_point(home: Path) -> None:
    r = subprocess.run(
        [sys.executable, "-m", "appforge", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert __version__ in r.stdout
