"""La entrada del cortafuegos (dry-run y validación de excepciones con un ufw falso)."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from appforge.engine import Engine
from appforge.entry import load_entries


def firewall(config):
    entries, _ = load_entries(config.entries_dirs[0])
    return next(e for e in entries if e.id == "firewall")


def test_entry_is_valid(config) -> None:
    e = firewall(config)
    assert e.problems == []
    assert [p.name for p in e.params] == ["allow", "allow_from"]
    assert all(p.default == "-" for p in e.params)
    assert [s.kind for s in e.steps] == ["run", "script"]


def test_check_reports_not_applied(config) -> None:
    if shutil.which("ufw"):
        pytest.skip("ufw instalado en esta máquina")
    assert Engine(config, lambda *_: None).is_applied(firewall(config)) is False


def test_dry_run_and_remove(config, sink) -> None:
    e = firewall(config)
    engine = Engine(config, sink)
    assert engine.apply(e, {"allow": "22/tcp 443"}, dry_run=True), sink.text()
    out = sink.text()
    assert "# DEBIAN_FRONTEND=noninteractive apt-get install -y ufw" in out
    assert "configure-ufw.sh" in out
    assert engine.remove(e, dry_run=True)
    assert "ufw disable" in sink.text()


@pytest.fixture
def fake_ufw(tmp_path: Path):
    """``ufw`` falso que anota sus argumentos en ``ufw.log``."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "ufw.log"
    (bin_dir / "ufw").write_text(f'#!/bin/sh\necho "$*" >> {log}\n')
    (bin_dir / "ufw").chmod(0o755)
    return bin_dir, log


def configure(home: Path, fake_ufw, allow: str, allow_from: str = "-"):
    bin_dir, _ = fake_ufw
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "allow": allow,
        "allow_from": allow_from,
    }
    script = home / "entries" / "firewall" / "configure-ufw.sh"
    return subprocess.run(
        ["bash", str(script)], env=env, capture_output=True, text=True
    )


def test_valid_rules_are_applied_after_validation(home, fake_ufw) -> None:
    r = configure(home, fake_ufw, "22/tcp 443 60000:61000/udp ssh", "192.168.1.0/24")
    assert r.returncode == 0, r.stderr
    calls = fake_ufw[1].read_text().splitlines()
    first_change = calls.index("default deny incoming")
    assert all("--dry-run" in c for c in calls[:first_change])
    assert calls[first_change:] == [
        "default deny incoming",
        "default allow outgoing",
        "allow 22/tcp",
        "allow 443",
        "allow 60000:61000/udp",
        "allow ssh",
        "allow from 192.168.1.0/24",
        "--force enable",
        "status verbose",
    ]


def test_dash_means_no_rules(home, fake_ufw) -> None:
    r = configure(home, fake_ufw, "-", "-")
    assert r.returncode == 0, r.stderr
    calls = fake_ufw[1].read_text().splitlines()
    assert not [c for c in calls if c.startswith("allow")]
    assert "--force enable" in calls


@pytest.mark.parametrize(
    ("allow", "allow_from"),
    [
        ("22/tcp 70000", "-"),
        ("60000:61000", "-"),  # rango sin protocolo
        ("22/sctp", "-"),
        ("22;reboot", "-"),
        ("no-such-service", "-"),
        ("-", "10.0.0.0/8; reboot"),
    ],
)
def test_invalid_rule_changes_nothing(home, fake_ufw, allow, allow_from) -> None:
    r = configure(home, fake_ufw, allow, allow_from)
    assert r.returncode == 1
    assert "no válida" in r.stderr
    log = fake_ufw[1]
    calls = log.read_text().splitlines() if log.exists() else []
    assert all("--dry-run" in c for c in calls)
