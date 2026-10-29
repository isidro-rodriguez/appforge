<p align="center"><img src="src/appforge/resources/appforge-128.png" alt="AppForge" width="96"></p>

# appforge

Menú de consola que centraliza recetas de configuración repetibles: cada opción es un
fichero TOML que instala y configura una aplicación (ejemplos incluidos: Ollama bajo
demanda y alias de git). Para **Debian 13**.

## 🚀 Instalación

Descarga `appforge-<versión>-linux-x86_64.tar.gz` de
[Releases](https://github.com/isidro-rodriguez/appforge/releases) y extráelo como
superusuario:

```bash
sudo tar -xzf appforge-<versión>-linux-x86_64.tar.gz -C /opt
sudo ln -s /opt/appforge/appforge /usr/local/bin/appforge
```

Contiene el binario, `config.toml` y `entries/` con las recetas de ejemplo.

## 🛠️ Uso

AppForge solo funciona como superusuario.

```bash
sudo appforge                       # TUI: espacio marca, i instala, d dry-run, v detalle
sudo appforge validate --strict     # revisa las recetas sin ejecutarlas
```

El buscador y el panel de categorías se activan en `/opt/appforge/config.toml` (`[ui]`).

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
