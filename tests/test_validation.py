"""Validación de entradas y de config.toml."""

from pathlib import Path

import pytest

from appforge.config import Config, ConfigError, load_config
from appforge.entry import Entry, load_entries


def get_entry(config: Config, name: str) -> Entry:
    entries, _ = load_entries(config.entries_dir)
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
        (f'name="x"\nrequires_root="sí"\n{STEP}', "true/false"),
        (f'name="x"\nparam="no"\n{STEP}', "[[param]]"),
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
    (config.entries_dir / "s" / "link").symlink_to("/etc/hostname")
    assert any("enlace simbólico" in p for p in get_entry(config, "s").problems)


def test_config_errors(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="No existe"):
        load_config(tmp_path)
    (tmp_path / "config.toml").write_text('entries_dir = "nope"')
    with pytest.raises(ConfigError, match="no existe"):
        load_config(tmp_path)
    (tmp_path / "config.toml").write_text('entries = "x"')
    with pytest.raises(ConfigError, match="desconocidas"):
        load_config(tmp_path)
    (tmp_path / "config.toml").write_text("entries_dir = ")
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
    cfg.write_text('entries_dir = "entries"\n')
    assert not load_config(tmp_path).ui.search
    cfg.write_text('entries_dir = "entries"\n[ui]\nsearch = true\ncategories = true\n')
    ui = load_config(tmp_path).ui
    assert ui.search
    assert ui.categories
    cfg.write_text('entries_dir = "entries"\n[ui]\nfoo = true\n')
    with pytest.raises(ConfigError, match="desconocidas en \\[ui\\]"):
        load_config(tmp_path)
    cfg.write_text('entries_dir = "entries"\nui = 1\n')
    with pytest.raises(ConfigError, match="tabla \\[ui\\]"):
        load_config(tmp_path)
