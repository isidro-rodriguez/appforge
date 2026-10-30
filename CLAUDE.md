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

A console launcher shipped as a `.tar.gz` extracted into `/opt/appforge`: one
self-contained folder with the PyInstaller binary, `config.toml`, `appforge-entries/`
(shipped examples, from the repo's `entries/`), `custom-entries/` (the user's) and
`.manifest.json`, plus `logs/` at runtime. One TOML per menu option. No `.deb`, man page or desktop launcher: the
single folder is deliberate, keep it that way. Each entry declares params, a `[check]`, ordered
steps (`run`, `script`, `template`, `copy`) and an optional `[remove]`. Target: current
Debian stable (13). It **only runs as root**: no sudo handling in the engine, no unprivileged cases.

## Structure

```text
.
├── .github/                # CI, docs (Pages), release (.tar.gz) and Dependabot
├── .pre-commit-config.yaml # pre-commit/pre-push hooks (ruff, ty, pytest)
├── AGENTS.md               # Guide for agents adding entries
├── CLAUDE.md               # This file
├── CHANGELOG.md            # Keep a Changelog
├── config.toml             # development config: entries_dirs = ["entries"]
├── docs/                   # Zensical site (Spanish): guia/, avanzado/, desarrollo/
├── docs_templates/         # Zensical overrides (favicons, mkdocstrings in Spanish)
├── entries/                # Example entries (→ /opt/appforge/appforge-entries); ollama.toml is the reference
├── pyproject.toml          # Deps, build (uv_build), ruff, ty, pytest, poe
├── README.md               # Minimal overview
├── scripts/
│   ├── backup.py           # git bundle
│   ├── build.py            # PyInstaller --onefile → dist/appforge/ + .tar.gz + SHA256SUMS
│   ├── package-config.toml # config.toml shipped in the package
│   ├── screenshots.py      # TUI and CLI SVG screenshots for the docs
│   └── try-entry.sh        # try an entry in a disposable incus VM/container
├── src/appforge/
│   ├── __init__.py         # __version__ via importlib.metadata
│   ├── __main__.py         # python -m appforge
│   ├── config.py           # Base dir (binary dir when packaged, cwd from source), config.toml
│   ├── engine.py           # Execution: check, steps, remove, .backup copies, dry-run
│   ├── entry.py            # Entry model and validation (never raises)
│   ├── main.py             # CLI entry point (Typer): validate, --version; no command -> TUI
│   ├── runlog.py           # Run log <base>/logs/appforge.log (acodo.logger, daily)
│   ├── theme.py            # Palette from the icon; Textual and Rich themes
│   ├── tui.py              # Textual app (catalog, detail page, batches, progress)
│   ├── update.py           # `appforge update`: download, verify, manifest-based merge
│   ├── validate.py         # `appforge validate`: whole-directory checks, never runs entries
│   ├── resources/          # Icon PNGs (README logo, docs favicons; not shipped)
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
- Configuration is only `config.toml` next to the binary (resolved through symlinks;
  cwd when run from source); logs go to `<base>/logs`. No environment variables.
  `config.toml` is rejected if it is a symlink or insecure.
- `entries_dirs` lists the entry directories in order; `entry.load_catalog` merges
  them and the **last one wins** on a repeated id (recorded in `Catalog.overrides`,
  reported by `validate`). An entry's files live in `<its dir>/<id>/`.
- `appforge update` never overwrites user changes: it compares the installed
  `.manifest.json`, the new one and the disk (`update.plan_update`). Unchanged
  package files are replaced, modified ones kept (new version as `.new`), deleted
  ones not recreated; `custom-entries/`, `logs/` and non-package files are never
  touched; the binary is replaced last. It needs root (not with `--dry-run`) and only
  runs on the packaged binary (`main.installed_dir()`). Downloads are verified with
  the release's `SHA256SUMS`.
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
  (Typer) only has what does not fit there: `validate`, `update` and `--version`. Do not add a
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
uv run python scripts/build.py                # dist/appforge/ + .tar.gz + SHA256SUMS
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
- Every repo entry has a dry-run test (`tests/test_<id>.py`, e.g. `tests/test_fonts.py`).
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
- User docs (`guia/`, `avanzado/`, README usage) describe the tarball extracted into
  `/opt/appforge` (`sudo /opt/appforge/appforge`; everything inside that folder). `uv` and running from source belong to `desarrollo/` only.
- Anchors keep accents (`#página-de-detalle`), like GitHub.

## Releases

- `.github/workflows/release.yml` builds the `.tar.gz` in a container of the current
  Debian stable (13, trixie), the only supported target, tests it extracted into
  `/opt` in a clean Debian 13 (checksum, version, contents, `validate --strict`,
  ownership/permissions, symlink in `PATH`, TUI without root/terminal) and publishes
  it with `SHA256SUMS` and a build provenance attestation. Do not add older releases.
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
