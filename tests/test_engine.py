"""Motor con entradas que escriben solo en directorios temporales."""

from pathlib import Path

import pytest

from appforge.config import Config
from appforge.engine import MASK, Engine
from appforge.entry import Entry, load_entries

DEMO = """
name = "Demo"
[[param]]
name = "who"
prompt = "Quién"
default = "mundo"
[[param]]
name = "token"
prompt = "Token"
secret = true
[check]
run = "grep -q hola {dest}/saludo.txt && test -f {dest}/bin/tool.sh"
[[step]]
title = "Mostrar"
run = "echo usuario=$who token=$token entry=$APPFORGE_ENTRY"
[[step]]
title = "Saludo"
template = "saludo.tpl"
dest = "{dest}/saludo.txt"
mode = "0600"
[[step]]
title = "Herramienta"
copy = "tool.sh"
dest = "{dest}/bin/tool.sh"
mode = "0755"
{extra}
[remove]
run = "rm -rf {dest}"
"""
DEMO_FILES = {
    "saludo.tpl": "hola $who, cuesta $$5, token=$token\n",
    "tool.sh": "#!/bin/sh\necho hi\n",
}


def get_entry(config: Config, name: str) -> Entry:
    entries, _ = load_entries(config.entries_dir)
    return next(e for e in entries if e.id == name)


@pytest.fixture
def dest(tmp_path: Path) -> Path:
    return tmp_path / "out"


@pytest.fixture
def demo(config, write_entry, dest: Path):
    """Crea la entrada demo; acepta pasos extra y un prefijo de cabecera."""

    def make(extra: str = "", header: str = "") -> Entry:
        write_entry("demo", header + DEMO.format(dest=dest, extra=extra), DEMO_FILES)
        return get_entry(config, "demo")

    return make


def test_apply_check_and_remove(config, sink, demo, dest: Path) -> None:
    e = demo()
    assert e.valid, e.problems
    eng = Engine(config, sink)
    assert eng.is_applied(e) is False

    assert eng.apply(e, {"token": "s3cr3t"}), sink.text()
    assert (dest / "saludo.txt").read_text() == "hola mundo, cuesta $5, token=s3cr3t\n"
    assert (dest / "saludo.txt").stat().st_mode & 0o777 == 0o600
    assert (dest / "bin" / "tool.sh").stat().st_mode & 0o777 == 0o755
    assert "usuario=mundo" in sink.text("out")
    assert "entry=demo" in sink.text("out")
    assert "s3cr3t" not in sink.text()
    assert f"token={MASK}" in sink.text()
    assert "verificada" in sink.text("ok")
    assert eng.is_applied(e) is True

    assert eng.remove(e)
    assert not dest.exists()
    assert eng.is_applied(e) is False


def test_reapply_is_idempotent_and_backs_up(config, sink, demo, dest: Path) -> None:
    e = demo()
    eng = Engine(config, sink)
    assert eng.apply(e, {"token": "a"})
    sink.events.clear()
    assert eng.apply(e, {"token": "a"})
    assert sink.text().count("sin cambios") == 2
    backup = dest / "saludo.txt.backup"
    assert not backup.exists()

    (dest / "saludo.txt").write_text("editado a mano\n")
    (dest / "saludo.txt").chmod(0o600)
    assert eng.apply(e, {"token": "a"})
    assert backup.read_text() == "editado a mano\n"
    assert backup.stat().st_mode & 0o777 == 0o600  # los permisos del original
    assert f"copia de seguridad: {backup}" in sink.text("info")

    (dest / "saludo.txt").write_text("otra edición\n")
    assert eng.apply(e, {"token": "a"})
    assert backup.read_text() == "otra edición\n"  # la copia anterior se sobrescribe
    assert list(dest.rglob("*.backup")) == [backup]  # una sola copia


def test_dry_run_shows_diff_and_writes_nothing(config, sink, demo, dest: Path) -> None:
    e = demo()
    assert Engine(config, sink).apply(e, {"token": "zzz"}, dry_run=True)
    out = sink.text()
    assert "# echo usuario=$who" in out  # se muestra, no se ejecuta
    assert "+hola mundo, cuesta $5, token=" + MASK in out
    assert "zzz" not in out
    assert not dest.exists()


def test_failing_step_stops(config, sink, demo, dest: Path) -> None:
    extra = (
        '[[step]]\ntitle = "Falla"\nrun = "echo antes; exit 7"\n'
        f'[[step]]\ntitle = "Nunca"\nrun = "touch {dest}/nunca"'
    )
    e = demo(extra)
    assert not Engine(config, sink).apply(e, {"token": "x"})
    assert "código 7" in sink.text("error")
    assert "Detenido en el paso 4/5" in sink.text("error")
    assert not (dest / "nunca").exists()


def test_on_step_reports_progress(config, sink, demo) -> None:
    e = demo()
    eng = Engine(config, sink)
    seen: list[tuple[int, int, str]] = []
    eng.on_step = lambda i, total, step: seen.append((i, total, step.kind))
    assert eng.apply(e, {"token": "x"}, dry_run=True)
    assert seen == [(1, 3, "run"), (2, 3, "template"), (3, 3, "copy")]


def test_cancel_terminates_and_stops(config, sink, demo, dest: Path) -> None:
    import threading

    e = demo(
        f'[[step]]\ntitle = "Lento"\nrun = "sleep 30"\n'
        f'[[step]]\ntitle = "Nunca"\nrun = "touch {dest}/nunca"'
    )
    eng = Engine(config, sink)
    eng.on_step = lambda i, total, step: (
        threading.Timer(0.3, eng.cancel).start() if step.title == "Lento" else None
    )
    start = __import__("time").monotonic()
    assert not eng.apply(e, {"token": "x"})
    assert __import__("time").monotonic() - start < 10
    assert "Cancelado por el usuario" in sink.text("warn")
    assert not (dest / "nunca").exists()
    assert eng.cancelled
