# AGENTS.md

Guide for agents that add or edit **menu entries** in `entries/`. Changing the engine,
CLI or TUI is out of scope here: see [CLAUDE.md](CLAUDE.md).

## Language

- Entry content shown to the user (`name`, `description`, `details`, `prompt`, `title`,
  comments) in **Spanish**.
- Param names, file names and shell code identifiers in **English** (`snake_case`).

## Where things go

```text
entries/
├── <id>.toml        # the entry; <id> in kebab-case, e.g. docker-rootless
└── <id>/            # only if the entry needs extra files
    ├── *.tpl        # templates (string.Template)
    ├── *.sh         # scripts for `script` steps
    └── ...          # files for `copy` steps
```

Full format reference: [docs/desarrollo/formato.md](docs/desarrollo/formato.md); step-by-step
tutorial: [docs/desarrollo/nueva-entrada.md](docs/desarrollo/nueva-entrada.md). Reference
example: `entries/ollama.toml` ([docs/guia/ollama.md](docs/guia/ollama.md)).

## Format cheat sheet

```toml
name = "Nombre en el menú"
description = "Una línea"
category = "Desarrollo"        # optional; groups entries in the categories panel
details = """
Long Markdown description shown in the TUI detail page (double click or `v`).
"""
requires_root = true

[[param]]
name = "owner"                 # available as $owner in run/script and templates
prompt = "Usuario propietario"
default = "isidro"             # omit to make it mandatory
secret = false                 # true: hidden input, masked output

[check]                        # exit 0 = applied; runs WITHOUT root, with defaults
run = "test -x /opt/x/bin/x"

[[step]]                       # exactly one of: run | script | template | copy
title = "Instalar dependencias"
run = "DEBIAN_FRONTEND=noninteractive apt-get install -y curl"

[[step]]
title = "Configuración"
template = "x.conf.tpl"        # relative to entries/<id>/
dest = "/etc/x.conf"           # absolute
mode = "0644"

[remove]                       # optional; afterwards [check] must fail
run = "rm -rf /opt/x"
```

Extra variables in `run`/`script`: `APPFORGE_ENTRY`, `APPFORGE_ENTRY_DIR`,
`APPFORGE_DRY_RUN`. Working directory: `entries/<id>/`.

## Rules (load-bearing)

1. **Idempotent steps.** Every step must be safe to run again after a partial failure.
   Prefer `install -D`, `mkdir -p`, `apt-get install -y`, `ln -sf`, `systemctl enable`.
2. **`[check]` verifies the final result**, not an intermediate step, and must be
   read-only and work without root (use `test -e`, `command -v`, `grep -q` on readable
   files). If the result is not readable without root, check something that is.
3. **Target Debian.** Use `apt-get` with `DEBIAN_FRONTEND=noninteractive`. Do not
   abstract the package manager.
4. **No `curl | bash`.** Download to a file, verify when the upstream publishes a
   checksum, then run. Use HTTPS and `curl -fsSL`.
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
12. **Category:** reuse an existing `category` when one fits (`uv run appforge list`
    shows them) instead of creating near-duplicates.
13. **Do not modify** the engine, CLI, TUI or the entry format to fit a new entry. If
    the format falls short, stop and propose the change.

## Verification

Run from the repository root:

```bash
chmod -R go-w entries
uv run appforge show <id>                    # must list no problems (exit 0)
uv run appforge apply <id> -n --no-input -s param=value ...   # dry-run
uv run appforge check <id>                   # 1 = not applied yet
uv run pytest                                # existing suite still passes
```

Review the dry-run output: commands (`#` = runs as root), diffs of every generated file,
and no secret in clear text.

Optionally add a test in `tests/test_<id>.py` following `tests/test_ollama.py`: validate
the entry, run a dry-run with the `home` fixture and assert on the rendered files. Tests
must never touch real system paths.

## Definition of done

- `appforge show <id>` reports no problems.
- Dry-run reviewed; `[check]` fails before applying.
- `uv run pytest` passes.
- If the entry needs a file the user must provide (icon, key), say so in its
  `description` or a comment and in your final report.
- `CHANGELOG.md` updated under `## [Unreleased]` → `### Added` (Spanish).
- Commit the entry (Conventional Commits in Spanish, e.g. `feat: receta de syncthing`);
  never push.
