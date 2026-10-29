# Empaquetado y distribución

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

El workflow `.github/workflows/release.yml` construye el paquete en **Debian 12**
(glibc 2.36), extrae el `.tar.gz`, prueba el binario (`--version` y
`validate --strict`) y:

| Disparador | Resultado |
|---|---|
| Etiqueta `vX.Y.Z` | Crea la Release `vX.Y.Z` con el `.tar.gz` y su `.sha256` |
| *Run workflow* (manual) | Deja el paquete como artefacto de la ejecución |

La etiqueta debe coincidir con `version` de `pyproject.toml`; si no, el workflow
falla antes de construir. Para publicar una versión:

```bash
git tag v0.4.0          # la versión de pyproject.toml
git push origin v0.4.0
```

## Lanzador de escritorio

En Linux PyInstaller no incrusta iconos en el binario. Para tener AppForge en el menú
de aplicaciones, crea un lanzador que abra una terminal:

```ini title="~/.local/share/applications/appforge.desktop"
[Desktop Entry]
Type=Application
Name=AppForge
Comment=Recetas de configuración
Exec=/ruta/a/appforge/appforge
Icon=/ruta/a/appforge/appforge.png
Terminal=true
Categories=System;Utility;
```

Los iconos en otros tamaños están en `src/appforge/resources/`
(`appforge-{32,48,64,128,256,512}.png`, esquinas transparentes).

## Notas

| Tema | Detalle |
|---|---|
| glibc | El binario enlaza con la glibc del sistema donde se construye: compila en la distro más antigua donde vaya a ejecutarse (la CI usa Debian 12) |
| Textual | Importa sus widgets de forma perezosa; por eso el build usa `--collect-submodules textual` y `--collect-data textual` |
| Intermedios | En `build/` (ignorado por git) |
| Sin binario | `uv run appforge` con `APPFORGE_HOME` apuntando a la carpeta con `config.toml` |
