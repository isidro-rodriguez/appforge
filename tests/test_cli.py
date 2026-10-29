"""CLI: ``validate``, ``--version`` y arranque de la TUI."""

import subprocess
import sys
from pathlib import Path

import pytest

from appforge import __version__
from appforge.main import main
from appforge.validate import validate_dir

GOOD = """
name = "Buena"
description = "Escribe un fichero"
[[param]]
name = "who"
default = "mundo"
[check]
run = "test -f /tmp/x"
[[step]]
template = "hola.tpl"
dest = "/tmp/x"
[remove]
run = "rm -f /tmp/x"
"""


def test_repo_entries_are_valid(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", "--strict"]) == 0
    out = capsys.readouterr().out
    assert "ollama" in out
    assert "errores: 0 · avisos: 0" in out


def test_good_entry(write_entry, config) -> None:
    write_entry("buena", GOOD, {"hola.tpl": "hola $who\n"})
    report = next(
        r for r in validate_dir(config.entries_dir).reports if r.entry.id == "buena"
    )
    assert report.errors == []
    assert report.warnings == []


def test_missing_files_and_bad_syntax(write_entry, config) -> None:
    write_entry(
        "rota",
        """
name = "Rota"
[check]
run = "test -f $APPFORGE_ENTRY_DIR/marca"
[[step]]
copy = "no-existe.conf"
dest = "/tmp/y"
[[step]]
run = "if true; then echo"
[[step]]
script = "s.sh"
[remove]
run = "bash ${APPFORGE_ENTRY_DIR}/borra.sh"
""",
        {"s.sh": "for x in; do\n", "borra.sh": "true\n"},
    )
    result = validate_dir(config.entries_dir)
    errors = "\n".join(next(r for r in result.reports if r.entry.id == "rota").errors)
    assert "falta el fichero rota/no-existe.conf" in errors
    assert "step #2: error de sintaxis" in errors
    assert "s.sh: error de sintaxis" in errors
    assert "pero no existe rota/marca" in errors
    assert "borra.sh" not in errors  # existe


def test_warnings(write_entry, config) -> None:
    write_entry(
        "floja",
        """
name = "Ollama (bajo demanda)"
[[param]]
name = "nadie"
default = "x"
[[step]]
run = "true"
""",
        {"sobra.txt": "x"},
    )
    (config.entries_dir / "huerfano").mkdir()
    result = validate_dir(config.entries_dir)
    warnings = "\n".join(
        next(r for r in result.reports if r.entry.id == "floja").warnings
    )
    assert "fichero sin usar: floja/sobra.txt" in warnings
    assert "parámetro sin usar: nadie" in warnings
    assert "sin [check]" in warnings
    assert "sin [remove]" in warnings
    assert "sin 'description'" in warnings
    general = "\n".join(result.warnings)
    assert "huerfano/: subdirectorio sin huerfano.toml" in general
    assert "nombre repetido" in general


def test_exit_codes(write_entry, capsys: pytest.CaptureFixture[str]) -> None:
    write_entry("floja", 'name = "Floja"\n[[step]]\nrun = "true"\n')
    assert main(["validate"]) == 0  # solo avisos
    assert main(["validate", "--strict"]) == 1
    assert main(["validate", "ollama", "--strict"]) == 0  # filtra por id
    assert main(["validate", "nada"]) == 2
    assert "no existe la entrada: nada" in capsys.readouterr().err
    write_entry("mala", 'name = "Mala"\n')
    assert main(["validate"]) == 1


def test_validate_other_dir(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = tmp_path / "otras"
    folder.mkdir(mode=0o755)
    assert main(["validate", "--dir", str(folder)]) == 0
    assert "no hay ninguna entrada" in capsys.readouterr().out


def test_bad_config_exits_2(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (home / "config.toml").write_text('entries_dir = "entries"\n[ui]\nsearch = 1\n')
    assert main(["validate"]) == 2
    assert "[ui].search" in capsys.readouterr().err


def test_no_command_without_terminal(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("TERM", "dumb")
    assert main([]) == 2
    assert "necesita una terminal" in capsys.readouterr().out


def test_help_is_spanish(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--help"]) == 0
    out = capsys.readouterr().out
    assert "Uso:" in out
    assert "validate" in out
    assert "apply" not in out


def test_version_and_module_entry_point(home: Path) -> None:
    r = subprocess.run(
        [sys.executable, "-m", "appforge", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert __version__ in r.stdout
