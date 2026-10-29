# Receta incluida: Ollama bajo demanda

`entries/ollama.toml` instala [Ollama](https://ollama.com) para ejecutar modelos de
lenguaje en local **sin servicio de arranque**: no ocupa memoria ni GPU hasta que lo
enciendes. Un lanzador del escritorio hace de interruptor.

<figure class="af-shot" markdown>
![Página de detalle de la receta de Ollama](../assets/images/screenshots/detalle.svg)
</figure>

## Uso

1. Aplica la receta (en la TUI ++i++, o `appforge apply ollama`). Pide tu usuario,
   que será el dueño de la carpeta de modelos.
2. En el menú de aplicaciones aparece **Ollama**. Al pulsarlo arranca el servicio y
   una notificación avisa cuando responde («Servicio activo en …»).
3. Usa `ollama run <modelo>` o cualquier cliente que apunte a `OLLAMA_HOST`.
4. Vuelve a pulsar el lanzador para detenerlo («Servicio detenido»).

## Qué deja instalado

| Ruta | Contenido |
|---|---|
| `/opt/ollama/bin/`, `lib/` | Binario y librerías del tarball oficial |
| `/opt/ollama/models/` | Modelos (`OLLAMA_MODELS`), propiedad del usuario `owner` |
| `/opt/ollama/ollama.env` | Variables de rendimiento (plantilla) |
| `/opt/ollama/ollama-toggle.sh` | Interruptor on/off |
| `/opt/ollama/ollama.png` | Icono |
| `/usr/local/share/applications/ollama.desktop` | Lanzador |

El interruptor, si `ollama serve` está en marcha para tu usuario, lo detiene. Si no,
lo arranca en segundo plano, espera hasta 15 s a que responda `/api/version` y lo
notifica con `notify-send`. Su log está en `~/.local/state/ollama/serve.log`.

## Parámetros

| Parámetro | Por defecto | Uso |
|---|---|---|
| `owner` | — | Dueño de `/opt/ollama/models` |
| `arch` | `amd64` | `amd64` o `arm64` |
| `host` | `127.0.0.1:11434` | `OLLAMA_HOST` |
| `keep_alive` | `30m` | `OLLAMA_KEEP_ALIVE` (`-1` = siempre cargado) |
| `kv_cache` | `q8_0` | `OLLAMA_KV_CACHE_TYPE` (`f16`, `q8_0`, `q4_0`) |
| `context_length` | `8192` | `OLLAMA_CONTEXT_LENGTH` |

Fijos en la plantilla: `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_MAX_LOADED_MODELS=1` y
`OLLAMA_NUM_PARALLEL=1`, pensados para un solo usuario con una GPU de consumo.

!!! tip "Cambiar los ajustes"

    Vuelve a aplicar la receta con otros valores: solo se reescribe
    `ollama.env` (con copia de seguridad del anterior) y el resto de pasos quedan
    «sin cambios».

## Desinstalar

`[remove]` detiene el servicio y borra todo **menos** `/opt/ollama/models`: los
modelos pesan gigas y no hace falta volver a descargarlos.

## Limitaciones

- GPU AMD: el tarball ROCm es distinto (`ollama-linux-amd64-rocm`) y la receta no lo
  usa todavía.

Variables de entorno de referencia:
[`envconfig/config.go`](https://github.com/ollama/ollama/blob/main/envconfig/config.go)
y la [FAQ de Ollama](https://docs.ollama.com/faq).
