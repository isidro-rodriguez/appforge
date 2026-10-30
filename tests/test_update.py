"""`appforge update`: conserva los cambios del usuario y actualiza el resto."""

import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest

from appforge import __version__
from appforge import update as up
from appforge.main import main

V1 = {
    "appforge": "binario v1",
    "config.toml": 'entries_dirs = ["appforge-entries", "custom-entries"]\n',
    "appforge-entries/a.toml": "a v1\n",
    "appforge-entries/b.toml": "b v1\n",
    "appforge-entries/d.toml": "d v1\n",
    "appforge-entries/e.toml": "e igual\n",
    "appforge-entries/a/script.sh": "echo v1\n",
}
V2 = {
    "appforge": "binario v2",
    "config.toml": 'entries_dirs = ["appforge-entries", "custom-entries"]\n# v2\n',
    "appforge-entries/a.toml": "a v2\n",
    "appforge-entries/b.toml": "b v2\n",
    "appforge-entries/c.toml": "c nueva\n",
    "appforge-entries/e.toml": "e igual\n",
    "appforge-entries/a/script.sh": "echo v2\n",
}


def make_package(where: Path, version: str, files: dict[str, str]) -> Path:
    """Crea appforge-<version>-linux-<arch>.tar.gz con manifiesto y SHA256SUMS."""
    where.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": version,
        "files": {
            rel: hashlib.sha256(text.encode()).hexdigest()
            for rel, text in files.items()
        },
    }
    content = {**files, ".manifest.json": json.dumps(manifest)}
    package = where / up.asset_name(version)
    with tarfile.open(package, "w:gz") as tar:
        for rel, text in content.items():
            data = text.encode()
            info = tarfile.TarInfo(f"appforge/{rel}")
            info.size = len(data)
            info.mode = 0o755 if rel == "appforge" else 0o644
            tar.addfile(info, io.BytesIO(data))
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    (where / "SHA256SUMS").write_text(f"{digest}  {package.name}\n")
    return package


@pytest.fixture
def installed(tmp_path: Path) -> Path:
    """Instalación v1 en tmp_path/opt/appforge, con cambios del usuario."""
    package = make_package(tmp_path / "v1", "1.0.0", V1)
    with tarfile.open(package) as tar:
        tar.extractall(tmp_path / "opt", filter="data")
    base = tmp_path / "opt" / "appforge"
    (base / "custom-entries").mkdir()
    # Cambios del usuario:
    (base / "config.toml").write_text('entries_dirs = ["appforge-entries"]\n')
    (base / "appforge-entries" / "a.toml").write_text("a mía\n")
    (base / "appforge-entries" / "b.toml").unlink()
    (base / "appforge-entries" / "propia.toml").write_text("propia\n")
    (base / "custom-entries" / "mia.toml").write_text("mía\n")
    (base / "logs").mkdir()
    (base / "logs" / "appforge.log").write_text("registro\n")
    return base


def test_plan_respects_user_changes(installed: Path, tmp_path: Path) -> None:
    staged = up.extract(make_package(tmp_path / "v2", "2.0.0", V2), tmp_path / "w")
    plan = up.plan_update(installed, staged)
    assert plan.version == "2.0.0"
    assert plan.replace == ["appforge-entries/a/script.sh"]
    assert plan.add == ["appforge-entries/c.toml"]
    assert plan.keep == ["appforge-entries/a.toml", "config.toml"]
    assert plan.skip == ["appforge-entries/b.toml"]  # borrada por el usuario
    assert plan.remove == ["appforge-entries/d.toml"]  # el paquete ya no la trae
    assert plan.orphan == []


def test_apply_keeps_user_files(installed: Path, tmp_path: Path) -> None:
    staged = up.extract(make_package(tmp_path / "v2", "2.0.0", V2), tmp_path / "w")
    up.apply_update(installed, staged, up.plan_update(installed, staged))

    entries = installed / "appforge-entries"
    assert (installed / "appforge").read_text() == "binario v2"
    assert (entries / "a" / "script.sh").read_text() == "echo v2\n"
    assert (entries / "c.toml").read_text() == "c nueva\n"
    assert not (entries / "d.toml").exists()
    assert not (entries / "b.toml").exists()  # no se recrea
    # Lo modificado se conserva y la versión nueva queda al lado.
    assert (entries / "a.toml").read_text() == "a mía\n"
    assert (entries / "a.toml.new").read_text() == "a v2\n"
    assert (
        installed / "config.toml"
    ).read_text() == 'entries_dirs = ["appforge-entries"]\n'
    assert "# v2" in (installed / "config.toml.new").read_text()
    # Lo que no es del paquete no se toca.
    assert (entries / "propia.toml").read_text() == "propia\n"
    assert (installed / "custom-entries" / "mia.toml").read_text() == "mía\n"
    assert (installed / "logs" / "appforge.log").read_text() == "registro\n"
    assert up.manifest_version(installed) == "2.0.0"
    assert (installed / "appforge").stat().st_mode & 0o777 == 0o755


def test_second_update_only_touches_what_changed(
    installed: Path, tmp_path: Path
) -> None:
    staged = up.extract(make_package(tmp_path / "v2", "2.0.0", V2), tmp_path / "w")
    up.apply_update(installed, staged, up.plan_update(installed, staged))
    v3 = {**V2, "appforge-entries/c.toml": "c v3\n"}
    staged = up.extract(make_package(tmp_path / "v3", "3.0.0", v3), tmp_path / "w3")
    plan = up.plan_update(installed, staged)
    assert plan.replace == ["appforge-entries/c.toml"]
    assert plan.keep == []  # a.toml y config.toml: el paquete no los cambió


def test_modified_file_dropped_by_package_is_kept(
    installed: Path, tmp_path: Path
) -> None:
    (installed / "appforge-entries" / "d.toml").write_text("d mía\n")
    staged = up.extract(make_package(tmp_path / "v2", "2.0.0", V2), tmp_path / "w")
    plan = up.plan_update(installed, staged)
    assert plan.orphan == ["appforge-entries/d.toml"]
    up.apply_update(installed, staged, plan)
    assert (installed / "appforge-entries" / "d.toml").read_text() == "d mía\n"


def test_checksum_and_package_checks(tmp_path: Path) -> None:
    package = make_package(tmp_path / "v2", "2.0.0", V2)
    up.check_sum(package, tmp_path / "v2" / "SHA256SUMS")
    (tmp_path / "v2" / "SHA256SUMS").write_text(f"{'0' * 64}  {package.name}\n")
    with pytest.raises(up.UpdateError, match="no coincide"):
        up.check_sum(package, tmp_path / "v2" / "SHA256SUMS")
    evil = tmp_path / "evil.tar.gz"
    with tarfile.open(evil, "w:gz") as tar:
        info = tarfile.TarInfo("otra/cosa")
        tar.addfile(info, io.BytesIO(b""))
    with pytest.raises(up.UpdateError, match="no es un paquete de AppForge"):
        up.extract(evil, tmp_path / "x")


# -- CLI --------------------------------------------------------------------- #
@pytest.fixture
def cli(installed: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr("appforge.main.installed_dir", lambda: installed)
    monkeypatch.setattr("appforge.main.is_root", lambda: True)
    return installed


def test_cli_update_from_file(cli: Path, tmp_path: Path, capsys) -> None:
    package = make_package(tmp_path / "v2", "99.0.0", V2)
    assert main(["update", "--from", str(package), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert f"Programa: {__version__} → 99.0.0" in out
    assert "Modificados por ti" in out and "config.toml" in out
    assert "Dry-run" in out
    assert (cli / "appforge").read_text() == "binario v1"  # sin cambios

    assert main(["update", "--from", str(package)]) == 0
    assert "AppForge actualizado a 99.0.0" in capsys.readouterr().out
    assert (cli / "appforge").read_text() == "binario v2"
    assert not list(cli.parent.glob(".appforge-update-*"))  # temporal borrado


def test_cli_update_refuses_older_or_bad_package(
    cli: Path, tmp_path: Path, capsys
) -> None:
    old = make_package(tmp_path / "old", "0.0.1", V2)
    assert main(["update", "--from", str(old)]) == 0
    assert "--force" in capsys.readouterr().out
    assert (cli / "appforge").read_text() == "binario v1"

    bad = make_package(tmp_path / "bad", "99.0.0", V2)
    (tmp_path / "bad" / "SHA256SUMS").write_text(f"{'0' * 64}  {bad.name}\n")
    assert main(["update", "--from", str(bad)]) == 1
    assert "no coincide" in capsys.readouterr().err


def test_cli_update_up_to_date(
    cli: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(up, "latest_release", lambda: (__version__, {}))
    assert main(["update"]) == 0
    assert "Ya tienes la última versión" in capsys.readouterr().out


def test_cli_update_downloads_and_verifies(
    cli: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    package = make_package(tmp_path / "rel", "99.0.0", V2)
    assets = {package.name: "pkg", "SHA256SUMS": "sums"}
    sources = {"pkg": package, "sums": tmp_path / "rel" / "SHA256SUMS"}

    def fake_get(url: str, dest: Path | None = None) -> bytes:
        assert dest is not None
        dest.write_bytes(sources[url].read_bytes())
        return b""

    monkeypatch.setattr(up, "latest_release", lambda: ("99.0.0", assets))
    monkeypatch.setattr(up, "_get", fake_get)
    assert main(["update"]) == 0
    assert "Suma SHA-256 correcta" in capsys.readouterr().out
    assert (cli / "appforge").read_text() == "binario v2"


def test_cli_update_needs_installed_binary(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr("appforge.main.installed_dir", lambda: None)
    assert main(["update"]) == 2
    assert "git pull" in capsys.readouterr().err
