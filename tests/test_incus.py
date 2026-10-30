"""La entrada de Incus (siempre en dry-run)."""

import shutil

import pytest

from appforge.engine import Engine
from appforge.entry import load_entries


def incus(config):
    entries, _ = load_entries(config.entries_dirs[0])
    return next(e for e in entries if e.id == "incus")


def test_entry_is_valid(config) -> None:
    e = incus(config)
    assert e.problems == []
    assert [(p.name, p.default) for p in e.params] == [("vms", "yes")]
    assert [s.kind for s in e.steps] == ["script", "run", "run", "script"]


def test_check_reports_not_applied(config) -> None:
    if shutil.which("incus"):
        pytest.skip("Incus instalado en esta máquina")
    assert Engine(config, lambda *_: None).is_applied(incus(config)) is False


def test_dry_run_and_remove(config, sink) -> None:
    e = incus(config)
    engine = Engine(config, sink)
    assert engine.apply(e, {}, dry_run=True), sink.text()
    out = sink.text()
    assert "install-incus.sh" in out
    assert "#   incus admin init --minimal" in out
    assert '#   usermod -aG incus-admin "$APPFORGE_USER"' in out
    assert "ufw-rules.sh" in out
    rules = (config.entries_dirs[0] / "incus" / "ufw-rules.sh").read_text()
    for rule in (
        "ufw allow in on incusbr0",
        "ufw route allow in on incusbr0",
        "ufw route allow out on incusbr0",
    ):
        assert rule in rules
    assert engine.remove(e, dry_run=True)
    out = sink.text()
    assert "ufw route delete allow out on incusbr0" in out
    assert 'gpasswd -d "$APPFORGE_USER" incus-admin' in out
    assert "storage" not in out.split("Eliminar")[-1]
