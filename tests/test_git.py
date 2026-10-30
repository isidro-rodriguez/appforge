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
        ("aliases", "yes"),
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


def git_aliases(config) -> dict[str, str]:
    conf = config.entries_dirs[0] / "git" / "aliases.conf"
    lines = [
        ln for ln in conf.read_text().splitlines() if ln and not ln.startswith("#")
    ]
    return dict(ln.split(" ", 1) for ln in lines)


@pytest.mark.skipif(not shutil.which("git"), reason="git no instalado")
def test_aliases_do_not_hide_git_commands(config) -> None:
    r = subprocess.run(
        ["git", "--list-cmds=builtins,main,others"], capture_output=True, text=True
    )
    commands = set(r.stdout.split())
    assert "status" in commands
    assert not commands & set(git_aliases(config))


@pytest.mark.skipif(not shutil.which("git"), reason="git no instalado")
def test_bundle_pull_alias(config, tmp_path: Path) -> None:
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "u",
        "GIT_AUTHOR_EMAIL": "u@example.com",
        "GIT_COMMITTER_NAME": "u",
        "GIT_COMMITTER_EMAIL": "u@example.com",
    }

    def sh(*args: str, cwd: Path = tmp_path) -> None:
        subprocess.run(args, cwd=cwd, env=env, check=True, capture_output=True)

    for name, value in git_aliases(config).items():
        sh("git", "config", "--global", f"alias.{name}", value)
    src, dst = tmp_path / "src", tmp_path / "dst"
    sh("git", "init", "-q", "-b", "main", str(src))
    (src / "a").write_text("1\n")
    sh("git", "a", "a", cwd=src)
    sh("git", "c", "-qm", "uno", cwd=src)
    sh("git", "clone", "-q", str(src), str(dst))
    (src / "a").write_text("2\n")
    sh("git", "c", "-qam", "dos", cwd=src)
    sh("git", "bc", str(tmp_path / "x.bundle"), "main", cwd=src)
    sh("git", "bundle-pull", str(tmp_path / "x.bundle"), cwd=dst)
    assert (dst / "a").read_text() == "2\n"
