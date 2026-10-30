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

A console launcher shipped as a `.deb`: binary in `/opt/appforge` (`/usr/bin/appforge`
links to it), `/etc/appforge/config.toml` pointing to `/etc/appforge/entries/`, one TOML
per menu option. Each entry declares params, a `[check]`, ordered
steps (`run`, `script`, `template`, `copy`) and an optional `[remove]`. Target: current
Debian stable (13). It **only runs as root**: no sudo handling in the engine, no unprivileged cases.

## Structure

```text
.
├── .github/                # CI, docs (Pages), release (.deb) and Dependabot
├── .pre-commit-config.yaml # pre-commit/pre-push hooks (ruff, ty, pytest)
├── AGENTS.md               # Guide for agents adding entries
├── CLAUDE.md               # This file
├── CHANGELOG.md            # Keep a Changelog
├── config.toml             # entries_dir = "entries"
├── docs/                   # Zensical site (Spanish): guia/, avanzado/, desarrollo/
├── docs_templates/         # Zensical overrides (favicons, mkdocstrings in Spanish)
├── entries/                # Example entries (→ /etc/appforge/entries); ollama.toml is the reference
├── packaging/              # appforge.1 (man), appforge.desktop, postrm
├── pyproject.toml          # Deps, build (uv_build), ruff, ty, pytest, poe
├── README.md               # Minimal overview
├── scripts/
│   ├── backup.py           # git bundle
│   ├── build.py            # PyInstaller --onefile + dist/appforge_<v>_<arch>.deb
│   ├── screenshots.py      # TUI and CLI SVG screenshots for the docs
│   └── try-entry.sh        # try an entry in a disposable incus VM/container
├── src/appforge/
│   ├── __init__.py         # __version__ via importlib.metadata
│   ├── __main__.py         # python -m appforge
│   ├── config.py           # Base dir (/etc/appforge packaged, cwd from source), config.toml
│   ├── engine.py           # Execution: check, steps, remove, .backup copies, dry-run
│   ├── entry.py            # Entry model and validation (never raises)
│   ├── main.py             # CLI entry point (Typer): validate, --version; no command -> TUI
│   ├── runlog.py           # Run log (/var/log/appforge or <cwd>/logs; acodo.logger)
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
- `[check]` always runs with param defaults.
- **Root only.** `main._require_root()` stops the packaged TUI with a clear error
  (exit 2) unless `main.is_root()`; from source with a TTY it re-execs itself with
  `sudo` (`main.sudo_command()`). `validate` only reads files, so it does not require root;
  nor do `--help`/`--version`. Everything runs with the process privileges: do not reintroduce sudo, `requires_root` or
  unprivileged code paths.
- Steps and templates get `APPFORGE_USER` / `APPFORGE_USER_HOME` from
  `engine.invoking_user()` (`SUDO_USER`, else the process user); `entry.USER_VARS`
  lists them for template validation. Entries use them for user-owned files instead
  of asking for a user name.
- Configuration is only `/etc/appforge/config.toml` when packaged (cwd when run from
  source); logs go to `/var/log/appforge` (`<cwd>/logs` from source). No environment
  variables, no extra directories. `config.toml` is rejected if it is a symlink or
  insecure. Multiple entry directories may come
  later; do not add them (or mention them in docs) until asked.
- Before overwriting a file, copy it to `<dest>.backup` in the same directory with the
  original's mode, replacing any previous backup; the sink event lands in the run log
  (`Config.logs_dir`). Identical content means "sin cambios", no backup.
- Security checks in `entry.py` (owner in `trusted_uids()` = root, process user or
  `SUDO_UID`; group/other writable, symlinks, `..`, reserved param names) are part of
  the contract. Do not relax them without asking.
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
uv run appforge validate --strict             # repo entries: no errors or warnings (no root needed)
uv run python scripts/build.py                # binary + .deb in dist/ (needs dpkg-deb)
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
  `config.toml` (never the repo's, which is user configuration), `chdir`s into it and
  patches `appforge.main.is_root` to `True` (tests run unprivileged).
- Tests must never touch real system paths. Use dry-run for real entries and
  `tmp_path` destinations for engine tests.
- TUI tests use `App.run_test()` and Pilot at 100×30; `demo_entry()` in
  `tests/test_ui.py` builds non-root entries that write under `tmp_path`, and an
  autouse fixture keeps only `ollama` from the repo entries.
- Every repo entry has a dry-run test (`tests/test_ollama.py`, `tests/test_fonts.py`).
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
  (`usuario`, `$USER`). The only exception is the repository URL
  (`github.com/isidro-rodriguez/appforge` and its Pages site).
- User docs (`guia/`, `avanzado/`, README usage) describe the installed `.deb`
  (`sudo appforge`, paths under `/etc/appforge` and `/var/log/appforge`). `uv` and running from source belong to `desarrollo/` only.
- Anchors keep accents (`#página-de-detalle`), like GitHub.

## Releases

- `.github/workflows/release.yml` builds the `.deb` in a container of the current
  Debian stable (13, trixie), the only supported target, tests it in a clean Debian 13
  (install, man, desktop file, permissions, reinstall with a modified conffile,
  remove, purge) and publishes it with `SHA256SUMS` and a build provenance
  attestation. Do not add older releases. The man page and launcher live in
  `packaging/`; keep `packaging/appforge.1` in sync with the CLI.
- A `vX.Y.Z` tag publishes a GitHub Release; the tag must match `pyproject.toml`.
  Manual runs only upload a workflow artifact, unless `publish=true` on `main`: then
  the workflow creates the tag from `pyproject.toml` and the Release. Release notes
  come from that version's `CHANGELOG.md` section.
- Release flow for agents (this session cannot push tags): bump version + CHANGELOG,
  push to `main`, wait for CI, then `gh workflow run release.yml --ref main -f
  publish=true`.

## Definition of done

- `uv run ruff format --check .`, `uv run ruff check .`, `uv run ty check` and
  `uv run pytest` pass.
- Docs and README updated if usage or the entry format changes.
- Version bumped and `CHANGELOG.md` updated before push.
