Instala [Ollama](https://ollama.com) para ejecutar modelos de lenguaje en local,
**sin servicio de arranque**: no consume memoria ni GPU hasta que lo enciendes.

La versión es un parámetro: se descarga de las Releases de Ollama en GitHub y se
**verifica con su `sha256sum.txt`**; sin suma publicada no se instala. Para
actualizar, vuelve a aplicar la receta con otra versión.

### Qué deja instalado

- Binario y librerías en `/opt/ollama`; modelos en `/opt/ollama/models`, propiedad
  del usuario que ejecutó `sudo appforge`.
- Un lanzador **Ollama** en el menú de aplicaciones que hace de interruptor:
  la primera pulsación arranca `ollama serve` y la siguiente lo detiene. Cada
  cambio se anuncia con una notificación del escritorio.

### Ajustes de rendimiento

Se escriben en `/opt/ollama/ollama.env` y los aplica el interruptor:

- *Flash attention* activado y caché K/V cuantizada (`q8_0`): menos VRAM por
  token de contexto.
- Contexto de 8192 tokens y un solo modelo cargado a la vez.
- `OLLAMA_KEEP_ALIVE=30m`: el modelo sigue en memoria media hora sin uso.

### Uso

Pulsa el lanzador y, cuando aparezca «Servicio activo», usa `ollama run <modelo>`
o cualquier cliente que apunte a `OLLAMA_HOST`.

Desinstalar detiene el servicio y borra todo **menos** `/opt/ollama/models`: los
modelos pesan gigas y no hace falta volver a descargarlos.

### Limitaciones

- GPU AMD: el tarball ROCm (`ollama-linux-amd64-rocm`) es distinto y la receta no
  lo usa todavía.

Variables de entorno de referencia:
[`envconfig/config.go`](https://github.com/ollama/ollama/blob/main/envconfig/config.go)
y la [FAQ de Ollama](https://docs.ollama.com/faq).
