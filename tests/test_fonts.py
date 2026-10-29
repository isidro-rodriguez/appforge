"""La entrada de fuentes adicionales (siempre en dry-run)."""

from appforge.engine import Engine
from appforge.entry import load_entries


def fonts(config):
    entries, _ = load_entries(config.entries_dir)
    return next(e for e in entries if e.id == "fonts")


def test_entry_is_valid(config) -> None:
    e = fonts(config)
    assert e.problems == []
    assert [p.name for p in e.params] == ["nerd_version"]
    assert [s.kind for s in e.steps] == ["run", "script", "run", "run", "script", "run"]


def test_dry_run_installs_every_font(config, sink) -> None:
    e = fonts(config)
    engine = Engine(config, sink)
    assert engine.apply(e, {"nerd_version": "v3.4.0"}, dry_run=True), sink.text()
    out = sink.text()
    assert "msttcorefonts/accepted-mscorefonts-eula select true" in out
    assert (
        "apt-get install -y ttf-mscorefonts-installer fonts-ubuntu fonts-firacode"
        in out
    )
    assert "nerd-font.sh" in out
    assert "# fc-cache -f" in out
    assert engine.remove(e, dry_run=True)
    assert "rm -f /etc/apt/sources.list.d/appforge-fonts.sources" in sink.text()
