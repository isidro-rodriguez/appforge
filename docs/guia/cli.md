# Línea de comandos

Todo lo que hace la TUI está también disponible como subcomandos, útiles para
scripts o para una sola receta. Sin subcomando, `appforge` abre la TUI.

| Comando | Qué hace | Código de salida |
|---|---|---|
| `appforge list` | Lista las recetas con su estado | 0 |
| `appforge show ID` | Parámetros, pasos y problemas de una receta | 0 válida · 1 inválida |
| `appforge check ID` | Ejecuta su `[check]` | 0 aplicada · 1 no · 2 sin check o inválida |
| `appforge apply ID` | Aplica la receta | 0 bien · 1 error |
| `appforge remove ID` | Ejecuta su `[remove]` | 0 bien · 1 error |
| `appforge --version` | Versión | 0 |

`ID` es el nombre del fichero sin `.toml` (`ollama` para `entries/ollama.toml`).

## Opciones de `apply` y `remove`

| Opción | Efecto |
|---|---|
| `-n`, `--dry-run` | Muestra comandos y diffs sin cambiar nada |
| `-s`, `--set NOMBRE=VALOR` | Da un parámetro; se puede repetir (solo `apply`) |
| `--no-input` | No preguntar: usa `--set` y los valores por defecto (solo `apply`) |

Sin `--no-input`, en una terminal se preguntan los parámetros que falten; los
secretos se piden sin eco.

## Ejemplos

```bash
# Qué hay y qué está aplicado
appforge list

# Ver qué haría la receta de Ollama, sin preguntas
appforge apply ollama -n --no-input -s owner="$USER"

# Aplicarla de verdad con otro puerto
appforge apply ollama -s owner="$USER" -s host=127.0.0.1:11500

# En un script: instalar solo si falta
appforge check ollama || appforge apply ollama --no-input -s owner="$USER"
```

```text title="Salida de un dry-run"
  Estado actual: no aplicada
==> [1/7] Dependencias (curl, zstd, notify-send) [dry-run]
  │ # DEBIAN_FRONTEND=noninteractive apt-get install -y curl zstd libnotify-bin
==> [4/7] Variables de entorno (optimización) [dry-run]
  crear /opt/ollama/ollama.env (modo 0644, 276 bytes)
  │ +OLLAMA_MODELS=/opt/ollama/models
  │ +OLLAMA_HOST=127.0.0.1:11434
✔ Dry-run completado: no se ha cambiado nada
```

La CLI usa los colores de AppForge en una terminal y respeta `NO_COLOR`. Los
errores van a la salida de error.
