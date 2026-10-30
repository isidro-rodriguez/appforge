"""La documentación de usuario refleja las recetas del repositorio."""

from pathlib import Path

from appforge.entry import Entry, load_entries

ROOT = Path(__file__).resolve().parent.parent
RECIPES_PAGE = ROOT / "docs" / "guia" / "recetas.md"
HEADER = "| Receta | Id | Categoría | Descripción | Parámetros |"


def catalog_row(entry: Entry) -> str:
    """Fila de la tabla de «Recetas incluidas» para ``entry``."""
    params = ", ".join(f"`{p.name}`" for p in entry.params) or "—"
    return (
        f"| {entry.name} | `{entry.id}` | {entry.category} | "
        f"{entry.description} | {params} |"
    )


def page_rows() -> list[str]:
    """Filas de la tabla del catálogo en ``docs/guia/recetas.md``."""
    lines = RECIPES_PAGE.read_text(encoding="utf-8").splitlines()
    start = lines.index(HEADER) + 2  # cabecera y separador
    rows = []
    for line in lines[start:]:
        if not line.startswith("|"):
            break
        rows.append(line)
    return rows


def test_recipes_page_lists_every_entry(home: Path) -> None:
    entries, _ = load_entries(home / "entries")
    expected = [
        catalog_row(e) for e in sorted(entries, key=lambda e: (e.category, e.name))
    ]
    assert page_rows() == expected, (
        "docs/guia/recetas.md no coincide con las recetas de entries/; "
        "la tabla debe ser, por categoría y nombre:\n" + "\n".join(expected)
    )
