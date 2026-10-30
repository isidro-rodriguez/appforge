"""La entrada de Neovim (siempre en dry-run)."""

from pathlib import Path

from appforge.engine import Engine
from appforge.entry import load_entries


def nvim(config):
    entries, _ = load_entries(config.entries_dirs[0])
    return next(e for e in entries if e.id == "nvim")


def test_entry_is_valid(config) -> None:
    e = nvim(config)
    assert e.problems == []
    assert [p.name for p in e.params] == ["version", "ts_version", "arch"]
    assert e.params[0].link == "https://github.com/neovim/neovim/releases"
    assert e.params[1].link == "https://github.com/tree-sitter/tree-sitter/releases"
    kinds = [s.kind for s in e.steps]
    assert kinds == ["run", "script", "copy", "copy", "script"] + ["copy"] * 9 + [
        "script",
        "script",
    ]
    copies = [s for s in e.steps if s.kind == "copy"]
    assert all(s.dest.startswith("/opt/nvim/") for s in copies)
    assert copies[0].mode == 0o755 and copies[1].mode == 0o755  # view, vimdiff


def test_check_reports_not_applied(config, sink) -> None:
    assert Engine(config, sink).is_applied(nvim(config)) is False


def test_dry_run_installs_nvim_and_config(config, sink) -> None:
    e = nvim(config)
    engine = Engine(config, sink)
    assert engine.apply(e, {"version": "v0.12.6"}, dry_run=True), sink.text()
    out = sink.text()
    assert "install-nvim.sh" in out and "alternatives.sh" in out
    assert "apt-get install -y" in out and "fd-find" in out
    assert "crear /opt/nvim/libexec/view" in out
    assert "crear /opt/nvim/libexec/vimdiff (modo 0755" in out
    assert "crear /opt/nvim/appforge/config/lua/appforge/plugins.lua" in out
    assert "crear /opt/nvim/appforge/config/nvim-pack-lock.json" in out
    assert "user-config.sh" in out and "bootstrap.sh" in out
    assert "Dry-run completado" in out
    assert not Path("/opt/nvim/appforge").exists()


def test_remove_restores_alternatives(config, sink) -> None:
    e = nvim(config)
    assert Engine(config, sink).remove(e, dry_run=True), sink.text()
    out = sink.text()
    assert "update-alternatives --remove" in out
    assert "rm -rf /opt/nvim" in out
    assert ".config" not in out.replace("Conserva ~/.config/nvim", "")
