"""La entrada de alias de bash (dry-run y el script con un HOME temporal)."""

import os
import subprocess
from pathlib import Path

from appforge.engine import Engine
from appforge.entry import load_entries


def bash_aliases(config):
    entries, _ = load_entries(config.entries_dirs[0])
    return next(e for e in entries if e.id == "bash-aliases")


def test_entry_is_valid(config) -> None:
    e = bash_aliases(config)
    assert e.problems == []
    assert e.params == []
    assert [s.kind for s in e.steps] == ["script"]


def test_aliases_are_valid_bash(config) -> None:
    aliases = config.entries_dirs[0] / "bash-aliases" / "bash_aliases"
    r = subprocess.run(
        ["bash", "-c", f"shopt -s expand_aliases; . {aliases}; alias ll cp grep"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    assert "alias cp='cp -i'" in r.stdout


def test_dry_run(config, sink) -> None:
    e = bash_aliases(config)
    engine = Engine(config, sink)
    assert engine.apply(e, {}, dry_run=True), sink.text()
    assert "install-aliases.sh" in sink.text()
    assert engine.remove(e, dry_run=True)
    assert 'mv -f "$dest.backup" "$dest"' in sink.text()


def run(home: Path, user_home: Path, code: str):
    env = {
        **os.environ,
        "APPFORGE_USER": subprocess.run(
            ["id", "-un"], capture_output=True, text=True
        ).stdout.strip(),
        "APPFORGE_USER_HOME": str(user_home),
        "APPFORGE_ENTRY_DIR": str(home / "entries" / "bash-aliases"),
    }
    return subprocess.run(["bash", "-c", code], env=env, capture_output=True, text=True)


def test_install_backs_up_and_remove_restores(config, home, tmp_path) -> None:
    e = bash_aliases(config)
    user_home = tmp_path / "home"
    user_home.mkdir()
    (user_home / ".bashrc").write_text("[ -f ~/.bash_aliases ] && . ~/.bash_aliases\n")
    (user_home / ".bash_aliases").write_text("alias propio='true'\n")
    script = home / "entries" / "bash-aliases" / "install-aliases.sh"

    r = run(home, user_home, f"bash {script}")
    assert r.returncode == 0, r.stderr
    assert r.stderr == ""  # .bashrc lo carga: sin aviso
    installed = (user_home / ".bash_aliases").read_text()
    assert installed == (home / "entries" / "bash-aliases" / "bash_aliases").read_text()
    assert oct((user_home / ".bash_aliases").stat().st_mode & 0o777) == "0o644"
    assert (user_home / ".bash_aliases.backup").read_text() == "alias propio='true'\n"
    assert run(home, user_home, e.check).returncode == 0

    assert run(home, user_home, e.remove).returncode == 0
    assert (user_home / ".bash_aliases").read_text() == "alias propio='true'\n"
    assert run(home, user_home, e.check).returncode != 0


def test_remove_keeps_edited_file(config, home, tmp_path) -> None:
    e = bash_aliases(config)
    (tmp_path / ".bash_aliases").write_text("editado\n")
    r = run(home, tmp_path, e.remove)
    assert r.returncode == 0 and "no se toca" in r.stderr
    assert (tmp_path / ".bash_aliases").read_text() == "editado\n"


def test_warns_when_bashrc_does_not_load_it(home, tmp_path) -> None:
    script = home / "entries" / "bash-aliases" / "install-aliases.sh"
    r = run(home, tmp_path, f"bash {script}")
    assert r.returncode == 0
    assert "no carga ~/.bash_aliases" in r.stderr
