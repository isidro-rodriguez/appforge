<p align="center"><img src="src/appforge/resources/appforge-128.png" alt="AppForge" width="96"></p>

# appforge

Menú de consola que centraliza recetas de configuración repetibles: cada opción es un
fichero TOML que instala y configura una aplicación (ejemplos incluidos: Ollama bajo
demanda y alias de git). Hecho con [Textual](https://textual.textualize.io/) y las herramientas de
[Astral](https://astral.sh) (`uv`, `ruff`, `ty`).

## 🚀 Instalación

Descarga `appforge-<versión>-linux-x86_64.tar.gz` de **Releases** (binario,
`config.toml` y recetas de ejemplo) y extráelo, o desde el código:

```bash
git clone https://github.com/<usuario>/appforge.git
cd appforge
uv sync
```

## 🛠️ Uso

```bash
uv run appforge                          # TUI: espacio marca, i instala, d dry-run, v detalle
uv run appforge validate --strict        # revisa las recetas sin ejecutarlas
uv run python scripts/build.py --archive # binario y .tar.gz en dist/
```

El buscador y el panel de categorías se activan en `config.toml` (`[ui]`).

## ✅ Calidad

```bash
uv run ruff format .
uv run ruff check .
uv run ty check
uv run pytest
```

Con [Poe the Poet](https://poethepoet.natn.io/) instalado globalmente: `poe check`,
`poe fix`, `poe build`, `poe backup`.

## 📚 Documentación

**[Web de la documentación](https://isidro-rodriguez.github.io/appforge/)** — guía de uso, uso avanzado y
cómo crear recetas. Fuente en [`docs/`](docs/); vista previa local con
`uv run --group docs zensical serve`.

- Desarrollo: [CLAUDE.md](CLAUDE.md) · Nuevas recetas: [AGENTS.md](AGENTS.md)

## Licencia

[MIT](LICENSE).
