"""La entrada de git y GitHub CLI (dry-run y validación de parámetros)."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from appforge.engine import Engine
from appforge.entry import load_entries

VALUES = {"user_name": "Usuario", "user_email": "usuario@example.com"}


def git(config):
    entries, _ = load_entries(config.entries_dirs[0])
    return next(e for e in entries if e.id == "git")


def test_entry_is_valid(config) -> None:
    e = git(config)
    assert e.problems == []
    assert [(p.name, p.default) for p in e.params] == [
        ("user_name", None),
        ("user_email", None),
        ("default_branch", "main"),
        ("editor", "-"),
    ]
    assert [s.kind for s in e.steps] == ["run", "script", "copy", "run", "script"]


def test_check_reports_not_applied(config) -> None:
    if shutil.which("gh"):
        pytest.skip("GitHub CLI instalado en esta máquina")
    assert Engine(config, lambda *_: None).is_applied(git(config)) is False


def test_repo_and_key_rotation(config) -> None:
    folder = config.entries_dirs[0] / "git"
    sources = (folder / "github-cli.sources").read_text()
    assert "URIs: https://cli.github.com/packages" in sources
    assert "Signed-By: /etc/apt/keyrings/githubcli-archive-keyring.gpg" in sources
    key_script = (folder / "apt-key.sh").read_text()
    assert "REQUIRED=7F38BBB59D064DBCB3D84D725612B36462313325" in key_script


def test_dry_run_and_remove_keeps_gitconfig(config, sink) -> None:
    e = git(config)
    engine = Engine(config, sink)
    assert engine.apply(e, VALUES, dry_run=True), sink.text()
    out = sink.text()
    assert "crear /etc/apt/sources.list.d/github-cli.sources" in out
    assert "apt-get install -y gh" in out
    assert "git-config.sh" in out
    assert engine.remove(e, dry_run=True)
    removal = sink.text().split("Eliminar")[-1]
    assert "apt-get remove -y gh" in removal
    assert ".gitconfig" not in removal


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"user_name": "  "}, "nombre"),
        ({"user_email": "usuario"}, "email no válido"),
        ({"user_email": "usuario@localhost"}, "email no válido"),
        ({"default_branch": "rama..mala"}, "rama no válido"),
    ],
)
def test_invalid_params_stop_before_configuring(home: Path, values, message) -> None:
    env = {
        **os.environ,
        **VALUES,
        "default_branch": "main",
        "editor": "-",
        "APPFORGE_USER": "usuario",
        "APPFORGE_USER_HOME": "/nonexistent",
        **values,
    }
    script = home / "entries" / "git" / "git-config.sh"
    r = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True)
    assert r.returncode == 1
    assert message in r.stderr
