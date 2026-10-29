# Empaquetado y publicación

## Binario

```bash
uv run python scripts/build.py      # o: poe build
```

Genera con [PyInstaller](https://pyinstaller.org/) `--onefile`:

```text
dist/appforge/
├── appforge        # binario (~18 MB, incluye Python y Textual)
├── appforge.png    # icono (256 px)
├── config.toml
└── entries/
```

La carpeta completa se puede copiar a cualquier sitio: el binario busca `config.toml`
junto a sí mismo. El script quita la escritura de grupo y otros de las recetas,
porque AppForge rechaza las inseguras.

## Paquete `.tar.gz`

```bash
uv run python scripts/build.py --archive
```

Además de la carpeta, crea en `dist/`:

| Fichero | Contenido |
|---|---|
| `appforge-<versión>-linux-<arquitectura>.tar.gz` | La carpeta `appforge/` completa, sin el usuario ni el grupo de quien la construye |
| `appforge-<versión>-linux-<arquitectura>.tar.gz.sha256` | Suma para `sha256sum -c` |

## Publicación automática

El workflow `.github/workflows/release.yml` construye el paquete en un contenedor de
**Debian 13** (la estable actual), extrae el `.tar.gz`, prueba el binario (`--version` y
`validate --strict`) y:

| Disparador | Resultado |
|---|---|
| Etiqueta `vX.Y.Z` | Crea la Release `vX.Y.Z` con el `.tar.gz` y su `.sha256` |
| *Run workflow* (manual) | Deja el paquete como artefacto de la ejecución |
| *Run workflow* con **publish** en `main` | Crea la etiqueta `vX.Y.Z` (versión de `pyproject.toml`) sobre ese commit y su Release |

La etiqueta debe coincidir con `version` de `pyproject.toml`; si no, el workflow
falla antes de construir. Las notas de la Release salen de la sección de esa versión
en `CHANGELOG.md`. Para publicar una versión, una de las dos:

```bash
git tag v0.6.1 && git push origin v0.6.1                     # etiqueta propia
gh workflow run release.yml --ref main -f publish=true       # la crea el workflow
```

Los iconos en otros tamaños están en `src/appforge/resources/`
(`appforge-{32,48,64,128,256,512}.png`, esquinas transparentes).

## Notas

| Tema | Detalle |
|---|---|
| glibc | El binario enlaza con la glibc del sistema donde se construye: por eso la CI compila en Debian 13 y no en `ubuntu-latest` |
| Textual | Importa sus widgets de forma perezosa; por eso el build usa `--collect-submodules textual` y `--collect-data textual` |
| Intermedios | En `build/` (ignorado por git) |
| Sin binario | `sudo .venv/bin/appforge` desde la raíz del repositorio: busca `config.toml` en el directorio de trabajo |
