"""La entrada de Ollama como caso de prueba real."""

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

from appforge.engine import Engine, EngineError, resolve_values
from appforge.entry import load_entries

VALUES = {"owner": "usuario"}


def ollama(config):
    entries, _ = load_entries(config.entries_dir)
    return next(e for e in entries if e.id == "ollama")


def test_entry_is_valid(config):
    e = ollama(config)
    assert e.problems == []
    assert e.requires_root
    assert [p.name for p in e.params] == [
        "owner",
        "arch",
        "host",
        "keep_alive",
        "kv_cache",
        "context_length",
    ]
    assert [s.kind for s in e.steps] == [
        "run",
        "run",
        "run",
        "template",
        "copy",
        "copy",
        "copy",
    ]
    assert e.steps[3].dest == "/opt/ollama/ollama.env" and e.steps[3].mode == 0o644
    assert e.steps[4].mode == 0o755


def test_missing_icon_is_reported(config):
    (config.entries_dir / "ollama" / "ollama.png").unlink()
    e = ollama(config)
    assert any("ollama.png" in p for p in e.problems)


def test_owner_is_required(config):
    with pytest.raises(EngineError, match="owner"):
        resolve_values(ollama(config), {})


def test_dry_run_renders_env_and_changes_nothing(config, sink):
    e = ollama(config)
    ok = Engine(config, sink).apply(e, {**VALUES, "kv_cache": "q4_0"}, dry_run=True)
    assert ok, sink.text()
    out = sink.text()
    assert "[1/7] Dependencias" in out and "[dry-run]" in out
    assert "# DEBIAN_FRONTEND=noninteractive apt-get install" in out  # '#' = con root
    assert "+OLLAMA_MODELS=/opt/ollama/models" in out
    assert "+OLLAMA_KV_CACHE_TYPE=q4_0" in out  # valor dado
    assert "+OLLAMA_KEEP_ALIVE=30m" in out  # default
    assert "crear /usr/local/share/applications/ollama.desktop" in out
    assert "Dry-run completado" in out
    assert not Path("/opt/ollama/ollama.env").exists()


def test_check_reports_not_applied(config):
    if Path("/opt/ollama/bin/ollama").exists():
        pytest.skip("Ollama instalado en esta máquina")
    assert Engine(config, lambda *_: None).is_applied(ollama(config)) is False


def test_remove_dry_run_keeps_models(config, sink):
    assert Engine(config, sink).remove(ollama(config), dry_run=True)
    out = sink.text()
    assert "rm -rf /opt/ollama/bin /opt/ollama/lib" in out
    assert "/opt/ollama/models" not in out.replace(
        "rm -rf /opt/ollama/bin /opt/ollama/lib", ""
    )


# --------------------------------------------------------------------------- #
# Switcher on/off con un ollama y un notify-send falsos
# --------------------------------------------------------------------------- #
def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def fake_install(tmp_path, home):
    base = tmp_path / "opt-ollama"
    (base / "bin").mkdir(parents=True)
    api = tmp_path / "www" / "api"
    api.mkdir(parents=True)
    (api / "version").write_text('{"version":"fake"}')
    port = free_port()
    fake = base / "bin" / "ollama"
    fake.write_text(f"""#!/usr/bin/env bash
[ "$1" = serve ] || exit 2
python3 -m http.server --bind 127.0.0.1 {port} --directory {tmp_path / "www"} &
child=$!
trap 'kill $child; exit 0' TERM INT
wait $child
""")
    fake.chmod(0o755)
    (base / "ollama.env").write_text(
        f"OLLAMA_HOST=127.0.0.1:{port}\nOLLAMA_MODELS={base}/models\n"
    )
    shutil.copy(
        home / "entries" / "ollama" / "ollama-toggle.sh", base / "ollama-toggle.sh"
    )

    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    log = tmp_path / "notify.log"
    (fakebin / "notify-send").write_text(f'#!/bin/sh\necho "$@" >> {log}\n')
    (fakebin / "notify-send").chmod(0o755)
    env = {
        **os.environ,
        "OLLAMA_BASE": str(base),
        "PATH": f"{fakebin}:{os.environ['PATH']}",
        "XDG_STATE_HOME": str(tmp_path / "state"),
        "USER": os.environ.get("USER", "root"),
    }
    env["USER"] = subprocess.run(
        ["id", "-un"], capture_output=True, text=True
    ).stdout.strip()
    yield base, env, log, port
    subprocess.run(["pkill", "-f", f"{base}/bin/ollama serve"])


def test_toggle_on_then_off(fake_install):
    base, env, log, port = fake_install
    toggle = [str(base / "ollama-toggle.sh")]

    r = subprocess.run(toggle, env=env, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    notes = log.read_text()
    assert (
        "Arrancando servicio" in notes
        and f"Servicio activo en 127.0.0.1:{port}" in notes
    )
    assert subprocess.run(["pgrep", "-f", f"{base}/bin/ollama serve"]).returncode == 0

    r = subprocess.run(toggle, env=env, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    assert "Servicio detenido" in log.read_text()
    time.sleep(0.5)
    assert subprocess.run(["pgrep", "-f", f"{base}/bin/ollama serve"]).returncode != 0


def test_dry_run_is_logged(config, sink) -> None:
    from appforge.runlog import RunLog

    entries, _ = load_entries(config.entries_dir)
    entry = next(e for e in entries if e.id == "ollama")
    engine = Engine(config, RunLog(config).tee(sink, "ollama: "))
    assert engine.apply(entry, VALUES, dry_run=True)
    log = (config.logs_dir / "appforge.log").read_text(encoding="utf-8")
    assert "ollama: [1/7] Dependencias" in log
    assert "Dry-run completado" in log
