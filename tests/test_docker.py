"""La entrada de Docker (siempre en dry-run)."""

import shutil

import pytest

from appforge.engine import Engine
from appforge.entry import load_entries

PACKAGES = (
    "docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"
)


def docker(config):
    entries, _ = load_entries(config.entries_dirs[0])
    return next(e for e in entries if e.id == "docker")


def test_entry_is_valid(config) -> None:
    e = docker(config)
    assert e.problems == []
    assert e.params == []
    assert [s.kind for s in e.steps] == ["run", "script", "copy", "run", "run"]
    assert e.steps[2].dest == "/etc/apt/sources.list.d/docker.sources"


def test_check_reports_not_applied(config) -> None:
    if shutil.which("docker"):
        pytest.skip("Docker instalado en esta máquina")
    assert Engine(config, lambda *_: None).is_applied(docker(config)) is False


def test_repo_is_signed_by_its_own_key(config) -> None:
    folder = config.entries_dirs[0] / "docker"
    sources = (folder / "docker.sources").read_text()
    assert "Signed-By: /etc/apt/keyrings/docker.asc" in sources
    assert "Suites: trixie" in sources
    key_script = (folder / "apt-key.sh").read_text()
    assert "9DC858229FC7DD38854AE2D88D81803C0EBFCD88" in key_script
    assert "KEYRING=/etc/apt/keyrings/docker.asc" in key_script


def test_dry_run_and_remove_keeps_data(config, sink) -> None:
    e = docker(config)
    engine = Engine(config, sink)
    assert engine.apply(e, {}, dry_run=True), sink.text()
    out = sink.text()
    assert "crear /etc/apt/sources.list.d/docker.sources" in out
    assert "apt-get install -y " + PACKAGES + "\n" in out
    assert '#   usermod -aG docker "$APPFORGE_USER"' in out
    assert engine.remove(e, dry_run=True)
    removal = sink.text().split("Eliminar")[-1]
    assert "/etc/apt/keyrings/docker.asc" in removal
    assert "/var/lib/docker" not in removal
