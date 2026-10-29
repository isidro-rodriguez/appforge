# Empaquetado y publicación

## Paquete `.deb`

En Debian (hace falta `dpkg-deb`):

```bash
uv run python scripts/build.py              # o: poe build
uv run python scripts/build.py --binary-only  # solo el binario, en build/bin/
```

El binario sale de [PyInstaller](https://pyinstaller.org/) `--onefile` (~18 MB,
incluye Python y Textual) y el paquete, `dist/appforge_<versión>_amd64.deb` con
`dist/SHA256SUMS`, instala:

| Ruta | Contenido |
|---|---|
| `/opt/appforge/appforge` | Binario |
| `/usr/bin/appforge` | Enlace al binario |
| `/etc/appforge/config.toml` | Configuración (*conffile*) |
| `/etc/appforge/entries/` | Recetas de `entries/` (*conffiles*) |
| `/var/log/appforge/` | Registro; `postrm` lo borra al purgar |
| `/usr/share/man/man1/appforge.1.gz` | Página `man`, de `packaging/appforge.1` |
| `/usr/share/applications/appforge.desktop` | Lanzador, de `packaging/appforge.desktop` |
| `/usr/share/icons/hicolor/*/apps/appforge.png` | Iconos de `src/appforge/resources/` |
| `/usr/share/doc/appforge/` | Licencia y changelog |

Todo es de `root` (`dpkg-deb --root-owner-group`) y nadie más puede escribirlo. Como
*conffiles*, `config.toml` y las recetas conservan los cambios locales al actualizar;
`apt remove` los deja y `apt purge` los borra.

El binario empaquetado lee siempre `/etc/appforge/config.toml` y registra en
`/var/log/appforge/`. Desde el código usa el directorio de trabajo
(ver [Contribuir](contribuir.md#ejecutar-desde-el-código)).

### Lanzador

`appforge.desktop` abre AppForge en una terminal con `sudo appforge`: `sudo` pide la
contraseña en la terminal. No hay elevación gráfica (`pkexec` y similares).

### Página `man`

Se mantiene en `packaging/appforge.1` (roff); `build.py` sustituye `@VERSION@` y
`@DATE@`. Vista previa: `man -l packaging/appforge.1`.

## Publicación automática

El workflow `.github/workflows/release.yml` construye el paquete en un contenedor de
**Debian 13** (la estable actual) y lo prueba en otro Debian 13 limpio: instala,
versión, enlace, `validate --strict`, `man`, `.desktop`, propietario y permisos, TUI
sin root y sin terminal, reinstalación conservando un *conffile* modificado,
desinstalación y purga sin restos. Después:

| Disparador | Resultado |
|---|---|
| Etiqueta `vX.Y.Z` | Crea la Release `vX.Y.Z` con el `.deb`, `SHA256SUMS` y la procedencia |
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
| Sin binario | `uv run appforge` desde la raíz del repositorio: pide la contraseña de `sudo` y busca `config.toml` en el directorio de trabajo |

## Procedencia

Al publicar, el workflow firma con
[`actions/attest-build-provenance`](https://github.com/actions/attest-build-provenance)
una atestación del `.deb`: quién lo construyó, en qué workflow y desde qué commit. Se
verifica con `gh attestation verify` (ver [Seguridad](../avanzado/seguridad.md#verificar-el-paquete)).
