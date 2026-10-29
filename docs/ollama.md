# Entrada de ejemplo: Ollama

`entries/ollama.toml` instala [Ollama](https://ollama.com) en `/opt/ollama`, sin servicio
de arranque, con un lanzador de escritorio que actúa de interruptor on/off.

## Resultado

| Ruta | Contenido |
|---|---|
| `/opt/ollama/bin/`, `lib/` | Binario y librerías del tarball oficial |
| `/opt/ollama/models/` | Modelos (`OLLAMA_MODELS`), propiedad del usuario `owner` |
| `/opt/ollama/ollama.env` | Variables de optimización (plantilla) |
| `/opt/ollama/ollama-toggle.sh` | Switcher on/off |
| `/opt/ollama/ollama.png` | Icono (`entries/ollama/ollama.png`, 256 px) |
| `/usr/local/share/applications/ollama.desktop` | Lanzador |

## Switcher

- Si `ollama serve` está en marcha (para el usuario actual), lo detiene.
- Si no, lo arranca en segundo plano, espera hasta 15 s a que responda `/api/version` y
  notifica con `notify-send`.
- Log: `~/.local/state/ollama/serve.log`.

## Parámetros

| Parámetro | Por defecto | Uso |
|---|---|---|
| `owner` | — | Dueño de `/opt/ollama/models` |
| `arch` | `amd64` | `amd64` o `arm64` |
| `host` | `127.0.0.1:11434` | `OLLAMA_HOST` |
| `keep_alive` | `30m` | `OLLAMA_KEEP_ALIVE` (`-1` = siempre cargado) |
| `kv_cache` | `q8_0` | `OLLAMA_KV_CACHE_TYPE` (`f16`, `q8_0`, `q4_0`) |
| `context_length` | `8192` | `OLLAMA_CONTEXT_LENGTH` |

Fijos en la plantilla: `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_MAX_LOADED_MODELS=1`,
`OLLAMA_NUM_PARALLEL=1`.

## `[remove]`

Detiene el servicio y borra todo **menos** `/opt/ollama/models`.

## Pendiente

- GPU AMD: el tarball ROCm es distinto (`ollama-linux-amd64-rocm`).

## Fuentes

- Variables de entorno: [`envconfig/config.go`](https://github.com/ollama/ollama/blob/main/envconfig/config.go) y [FAQ de Ollama](https://docs.ollama.com/faq)
