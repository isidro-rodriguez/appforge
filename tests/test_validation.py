"""Validación de entradas y de config.toml."""

from pathlib import Path

import pytest

from appforge.config import Config, ConfigError, load_config
from appforge.entry import Entry, load_entries


def get_entry(config: Config, name: str) -> Entry:
    entries, _ = load_entries(config.entries_dirs[0])
    return next(e for e in entries if e.id == name)


@pytest.fixture
def problems(config, write_entry):
    """Escribe una entrada y devuelve sus problemas."""

    def check(toml: str, files: dict[str, str] | None = None) -> list[str]:
        write_entry("bad", toml, files)
        return get_entry(config, "bad").problems

    return check


STEP = '[[step]]\nrun="true"'


@pytest.mark.parametrize(
    ("toml", "expected"),
    [
        (f'name="x"\nfoo=1\n{STEP}', "claves desconocidas: foo"),
        ('name="x"', "ningún [[step]]"),
        ('name="x"\n[[step]]\nrun="a"\ncopy="b"', "exactamente uno"),
        ('name="x"\n[[step]]\ncopy="../etc/passwd"\ndest="/tmp/x"', "sin '..'"),
        ('name="x"\n[[step]]\ncopy="/etc/passwd"\ndest="/tmp/x"', "relativo"),
        ('name="x"\n[[step]]\ncopy="nada"\ndest="/tmp/x"', "falta el fichero"),
        (f'name="x"\n{STEP}\ndest="/tmp/x"', "solo valen en template/copy"),
        (f'name="x"\n[[param]]\nname="PATH"\n{STEP}', "reservado"),
        (f'name="x"\n[[param]]\nname="APPFORGE_X"\n{STEP}', "reservado"),
        (f'name="x"\n[[param]]\nname="a b"\n{STEP}', "nombre inválido"),
        (f'name="x"\n[[param]]\nname="a"\n[[param]]\nname="a"\n{STEP}', "duplicado"),
        (f'name="x"\nrequires_root=true\n{STEP}', "claves desconocidas: requires_root"),
        (f'name="x"\n[[param]]\nname="a"\nsecret="sí"\n{STEP}', "true/false"),
        (f'name="x"\nparam="no"\n{STEP}', "[[param]]"),
        (
            f'name="x"\n[[param]]\nname="v"\nlink="javascript:x"\n{STEP}',
            "'link' debe ser una URL http(s)",
        ),
        (f'name="x"\ncheck="no"\n{STEP}', "tabla [check]"),
        ("name = ", "TOML inválido"),
    ],
)
def test_invalid_entries(problems, toml: str, expected: str) -> None:
    found = problems(toml)
    assert any(expected in p for p in found), found


def test_template_unknown_param_and_bad_mode(problems) -> None:
    found = problems(
        'name="t"\n[[step]]\ntemplate="a.tpl"\ndest="/tmp/a"\nmode="644x"',
        {"a.tpl": "$nope ${tampoco}"},
    )
    assert any("nope, tampoco" in p for p in found)
    assert any("'mode'" in p for p in found)


def test_world_writable_entry_is_rejected(config, write_entry) -> None:
    write_entry("w", f'name="w"\n{STEP}').chmod(0o666)
    e = get_entry(config, "w")
    assert not e.valid
    assert any("escribible" in p for p in e.problems)


def test_symlink_in_files_dir_is_rejected(config, write_entry) -> None:
    write_entry("s", f'name="s"\n{STEP}', {"ok.txt": "x"})
    (config.entries_dirs[0] / "s" / "link").symlink_to("/etc/hostname")
    assert any("enlace simbólico" in p for p in get_entry(config, "s").problems)


def test_config_errors(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="No existe"):
        load_config(tmp_path)
    (tmp_path / "config.toml").write_text('entries_dirs = ["nope"]')
    with pytest.raises(ConfigError, match="no existe"):
        load_config(tmp_path)
    (tmp_path / "config.toml").write_text('entries = "x"')
    with pytest.raises(ConfigError, match="desconocidas"):
        load_config(tmp_path)
    (tmp_path / "config.toml").write_text("entries_dirs = ")
    with pytest.raises(ConfigError, match="TOML inválido"):
        load_config(tmp_path)


def test_category_is_read(config, write_entry) -> None:
    write_entry("c", f'name="c"\ncategory = " Juegos "\n{STEP}')
    assert get_entry(config, "c").category == "Juegos"
    write_entry("c", f'name="c"\ncategory = 3\n{STEP}')
    assert any(
        "'category' debe ser texto" in p for p in get_entry(config, "c").problems
    )


def test_ui_options(tmp_path: Path) -> None:
    (tmp_path / "entries").mkdir()
    cfg = tmp_path / "config.toml"
    cfg.write_text('entries_dirs = ["entries"]\n')
    assert not load_config(tmp_path).ui.search
    cfg.write_text(
        'entries_dirs = ["entries"]\n[ui]\nsearch = true\ncategories = true\n'
    )
    ui = load_config(tmp_path).ui
    assert ui.search
    assert ui.categories
    cfg.write_text('entries_dirs = ["entries"]\n[ui]\nfoo = true\n')
    with pytest.raises(ConfigError, match="desconocidas en \\[ui\\]"):
        load_config(tmp_path)
    cfg.write_text('entries_dirs = ["entries"]\nui = 1\n')
    with pytest.raises(ConfigError, match="tabla \\[ui\\]"):
        load_config(tmp_path)


def test_sudo_user_files_are_trusted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    from appforge.entry import insecure_reason

    f = tmp_path / "x.toml"
    f.write_text("")
    f.chmod(0o644)
    real = f.stat()
    monkeypatch.setattr(os, "getuid", lambda: 4242)  # como si fuéramos otro (root)
    monkeypatch.delenv("SUDO_UID", raising=False)
    if real.st_uid != 0:
        assert "propietario ajeno" in (insecure_reason(f) or "")
    monkeypatch.setenv("SUDO_UID", str(real.st_uid))  # quien llamó a sudo
    assert insecure_reason(f) is None


def test_insecure_config_is_rejected(home: Path) -> None:
    from appforge.config import ConfigError, load_config

    config = home / "config.toml"
    config.chmod(0o666)
    with pytest.raises(ConfigError, match="escribible por grupo u otros"):
        load_config(home)
    config.chmod(0o644)
    real = home / "real.toml"
    config.rename(real)
    config.symlink_to(real)
    with pytest.raises(ConfigError, match="enlace simbólico"):
        load_config(home)


def test_several_entries_dirs_last_one_wins(home: Path) -> None:
    from appforge.entry import load_catalog
    from appforge.validate import validate_dirs

    custom = home / "custom-entries"
    custom.mkdir(mode=0o755)
    for entry_id, name in [("ollama", "Ollama propio"), ("mia", "Mía")]:
        (custom / entry_id).mkdir()
        (custom / entry_id / "entry.toml").write_text(f'name = "{name}"\n{STEP}')
        (custom / entry_id / "details.md").write_text("Ficha.\n")
    for p in [custom, *custom.rglob("*")]:
        p.chmod(p.stat().st_mode & ~0o022)
    (home / "config.toml").write_text('entries_dirs = ["entries", "custom-entries"]\n')
    config = load_config(home)
    assert [d.name for d in config.entries_dirs] == ["entries", "custom-entries"]

    catalog = load_catalog(config.entries_dirs)
    by_id = {e.id: e for e in catalog.entries}
    assert by_id["ollama"].name == "Ollama propio"  # gana el último directorio
    assert by_id["ollama"].source == "custom-entries/ollama/"
    assert "mia" in by_id and "fonts" in by_id
    assert catalog.overrides == [
        "ollama: custom-entries/ollama/ sustituye a entries/ollama/"
    ]
    warnings = validate_dirs(config.entries_dirs).warnings
    assert any("sustituye a entries/ollama/" in w for w in warnings)


def test_entries_dirs_must_be_a_list(tmp_path: Path) -> None:
    (tmp_path / "e").mkdir()
    for raw in ('entries_dirs = "e"', "entries_dirs = []", "entries_dirs = [1]"):
        (tmp_path / "config.toml").write_text(raw)
        with pytest.raises(ConfigError, match="lista de rutas"):
            load_config(tmp_path)
    (tmp_path / "config.toml").write_text("ui = {}")
    with pytest.raises(ConfigError, match="falta 'entries_dirs'"):
        load_config(tmp_path)


# -- Carpeta de la entrada ---------------------------------------------------- #
def test_details_md_is_required(config, write_entry) -> None:
    write_entry("sinficha", f'name = "Sin ficha"\n{STEP}', details=None)
    write_entry("vacia", f'name = "Vacía"\n{STEP}', details="  \n")
    assert "falta sinficha/details.md" in "\n".join(
        get_entry(config, "sinficha").problems
    )
    assert "vacia/details.md está vacío" in get_entry(config, "vacia").problems


def test_details_key_points_to_details_md(config, write_entry) -> None:
    write_entry("vieja", f'name = "Vieja"\ndetails = "texto"\n{STEP}')
    problems = get_entry(config, "vieja").problems
    assert problems == ["entrada: 'details' va en vieja/details.md"]


def test_details_md_feeds_the_detail_page(config, write_entry) -> None:
    write_entry("ficha", f'name = "Ficha"\n{STEP}', details="## Uso\n\nTexto.\n")
    entry = get_entry(config, "ficha")
    assert entry.valid
    assert entry.details == "## Uso\n\nTexto."
    assert entry.files_dir == config.entries_dirs[0] / "ficha"


def test_own_files_are_not_unused(config, write_entry) -> None:
    from appforge.validate import validate_entry

    write_entry("limpia", f'name = "Limpia"\ndescription = "d"\n{STEP}')
    warnings = validate_entry(get_entry(config, "limpia")).warnings
    assert not [w for w in warnings if "sin usar" in w]
