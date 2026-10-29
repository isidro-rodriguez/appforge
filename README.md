<p align="center"><img src="src/appforge/resources/appforge-128.png" alt="AppForge" width="96"></p>

# appforge

Menú de consola que centraliza recetas de configuración repetibles: cada opción es un
fichero TOML que instala y configura una aplicación (ejemplo incluido: Ollama bajo
demanda). Hecho con [Textual](https://textual.textualize.io/) y las herramientas de
[Astral](https://astral.sh) (`uv`, `ruff`, `ty`).

## 🚀 Instalación

```bash
git clone <repo> appforge
cd appforge
uv sync
```

## 🛠️ Uso

```bash
uv run appforge                          # menú: espacio marca, i instala, v detalle
uv run appforge list                     # entradas y estado (✔ aplicada)
uv run appforge apply ollama -n          # dry-run: muestra qué haría
uv run appforge apply ollama             # aplica (pide parámetros y sudo)
uv run python scripts/build.py           # binario en dist/appforge/
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

**<https://isidro-rodriguez.github.io/appforge/>** — guía de uso, uso avanzado y
cómo crear recetas. Fuente en [`docs/`](docs/); vista previa local con
`uv run --group docs zensical serve`.

- Desarrollo: [CLAUDE.md](CLAUDE.md) · Nuevas recetas: [AGENTS.md](AGENTS.md)

## Licencia

[MIT](LICENSE).
