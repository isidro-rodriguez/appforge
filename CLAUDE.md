# CLAUDE.md

Development guide for AppForge (the engine, CLI and TUI). For adding or editing menu
entries (`entries/*.toml`), follow [AGENTS.md](AGENTS.md) instead.

## Language

- **Code and identifiers in English**: variables, functions, constants, classes, methods,
  parameters, modules, and tests.
- **Documentation in Spanish**: docstrings, comments, error messages, README, docs, and
  commits.
- User-facing messages (CLI, TUI, engine sink events) must be in Spanish.
- `CLAUDE.md` and `AGENTS.md` are written in English.

## What AppForge is

A console launcher: one binary, a `config.toml` next to it pointing to an `entries/`
directory, one TOML per menu option. Each entry declares params, a `[check]`, ordered
steps (`run`, `script`, `template`, `copy`) and an optional `[remove]`. Target: Debian,
Linux only (bash, sudo, `install`).

## Structure

```text
.
├── .github/                # CI, docs (Pages), release (.tar.gz) and Dependabot
├── .pre-commit-config.yaml # pre-commit/pre-push hooks (ruff, ty, pytest)
├── AGENTS.md               # Guide for agents adding entries
├── CLAUDE.md               # This file
├── CHANGELOG.md            # Keep a Changelog
├── config.toml             # entries_dir = "entries"
├── docs/                   # Zensical site (Spanish): guia/, avanzado/, desarrollo/
├── docs_templates/         # Zensical overrides (favicons, mkdocstrings in Spanish)
├── entries/                # Menu entries shipped as examples; ollama.toml is the reference
├── pyproject.toml          # Deps, build (uv_build), ruff, ty, pytest, poe
├── README.md               # Minimal overview
├── scripts/
│   ├── backup.py           # git bundle
│   ├── build.py            # PyInstaller --onefile -> dist/appforge/ (--archive: .tar.gz)
│   └── screenshots.py      # TUI and CLI SVG screenshots for the docs
├── src/appforge/
│   ├── __init__.py         # __version__ via importlib.metadata
│   ├── __main__.py         # python -m appforge
│   ├── config.py           # Base dir and config.toml
│   ├── engine.py           # Execution: check, steps, remove, sudo, backups, dry-run
│   ├── entry.py            # Entry model and validation (never raises)
│   ├── main.py             # CLI entry point (Typer): validate, --version; no command -> TUI
│   ├── runlog.py           # Run log file (acodo.logger, daily rotation)
│   ├── theme.py            # Palette from the icon; Textual and Rich themes
│   ├── tui.py              # Textual app (catalog, detail page, batches, progress)
│   ├── validate.py         # `appforge validate`: whole-directory checks, never runs entries
│   ├── resources/          # Optimized icons (appforge-<size>.png)
│   └── py.typed
├── tests/                  # pytest
├── uv.lock
└── zensical.toml          # Docs site config (nav, theme, mkdocstrings)
```

## Architecture rules (load-bearing)

- `entry.load_entry` **never raises**: every validation failure goes to
  `Entry.problems`. Invalid entries are shown with ⚠ and cannot be applied.
- The engine **never prints**. It emits `sink(kind, text)` events with `kind` in
  `step`, `out`, `info`, `ok`, `warn`, `error`. CLI and TUI render them.
- State is derived from `[check]` only. Do not add a state file.
- Params are never persisted. They reach bash through a temporary `0600` script with
  `export` lines, never through `argv` or the process environment.
- Secret values are masked (`MASK`) in every sink event, including dry-run diffs.
- `[check]` always runs unprivileged and with param defaults.
- Privileged commands go through `Runner._prefix` (`sudo -n` after one `sudo -v`).
  `APPFORGE_SUDO` overrides the prefix; tests set it to `""`.
- Before overwriting a file, back it up to `backups_dir` (`0600`). Identical content
  means "sin cambios", no backup.
- Security checks in `entry.py` (owner, group/other writable, symlinks, `..`, reserved
  param names) are part of the contract. Do not relax them without asking.
- Scope limit: four step kinds, no conditionals, loops or inter-entry dependencies.
  Push complex logic into an entry `script`. Ask before extending the format.
- **The CLI does not duplicate the TUI.** Everything interactive (browse, apply,
  remove, dry-run) lives in the TUI, which already runs in any console. The CLI
  (Typer) only has what does not fit there: `validate` and `--version`. Do not add a
  command the TUI already covers.
- `appforge validate` never runs entry code: it reads files and calls `bash -n`.
  Errors make it exit 1; warnings only with `--strict`.
- The TUI imports Textual lazily from `main.py` so the CLI starts fast.
- Colors live only in `theme.py` (taken from the icon). TUI CSS uses theme variables
  (`$accent`, `$primary`, …) or `STYLES`; the CLI uses the `af.*` Rich styles and
  `TYPER_STYLES` for Typer's help. Do not hard-code colors elsewhere.
- Steps run inside `_wrap_cancellable` (subshell in its own process group) so
  `Engine.cancel()` kills the whole command tree. Keep it when touching `Runner.shell`.
- Catalog bindings must not act on other screens: add new main-screen actions to
  `_MAIN_ACTIONS` in `tui.py`.
- The TUI mirrors `docs/guia/interfaz.md`; update both together (and regenerate the
  screenshots with `scripts/screenshots.py`). `[ui]` options in
  `config.toml` are validated in `config.py`; unknown keys are an error.

## Tools and canonical commands

Do not use `pip install` directly. Use `uv`.

```bash
uv sync
uv run ruff format .
uv run ruff check .
uv run ty check
uv run pytest
uv run appforge validate --strict             # repo entries: no errors or warnings
uv run python scripts/build.py --archive      # binary in dist/appforge/ + .tar.gz
uv run python scripts/screenshots.py          # docs screenshots (SVG)
uv run --group docs zensical build            # docs site in site/
```

- One `uv.lock` and one venv at the root. Run tools from the root.
- Add dependencies with `uv add <pkg>` / `uv add --dev <pkg>` and justify them.
- The `docs` dependency group (`zensical`, `mkdocstrings-python`) is only for the site.
- `acodo` is the utility library (`acodo>=0.3,<1`); prefer its helpers (`get_env`,
  `to_path`, ...) over ad-hoc code. The other runtime dependencies are `textual` (TUI)
  and `typer` (CLI).

### Optional poe tasks

`[tool.poe]` defines shortcuts (`check`, `fix`, `build`, `screenshots`, `docs`,
`backup`) for developers who have Poe the Poet installed globally. `poethepoet` is **not** a project dependency;
every task must also run with plain `uv run`. Keep tasks thin wrappers.

## Code rules

- PEP 8, strict type annotations; `ty check --error-on-warning` must pass.
- Google-style docstrings in Spanish for public identifiers (`ruff` rule set `D`);
  brief docstrings for private ones.
- Small functions, explicit code, no overengineering. Stdlib first.

## Tests

- `pytest` with `--import-mode=importlib`: tests cannot import `conftest`; share helpers
  through fixtures (`home`, `config`, `write_entry`, `sink`).
- The `home` fixture copies the real `entries/` into `tmp_path` with a default
  `config.toml` (never the repo's, which is user configuration) and sets `APPFORGE_HOME`, `XDG_STATE_HOME` and `APPFORGE_SUDO=""`.
- Tests must never touch real system paths. Use dry-run for real entries and
  `tmp_path` destinations for engine tests.
- TUI tests use `App.run_test()` and Pilot at 100×30; `demo_entry()` in
  `tests/test_ui.py` builds non-root entries that write under `tmp_path`, and an
  autouse fixture keeps only `ollama` from the repo entries.
- Every repo entry has a test: a dry-run, or a real run under a temporary `HOME` for
  non-root entries (`tests/test_git_alias.py`).
- Linux only (CI runs on `ubuntu-latest`).

## Agent workflow

1. Before changing, read `README.md`, `pyproject.toml`, this file and related tests.
2. Make the smallest necessary change. Do not refactor unrelated code.
3. Run the quality commands from the root and fix until they pass.
4. If something fails and you cannot resolve it, show the exact error and propose the
   minimal fix.
5. Update `docs/` when behavior or the entry format changes, and check that
   `uv run --group docs zensical build` reports no issues.

## Commits and versioning

- Commit directly when a change is done and the quality commands pass; never push.
- Conventional Commits in Spanish (`feat: …`, `fix: …`, `docs: …`, `test: …`,
  `chore: …`), atomic, explaining the _why_.
- Before any push with code changes: bump the version in `pyproject.toml` (SemVer) and
  update `CHANGELOG.md` (Keep a Changelog, Spanish). Changing the entry format in a
  non-backward-compatible way is MAJOR.

## Documentation

- The site is built with Zensical from `docs/` and `zensical.toml`; the nav is explicit,
  so add new pages there. `.github/workflows/docs.yml` publishes it to GitHub Pages.
- Sections: `guia/` (users), `avanzado/` (advanced users), `desarrollo/` (entry authors
  and contributors). `docs/changelog.md` includes `CHANGELOG.md` via snippets.
- The site theme mirrors `theme.py` in `docs/assets/stylesheets/appforge.css`.
- Screenshots in `docs/assets/images/screenshots/` come from `scripts/screenshots.py`
  (harmless demo entries); never edit them by hand.
- **No personal data** in docs, examples, tests or screenshots: use placeholders
  (`usuario`, `<usuario>`, `~`, `$USER`).
- Anchors keep accents (`#página-de-detalle`), like GitHub.

## Releases

- `.github/workflows/release.yml` builds the `.tar.gz` (binary, `config.toml`,
  `entries/`) in a container of the current Debian stable (13, trixie), the only
  supported target, and smoke-tests it. Do not add older releases.
- A `vX.Y.Z` tag publishes a GitHub Release; the tag must match `pyproject.toml`.
  Manual runs only upload a workflow artifact.

## Definition of done

- `uv run ruff format --check .`, `uv run ruff check .`, `uv run ty check` and
  `uv run pytest` pass.
- Docs and README updated if usage or the entry format changes.
- Version bumped and `CHANGELOG.md` updated before push.
