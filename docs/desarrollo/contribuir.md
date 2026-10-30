# Contribuir

## Entorno

Necesitas [uv](https://docs.astral.sh/uv/); descarga Python 3.13 si no lo tienes.

```bash
git clone https://github.com/isidro-rodriguez/appforge.git
cd appforge
uv sync                        # dependencias de desarrollo
uv sync --group docs           # además, las de esta web
uv run pre-commit install      # comprobaciones antes de cada commit y push
```

`uv` gestiona todo: un `uv.lock` y un entorno en la raíz. No uses `pip install`.

## Ejecutar desde el código

Desde el código, AppForge busca `config.toml` en el **directorio de trabajo** y
registra en `logs/`. La TUI solo funciona como superusuario: sin root, `uv run
appforge` pide la contraseña de `sudo` y se relanza (el binario del paquete, en
cambio, sale con un error).

```bash
uv run appforge                               # TUI con las recetas de entries/ (pide sudo)
uv run appforge validate --strict             # sin sudo: solo lee ficheros
```

Acepta las recetas de tu copia de trabajo porque son tuyas (`SUDO_UID`); solo deben
no ser escribibles por grupo ni otros (`chmod -R go-w entries`).

## Calidad

Lo mismo que ejecuta la CI:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check --error-on-warning
uv run pytest
```

Con [Poe the Poet](https://poethepoet.natn.io/) instalado globalmente hay atajos:

| Tarea | Equivale a |
|---|---|
| `poe check` | Formato, lint, tipos y tests |
| `poe fix` | `ruff format` + `ruff check --fix` |
| `poe build` | Binario, `config.toml` y `entries/` en `dist/` (carpeta y `.tar.gz`) |
| `poe screenshots` | Capturas de la TUI para esta web |
| `poe docs` | Vista previa de la web |
| `poe backup` | `git bundle` del repositorio |

## Convenciones

- Código e identificadores en **inglés**; docstrings, comentarios, mensajes y
  documentación en **español**.
- Docstrings estilo Google en todo lo público (`ruff` con las reglas `D`) y tipos
  estrictos (`ty`).
- Los mensajes que ve el usuario (CLI, TUI, eventos del motor) en español.

## Tests

- `pytest` con `--import-mode=importlib`: los tests no importan `conftest`; las
  utilidades son fixtures (`home`, `config`, `write_entry`, `sink`).
- `home` copia `entries/` a un temporal con un `config.toml` por defecto (nunca el
  del repositorio, que es configuración tuya), entra en él (`chdir`) y simula ser
  superusuario.
- Nunca se tocan rutas reales del sistema: *dry-run* para las recetas del repositorio y
  destinos en `tmp_path` para el motor.
- La TUI se prueba con `App.run_test()` y Pilot.

## Documentación

Esta web se genera con [Zensical](https://zensical.org/) a partir de `docs/` y
`zensical.toml`.

```bash
uv run --group docs zensical serve     # http://localhost:8000 con recarga
uv run --group docs zensical build     # sitio estático en site/
uv run python scripts/screenshots.py   # regenera las capturas de la TUI
```

Las capturas son SVG generados por Textual con entradas de demostración
inofensivas: regéneralas cuando cambie la interfaz. La referencia de la [API](api.md)
sale de los docstrings con mkdocstrings.

Cada push a `main` que toque `docs/`, `src/` o `zensical.toml` publica la web en
GitHub Pages (`.github/workflows/docs.yml`).

## Commits y versiones

- [Conventional Commits](https://www.conventionalcommits.org/es/) en español
  (`feat:`, `fix:`, `docs:`, `test:`, `chore:`), atómicos, explicando el porqué.
- Versionado [SemVer](https://semver.org/lang/es/) en `pyproject.toml` y
  [`CHANGELOG.md`](../changelog.md) al día antes de publicar. Cambiar el formato de
  las recetas de forma incompatible es una versión mayor.
