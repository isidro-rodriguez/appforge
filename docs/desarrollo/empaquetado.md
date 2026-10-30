# Empaquetado y publicación

## Paquete

```bash
uv run python scripts/build.py      # o: poe build
```

El binario sale de [PyInstaller](https://pyinstaller.org/) `--onefile` (~18 MB,
incluye Python y Textual). En `dist/` quedan:

| Fichero | Contenido |
|---|---|
| `appforge/` | `appforge` (binario), `config.toml` y `entries/`, lista para copiar |
| `appforge-<versión>-linux-x86_64.tar.gz` | Esa carpeta empaquetada, con los ficheros a nombre de `root` y sin escritura para grupo ni otros |
| `SHA256SUMS` | Suma del `.tar.gz` para `sha256sum -c` |

Se instala extrayéndolo con `sudo tar -xzf … -C /opt`: así queda en `/opt/appforge`, de
`root`. El binario busca `config.toml` en su propia carpeta, aunque se lance desde un
enlace, y escribe el registro en `logs/` dentro de ella. Desde el código usa el
directorio de trabajo (ver [Contribuir](contribuir.md#ejecutar-desde-el-código)).

## Publicación automática

El workflow `.github/workflows/release.yml` construye el paquete en un contenedor de
**Debian 13** (la estable actual) y lo prueba en otro Debian 13 limpio: verifica la
suma, lo extrae en `/opt`, y comprueba versión, contenido, `validate --strict`,
propietario y permisos, un enlace en el `PATH` y la TUI sin root y sin terminal.
Después:

| Disparador | Resultado |
|---|---|
| Etiqueta `vX.Y.Z` | Crea la Release `vX.Y.Z` con el `.tar.gz`, `SHA256SUMS` y la procedencia |
| *Run workflow* (manual) | Deja el paquete como artefacto de la ejecución |
| *Run workflow* con **publish** en `main` | Crea la etiqueta `vX.Y.Z` (versión de `pyproject.toml`) sobre ese commit y su Release |

La etiqueta debe coincidir con `version` de `pyproject.toml`; si no, el workflow
falla antes de construir. Las notas de la Release salen de la sección de esa versión
en `CHANGELOG.md`. Para publicar una versión, una de las dos:

```bash
git tag v0.6.1 && git push origin v0.6.1                     # etiqueta propia
gh workflow run release.yml --ref main -f publish=true       # la crea el workflow
```

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
una atestación del `.tar.gz`: quién lo construyó, en qué workflow y desde qué commit. Se
verifica con `gh attestation verify` (ver [Seguridad](../avanzado/seguridad.md#verificar-el-paquete)).
