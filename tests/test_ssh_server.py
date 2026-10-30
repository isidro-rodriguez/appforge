"""La entrada del servidor SSH (dry-run y comprobaciones previas)."""

import os
import subprocess
from pathlib import Path

import pytest

from appforge.engine import Engine
from appforge.entry import load_entries

CONF = "/etc/ssh/sshd_config.d/50-appforge.conf"


def ssh_server(config):
    entries, _ = load_entries(config.entries_dirs[0])
    return next(e for e in entries if e.id == "ssh-server")


def test_entry_is_valid(config) -> None:
    e = ssh_server(config)
    assert e.problems == []
    assert [(p.name, p.default) for p in e.params] == [
        ("port", "22"),
        ("password_auth", "no"),
    ]
    assert [s.kind for s in e.steps] == ["script", "run", "template", "script"]
    assert e.steps[2].dest == CONF and e.steps[2].mode == 0o644


def test_check_reports_not_applied(config) -> None:
    if Path(CONF).exists():
        pytest.skip("servidor SSH de AppForge aplicado en esta máquina")
    assert Engine(config, lambda *_: None).is_applied(ssh_server(config)) is False


def test_dry_run_renders_hardening(config, sink) -> None:
    e = ssh_server(config)
    engine = Engine(config, sink)
    ok = engine.apply(e, {"port": "2222", "password_auth": "yes"}, dry_run=True)
    assert ok, sink.text()
    out = sink.text()
    user = engine.user_vars["APPFORGE_USER"]
    for line in (
        "+Port 2222",
        "+PermitRootLogin no",
        "+PasswordAuthentication yes",
        "+KbdInteractiveAuthentication no",
        "+X11Forwarding no",
        "+MaxAuthTries 3",
        f"+AllowUsers {user}",
    ):
        assert line in out
    assert out.index("preflight.sh") < out.index("apt-get install -y openssh-server")
    assert engine.remove(e, dry_run=True)
    assert f"rm -f {CONF}" in sink.text()


def preflight(home: Path, tmp_path: Path, **values: str):
    env = {
        **os.environ,
        "APPFORGE_USER": "usuario",
        "APPFORGE_USER_HOME": str(tmp_path),
        "port": "22",
        "password_auth": "no",
        **values,
    }
    script = home / "entries" / "ssh-server" / "preflight.sh"
    return subprocess.run(
        ["bash", str(script)], env=env, capture_output=True, text=True
    )


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"port": "70000"}, "puerto no válido"),
        ({"password_auth": "quizá"}, "«yes» o «no»"),
        ({"APPFORGE_USER": "root", "password_auth": "yes"}, "sudo desde tu usuario"),
        ({}, "authorized_keys no existe o no tiene claves"),
    ],
)
def test_preflight_stops_before_touching_anything(
    home, tmp_path, values, message
) -> None:
    r = preflight(home, tmp_path, **values)
    assert r.returncode == 1
    assert message in r.stderr


def test_preflight_ignores_comment_only_authorized_keys(home, tmp_path) -> None:
    (tmp_path / ".ssh").mkdir()
    (tmp_path / ".ssh" / "authorized_keys").write_text("# sin claves\n\n")
    r = preflight(home, tmp_path)
    assert r.returncode == 1 and "authorized_keys" in r.stderr
