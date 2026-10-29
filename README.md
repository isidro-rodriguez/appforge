<p align="center"><img src="src/appforge/resources/appforge-128.png" alt="AppForge" width="96"></p>

# appforge

Menú de consola que centraliza recetas de configuración repetibles: cada opción es un
fichero TOML que instala y configura una aplicación (ejemplos incluidos: Ollama bajo
demanda y fuentes adicionales). Para **Debian 13**.

## 🚀 Uso

Descarga `appforge-<versión>-linux-x86_64.tar.gz` de
[Releases](https://github.com/isidro-rodriguez/appforge/releases), descomprímelo y
ábrelo como superusuario:

```bash
tar -xzf appforge-<versión>-linux-x86_64.tar.gz
sudo ./appforge/appforge                    # TUI: espacio marca, i instala, d dry-run, v detalle
./appforge/appforge validate --strict       # revisa las recetas (sin sudo)
```

Trae el binario, `config.toml` y `entries/` con recetas de ejemplo: úsalas, cámbialas o
añade las tuyas. El buscador y las categorías se activan en `config.toml` (`[ui]`).

## 📚 Documentación

**[Web de la documentación](https://isidro-rodriguez.github.io/appforge/)**: guía de
uso, uso avanzado y cómo crear recetas.

## 🧑‍💻 Desarrollo

Con [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/isidro-rodriguez/appforge.git
cd appforge
uv sync
uv run ruff format . && uv run ruff check . && uv run ty check && uv run pytest
uv run python scripts/build.py --archive   # binario y .tar.gz en dist/
```

Más en [Contribuir](https://isidro-rodriguez.github.io/appforge/desarrollo/contribuir/),
[CLAUDE.md](CLAUDE.md) y, para nuevas recetas, [AGENTS.md](AGENTS.md).

## Licencia

[MIT](LICENSE).
