"""La entrada de ejemplo git-alias (alias de git para todo el sistema)."""

from appforge.engine import Engine
from appforge.entry import load_entries


def test_dry_run(config, sink) -> None:
    entries, _ = load_entries(config.entries_dir)
    entry = next(e for e in entries if e.id == "git-alias")
    assert entry.valid, entry.problems
    engine = Engine(config, sink)
    assert engine.apply(entry, {}, dry_run=True), sink.text()
    out = sink.text()
    assert "crear /usr/local/etc/appforge/git-aliases.gitconfig (modo 0644" in out
    assert "# git config --system --get-all include.path" in out
    assert engine.remove(entry, dry_run=True)
    assert "--unset-all include.path" in sink.text()
