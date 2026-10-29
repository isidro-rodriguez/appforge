"""La entrada de ejemplo git-alias, aplicada de verdad en un HOME temporal."""

import shutil
import subprocess
from pathlib import Path

import pytest

from appforge.engine import Engine
from appforge.entry import load_entries

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="sin git")


def test_apply_check_remove(config, sink, tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "casa"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("GIT_CONFIG_GLOBAL", raising=False)
    entries, _ = load_entries(config.entries_dir)
    entry = next(e for e in entries if e.id == "git-alias")
    engine = Engine(config, sink)
    values = {"file": "~/.config/git/appforge-aliases"}

    assert engine.is_applied(entry) is False
    assert engine.apply(entry, values), sink.text()
    assert engine.is_applied(entry) is True
    alias = subprocess.run(
        ["git", "config", "--includes", "--global", "alias.st"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert alias.stdout.strip() == "status -sb"
    assert engine.apply(entry, values)  # idempotente: no duplica el include
    gitconfig = (home / ".gitconfig").read_text(encoding="utf-8")
    assert gitconfig.count("appforge-aliases") == 1

    assert engine.remove(entry), sink.text()
    assert engine.is_applied(entry) is False
    assert not (home / ".config" / "git" / "appforge-aliases").exists()
