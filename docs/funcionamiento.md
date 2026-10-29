# Funcionamiento del motor

## Arquitectura

| Módulo | Responsabilidad |
|---|---|
| `config.py` | Localiza el directorio base y lee `config.toml` |
| `entry.py` | Carga y valida entradas; nunca lanza excepción, acumula `problems` |
| `engine.py` | Ejecuta `[check]`, pasos y `[remove]`; root, copias, dry-run |
| `main.py` | CLI (`argparse`); sin subcomando abre la TUI |
| `tui.py` | TUI Textual: menú, formulario de parámetros, log en vivo |

El motor no imprime nada: envía eventos `sink(kind, text)` (`step`, `out`, `info`, `ok`,
`warn`, `error`) que la CLI pinta en la consola y la TUI en un `RichLog`.

## Directorio base y `config.toml`

| Prioridad | Origen |
|---|---|
| 1 | Variable `APPFORGE_HOME` |
| 2 | Directorio del binario, si está empaquetado (`sys.frozen`, ver [PyInstaller](https://pyinstaller.org/en/stable/runtime-information.html)) |
| 3 | Directorio de trabajo |

```toml
entries_dir = "entries"                           # relativo al directorio base
# backups_dir = "~/.local/state/appforge/backups" # por defecto ($XDG_STATE_HOME)
```

## Flujo de `apply`

1. Si la entrada tiene problemas, se muestran y no se hace nada.
2. Se resuelven los parámetros (valores dados o `default`; si falta alguno, error).
3. Si `requires_root`, se pide la contraseña una vez con `sudo -v`; la TUI se suspende
   con [`App.suspend()`](https://textual.textualize.io/api/app/#textual.app.App.suspend).
4. Se informa del estado actual (`[check]`).
5. Pasos en orden; el primero que falla detiene todo e indica cuál.
6. Se vuelve a ejecutar `[check]`: si falla, se avisa de que no quedó aplicada.

## Estado

No hay fichero de estado: se deriva siempre de `[check]`. Sin `[check]` la entrada se
muestra con `·`.

## Root

| Situación | Comportamiento |
|---|---|
| Usuario normal + `requires_root` | Cada paso se ejecuta con `sudo -n` tras un `sudo -v` inicial |
| Ya root | Sin prefijo |
| `[check]` | Siempre sin root (no pide contraseña al pintar el menú) |
| Tests | `APPFORGE_SUDO=""` sustituye el prefijo |

## Parámetros y secretos

- Nunca se escriben en disco más allá de un fichero temporal `0600` que se borra al
  terminar el paso.
- Ese fichero contiene los `export` y el código: así los valores no aparecen en `argv`
  (visible en `ps`) y sobreviven a la limpieza de entorno de `sudo`.
- Los valores de `secret = true` se sustituyen por `••••••` en toda la salida, incluidos
  los diffs del dry-run.

## Ficheros (`template` / `copy`)

| Caso | Acción |
|---|---|
| Destino no existe | Se crea con `install -D -m <mode>` |
| Contenido idéntico | «sin cambios»; solo se reaplica el modo |
| Contenido distinto | Copia del original en `backups_dir/<id>/<AAAAMMDD-HHMMSS>/<ruta>` (`0600`) y se escribe |
| Destino no legible | Se lee con `sudo cat` si la entrada es de root |

## Dry-run

- `run`/`script`/`[remove]`: se muestran (`#` = con root, `$` = sin root), no se ejecutan.
- `template`/`copy`: se calcula el contenido y se muestra un diff unificado contra el
  destino actual.
- `[check]` **sí** se ejecuta (debe ser de solo lectura).
- No necesita root ni pide contraseña.

## Seguridad

Las entradas ejecutan comandos con privilegios, así que se tratan como código:

- Rechazo de ficheros escribibles por grupo u otros, de otro propietario o enlazados.
- Rutas de origen confinadas en `entries/<id>/`.
- Parámetros que no pueden sustituir variables críticas del entorno.
- Recomendación para autores: nada de `curl | bash`; descargar a fichero, verificar y
  ejecutar (ver [AGENTS.md](../AGENTS.md)).

## Límites de alcance

Cuatro tipos de paso, sin condicionales, bucles ni dependencias entre entradas, para no
convertir AppForge en un mini-Ansible. La lógica compleja va en un `script`.
