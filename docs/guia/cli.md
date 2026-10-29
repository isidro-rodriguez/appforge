# Línea de comandos

Todo lo interactivo (ver el catálogo, instalar, desinstalar, *dry-run*) se hace en la
[TUI](interfaz.md), que también funciona en cualquier consola. La línea de comandos
solo tiene lo que no cabe en ella:

| Comando | Qué hace | `sudo` | Código de salida |
|---|---|---|---|
| `appforge` | Abre la TUI | sí | 0 · 2 sin superusuario, sin terminal o `config.toml` inválido |
| `appforge validate [ID...]` | Revisa las recetas sin ejecutarlas | no | 0 bien · 1 errores · 2 uso |
| `appforge --version`, `-V` | Versión | no | 0 |
| `appforge --help`, `-h` | Ayuda (también `appforge validate -h`) | no | 0 |

`ID` es el nombre del fichero sin `.toml` (`ollama` para `entries/ollama.toml`).

![Ayuda de la línea de comandos](../assets/images/screenshots/cli-ayuda.svg){ .af-shot }

## `appforge validate`

Revisa todas las recetas (o las indicadas) **sin ejecutar nada**: solo lee los
ficheros y comprueba la sintaxis con `bash -n`, así que **no necesita `sudo`**. Úsalo al escribir una receta o en la
CI de tu repositorio de recetas.

| Opción | Efecto |
|---|---|
| `-d`, `--dir DIR` | Valida otro directorio de recetas en lugar del de `config.toml` |
| `-s`, `--strict` | Los avisos también hacen fallar (código 1) |

**Errores** (la receta no se puede aplicar o fallaría):

| Comprobación | Ejemplo de mensaje |
|---|---|
| TOML, claves y tipos | `step #2: necesita exactamente uno de run, template, copy, script` |
| Seguridad (permisos, propietario, enlaces) | `entries/x.toml: escribible por grupo u otros` |
| Ficheros de los pasos | `step #3: falta el fichero ollama/ollama.png` |
| Plantillas | `step #4: la plantilla usa parámetros inexistentes: port` |
| Sintaxis de bash en `run`, `[check]`, `[remove]` y scripts | `step #2: error de sintaxis: …` |
| Referencias `$APPFORGE_ENTRY_DIR/<fichero>` | `[remove]: usa $APPFORGE_ENTRY_DIR/borra.sh, pero no existe x/borra.sh` |

**Avisos** (se puede aplicar, pero algo sobra o falta):

| Comprobación | Ejemplo de mensaje |
|---|---|
| Ficheros del subdirectorio que nada usa | `fichero sin usar: x/viejo.conf` |
| Parámetros que ningún comando ni plantilla usa | `parámetro sin usar: port` |
| Sin `description`, `[check]` o `[remove]` | `sin [check]: su estado siempre será desconocido` |
| Dos recetas con el mismo `name` | `nombre repetido en 2 entradas: Docker` |
| Subdirectorio sin su `.toml` | `docker/: subdirectorio sin docker.toml` |

```bash
appforge validate                      # todas
appforge validate ollama fonts         # solo esas
appforge validate --strict             # en la CI: sin errores ni avisos
appforge validate -d ~/mis-recetas     # otro directorio
```

![Salida de appforge validate con una receta rota](../assets/images/screenshots/cli-validate.svg){ .af-shot }

La línea de comandos usa los colores de AppForge en una terminal y respeta
`NO_COLOR`. Los errores de uso van a la salida de error. `man appforge` resume todo
esto.
