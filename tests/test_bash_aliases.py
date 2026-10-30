"""La entrada de alias de bash (dry-run y el script con un HOME temporal)."""

import os
import subprocess
from pathlib import Path

import pytest

from appforge.engine import Engine
from appforge.entry import load_entries


def bash_aliases(config):
    entries, _ = load_entries(config.entries_dirs[0])
    return next(e for e in entries if e.id == "bash-aliases")


def test_entry_is_valid(config) -> None:
    e = bash_aliases(config)
    assert e.problems == []
    assert [(p.name, p.default) for p in e.params] == [
        ("eza", "yes"),
        ("eza_icons", "no"),
    ]
    assert [s.kind for s in e.steps] == ["script"]


@pytest.mark.parametrize("fragment", ["base.sh", "eza.sh", "eza-icons.sh"])
def test_fragments_are_valid_bash(config, fragment) -> None:
    path = config.entries_dirs[0] / "bash-aliases" / fragment
    r = subprocess.run(
        ["bash", "-c", f"shopt -s expand_aliases; eza() {{ :; }}; . {path}; alias"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    if fragment == "base.sh":
        assert "alias cp='cp -i'" in r.stdout
    else:
        assert "alias ls='eza " in r.stdout
        assert ("--icons=auto" in r.stdout) == (fragment == "eza-icons.sh")


def test_eza_fragment_is_inert_without_eza(config) -> None:
    path = config.entries_dirs[0] / "bash-aliases" / "eza.sh"
    r = subprocess.run(
        ["bash", "-c", f"PATH=/nonexistent; . {path}; alias"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0 and r.stdout == ""


def test_dry_run(config, sink) -> None:
    e = bash_aliases(config)
    engine = Engine(config, sink)
    assert engine.apply(e, {}, dry_run=True), sink.text()
    assert "install-aliases.sh" in sink.text()
    assert engine.remove(e, dry_run=True)
    assert 'mv -f "$dest.backup" "$dest"' in sink.text()


def run(home: Path, user_home: Path, code: str, **params: str):
    env = {
        **os.environ,
        "APPFORGE_USER": subprocess.run(
            ["id", "-un"], capture_output=True, text=True
        ).stdout.strip(),
        "APPFORGE_USER_HOME": str(user_home),
        "APPFORGE_ENTRY_DIR": str(home / "entries" / "bash-aliases"),
        **params,
    }
    return subprocess.run(["bash", "-c", code], env=env, capture_output=True, text=True)


def install(home: Path, user_home: Path, eza_icons: str = "no", eza: str = "no"):
    # eza=no por defecto: el test no puede instalar paquetes.
    script = home / "entries" / "bash-aliases" / "install-aliases.sh"
    return run(home, user_home, f"bash {script}", eza=eza, eza_icons=eza_icons)


@pytest.fixture
def user_home(tmp_path: Path) -> Path:
    path = tmp_path / "home"
    path.mkdir()
    (path / ".bashrc").write_text("[ -f ~/.bash_aliases ] && . ~/.bash_aliases\n")
    return path


def test_install_backs_up_and_remove_restores(config, home, user_home) -> None:
    e = bash_aliases(config)
    src = home / "entries" / "bash-aliases"
    (user_home / ".bash_aliases").write_text("alias propio='true'\n")
    own = user_home / ".bash_aliases.d" / "own.sh"
    own.parent.mkdir()
    own.write_text("alias mio='true'\n")

    r = install(home, user_home)
    assert r.returncode == 0, r.stderr
    assert r.stderr == ""  # .bashrc lo carga: sin aviso
    assert (user_home / ".bash_aliases").read_text() == (
        src / "bash_aliases"
    ).read_text()
    base = user_home / ".bash_aliases.d" / "base.sh"
    assert base.read_text() == (src / "base.sh").read_text()
    assert oct(base.stat().st_mode & 0o777) == "0o644"
    assert not (user_home / ".bash_aliases.d" / "eza.sh").exists()
    assert (user_home / ".bash_aliases.backup").read_text() == "alias propio='true'\n"
    assert run(home, user_home, e.check).returncode == 0

    # El cargador lee base.sh y los fragmentos propios.
    r = subprocess.run(
        ["bash", "-c", f"shopt -s expand_aliases; . {user_home}/.bash_aliases; alias"],
        env={**os.environ, "HOME": str(user_home)},
        capture_output=True,
        text=True,
    )
    assert "alias mio='true'" in r.stdout and "alias du1=" in r.stdout

    assert run(home, user_home, e.remove).returncode == 0
    assert (user_home / ".bash_aliases").read_text() == "alias propio='true'\n"
    assert not base.exists()
    assert own.exists()
    assert run(home, user_home, e.check).returncode != 0


def test_eza_fragment_variants_pass_check(config, home, user_home) -> None:
    e = bash_aliases(config)
    src = home / "entries" / "bash-aliases"
    assert install(home, user_home).returncode == 0
    fragment = user_home / ".bash_aliases.d" / "eza.sh"
    for variant in ("eza.sh", "eza-icons.sh"):
        fragment.write_text((src / variant).read_text())
        assert run(home, user_home, e.check).returncode == 0
    fragment.write_text("editado\n")
    assert run(home, user_home, e.check).returncode != 0

    r = run(home, user_home, e.remove)
    assert "eza.sh se ha modificado" in r.stderr
    assert fragment.read_text() == "editado\n"


def test_remove_keeps_edited_file(config, home, tmp_path) -> None:
    e = bash_aliases(config)
    (tmp_path / ".bash_aliases").write_text("editado\n")
    r = run(home, tmp_path, e.remove)
    assert r.returncode == 0 and "no se toca" in r.stderr
    assert (tmp_path / ".bash_aliases").read_text() == "editado\n"


def test_invalid_bool_stops(home, user_home) -> None:
    r = install(home, user_home, eza_icons="quizá")
    assert r.returncode == 1 and "no válido" in r.stderr
    assert not (user_home / ".bash_aliases").exists()


def test_warns_when_bashrc_does_not_load_it(home, tmp_path) -> None:
    r = install(home, tmp_path)
    assert r.returncode == 0
    assert "no carga ~/.bash_aliases" in r.stderr
