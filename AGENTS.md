# AGENTS.md

Guide for agents that add or edit **menu entries** in `entries/`. Changing the engine,
CLI or TUI is out of scope here: see [CLAUDE.md](CLAUDE.md).

The repo's `entries/` ships in the package as `/opt/appforge/appforge-entries/`.
End users put their own recipes in `/opt/appforge/custom-entries/` (listed later in
`entries_dirs`, so a folder there with the same id replaces the shipped one). Recipes
for the project go in `entries/`.

## Language

- Entry content shown to the user (`name`, `description`, `details.md`, `prompt`,
  `title`, comments) in **Spanish**.
- Param names, file names and shell code identifiers in **English** (`snake_case`).

## Where things go

```text
entries/
└── <id>/            # one folder per entry; <id> in kebab-case, e.g. docker-rootless
    ├── entry.toml   # the entry (required)
    ├── details.md   # its detail page in Markdown (required; not declared in entry.toml)
    ├── *.tpl        # templates (string.Template)
    ├── *.sh         # scripts for `script` steps
    └── ...          # files for `copy` steps
```

`details.md` explains what the entry installs, what to know before applying it
(prerequisites, risks, interactions with other entries) and what `[remove]` keeps. A
missing or empty `details.md`, or a `details` key in `entry.toml`, makes the entry
invalid.

Full format reference: [docs/desarrollo/formato.md](docs/desarrollo/formato.md); step-by-step
tutorial: [docs/desarrollo/nueva-entrada.md](docs/desarrollo/nueva-entrada.md). Reference
example: `entries/ollama/`.

Every entry is listed in the catalog table of
[docs/guia/recetas.md](docs/guia/recetas.md) (name, id, category, description,
params; sorted by category and name). `tests/test_docs.py` fails, printing the
expected table, if it is out of date. Add interactions with other entries to its
«Combinarlas» section.

## Format cheat sheet

```toml
name = "Nombre en el menú"
description = "Una línea"
category = "Desarrollo"        # optional; groups entries in the categories panel
# The long description goes in details.md (TUI detail page: double click or `v`).

[[param]]
name = "owner"                 # available as $owner in run/script and templates
prompt = "Usuario propietario"
default = "usuario"            # omit to make it mandatory
secret = false                 # true: hidden input, masked output
link = "https://…/releases"    # optional: where to pick the value (shown in the TUI)

[check]                        # exit 0 = applied; runs with param defaults
run = "test -x /opt/x/bin/x"

[[step]]                       # exactly one of: run | script | template | copy
title = "Instalar dependencias"
run = "DEBIAN_FRONTEND=noninteractive apt-get install -y curl"

[[step]]
title = "Configuración"
template = "x.conf.tpl"        # relative to the entry folder (entries/<id>/)
dest = "/etc/x.conf"           # absolute
mode = "0644"

[remove]                       # optional; afterwards [check] must fail
run = "rm -rf /opt/x"
```

Extra variables in `run`/`script`: `APPFORGE_USER` and `APPFORGE_USER_HOME` (who ran
`sudo appforge`; also usable in templates), `APPFORGE_ENTRY`, `APPFORGE_ENTRY_DIR`,
`APPFORGE_DRY_RUN`. Working directory: `entries/<id>/`.

Everything runs as root. When an entry writes files that belong to the user (their
`HOME`, a directory they must write to), give them to `$APPFORGE_USER` (`chown`,
`install -o`). Never ask for the user name as a param.

## Rules (load-bearing)

1. **Idempotent steps.** Every step must be safe to run again after a partial failure.
   Prefer `install -D`, `mkdir -p`, `apt-get install -y`, `ln -sf`, `systemctl enable`.
2. **`[check]` verifies the final result**, not an intermediate step, and must be
   read-only (use `test -e`, `command -v`, `grep -q`): it runs every time the catalog
   is drawn. AppForge only runs as root, so everything (steps, `[check]`, `[remove]`)
   runs as root; there is no `requires_root` key.
3. **Target Debian.** Use `apt-get` with `DEBIAN_FRONTEND=noninteractive`. Do not
   abstract the package manager.
4. **No `curl | bash`.** Download to a file, verify, then run. Use HTTPS and
   `curl -fsSL`.
4b. **Pinned, verified downloads.** When the download URL contains the version and
   upstream releases often, expose it as a `version` param with a sensible default
   and `link` to the upstream releases page, and verify the SHA-256 against the
   official checksum file of that version. No published checksum → fail, never
   install unverified (see `entries/ollama/install-ollama.sh`).
5. **Files over heredocs.** Config files go in `entries/<id>/` as `template` or `copy`
   steps, so the dry-run shows a diff and backups are made.
6. **Templates:** only declared params (`$name`); write `$$` for a literal `$` (shell
   scripts with `$VAR` must be `copy`, not `template`).
7. **Secrets:** mark them `secret = true`; never give them a default and never write
   them to logs. If a secret must land in a file, use `mode = "0600"`.
8. **Paths:** sources relative to `entries/<id>/` without `..`; `dest` absolute.
   Keep everything an entry installs under one prefix when possible (e.g. `/opt/<app>`),
   so `[remove]` is simple.
9. **`[remove]` keeps user data** (models, databases, documents) unless the user asks
   otherwise; say so in a comment.
10. **Permissions:** entry files must not be writable by group/others
    (`chmod -R go-w entries`), and no symlinks inside `entries/<id>/`. AppForge rejects
    them.
11. **Scope:** no conditionals or loops in TOML. If you need logic, write a `script`
    step and keep it idempotent with `set -euo pipefail`.
12. **Category:** reuse an existing `category` when one fits
    (`grep -h '^category' entries/*/entry.toml | sort -u`) instead of creating near-duplicates.
13. **Do not modify** the engine, CLI, TUI or the entry format to fit a new entry. If
    the format falls short, stop and propose the change.

## Verification

Run from the repository root:

```bash
chmod -R go-w entries
uv run appforge validate --strict <id>       # no errors and no warnings (exit 0)
uv run pytest tests/test_<id>.py -s          # your dry-run test (see below)
uv run pytest                                # existing suite still passes
scripts/try-entry.sh <id> --no-tui           # optional: install + validate in a clean VM (incus)
```

`validate` never runs anything: it checks the format, security, bash syntax (`bash -n`),
`$APPFORGE_ENTRY_DIR/<file>` references, and unused files and params.

The CLI has no `apply`: the dry-run goes through a test. Add `tests/test_<id>.py`
following `tests/test_ollama.py`: load the entry with the `config` fixture, run
`Engine(config, sink).apply(entry, values, dry_run=True)`, and assert that `[check]` is
false (`engine.is_applied(entry) is False`) and on the rendered files in `sink.text()`.
Review that output: commands (shown with `#`), diffs of every generated file, and no
secret in clear text. Tests must never touch real system paths, so repo entries are only
tested with a dry-run (see `tests/test_git_alias.py`).

## Definition of done

- `appforge validate --strict <id>` reports no errors or warnings.
- Dry-run test added and reviewed; `[check]` fails before applying.
- `uv run pytest` passes.
- If the entry needs a file the user must provide (icon, key), say so in its
  `description` or a comment and in your final report.
- `CHANGELOG.md` updated under `## [Unreleased]` → `### Added` (Spanish).
- Commit the entry (Conventional Commits in Spanish, e.g. `feat: receta de syncthing`);
  never push.
