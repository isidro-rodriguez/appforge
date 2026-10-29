# Primeros pasos

Este recorrido usa la receta de [Ollama](ollama.md), que viene incluida. Ningún paso
cambia nada en tu sistema hasta el final, y ese paso es opcional.

## 1. Abre el catálogo

```bash
sudo appforge          # o: sudo /opt/appforge/appforge
```

<figure class="af-shot" markdown>
![Catálogo sin buscador ni categorías](../assets/images/screenshots/catalogo-simple.svg)
<figcaption>Vista por defecto: lista de recetas y ficha de la resaltada.</figcaption>
</figure>

Cada fila tiene una **casilla** de selección, el nombre y una etiqueta:

| Etiqueta | Significado |
|---|---|
| `aplicada` | Su comprobación (`[check]`) pasa: ya está en tu sistema |
| `·` | No aplicada |
| `…` | Comprobando |
| `inválida` | La receta tiene errores; la ficha dice cuáles |

Muévete con las flechas. La ficha de la derecha resume la receta resaltada.

## 2. Lee la receta completa

Haz **doble clic** sobre *Ollama* o pulsa ++v++.

<figure class="af-shot" markdown>
![Página de detalle de Ollama](../assets/images/screenshots/detalle.svg)
<figcaption>La ficha completa: descripción, parámetros, cada paso, comprobación y eliminación.</figcaption>
</figure>

Es lo mismo que hay en el TOML, pero legible. ++esc++ vuelve al catálogo.

## 3. Prueba sin tocar nada

Pulsa ++d++ (*dry-run*). AppForge te pide los parámetros de la receta:

<figure class="af-shot" markdown>
![Formulario de parámetros](../assets/images/screenshots/parametros.svg)
<figcaption>Los campos vacíos usan el valor por defecto que se ve en gris.</figcaption>
</figure>

Escribe tu usuario en el primero y acepta. La pantalla de progreso enseña cada
comando que se ejecutaría (precedido de `#`) y el **diff** de cada fichero
que se escribiría. Al terminar, ++esc++ vuelve al catálogo.

## 4. Instala por lotes

Marca varias recetas con ++space++ y pulsa ++i++. AppForge pide los parámetros de
cada una y confirma la lista antes de empezar.

<figure class="af-shot" markdown>
![Confirmación del lote](../assets/images/screenshots/confirmar.svg)
</figure>

<figure class="af-shot" markdown>
![Lote completado](../assets/images/screenshots/progreso-final.svg)
<figcaption>Las recetas que terminan bien se desmarcan. ++ctrl+c++ cancela; ++l++ abre el registro completo.</figcaption>
</figure>

Si una receta falla, el lote sigue con la siguiente y la fila queda en rojo. El
registro dice en qué paso se detuvo; corrige y vuelve a aplicarla (los pasos se
pueden repetir).

## 5. Desinstala

Resalta (o marca) una receta aplicada y pulsa ++u++: se ejecuta su `[remove]`.

## Siguientes pasos

- Activa el [buscador y las categorías](../avanzado/configuracion.md#interfaz).
- Consulta todas las teclas en [Interfaz](interfaz.md).
- Escribe [tu primera receta](../desarrollo/nueva-entrada.md).
