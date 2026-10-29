# Qué pasa al aplicar una receta

## Flujo

```mermaid
flowchart TD
    A[Receta válida?] -->|no| X[Muestra los problemas y no hace nada]
    A -->|sí| B[Resuelve parámetros]
    B --> E["[check]: estado actual"]
    E --> F[Pasos en orden]
    F -->|un paso falla| Y[Se detiene e indica cuál]
    F -->|todos bien| G["[check] otra vez"]
    G -->|pasa| OK[Aplicada y verificada]
    G -->|falla| W[Aviso: los pasos no dejaron el resultado esperado]
```

1. Si la receta tiene problemas de validación, se muestran y no se hace nada.
2. Cada parámetro toma el valor dado o su `default`; si falta alguno, error.
3. `[check]` informa del estado actual.
4. Los pasos se ejecutan en orden. El primero que falla detiene la receta.
5. `[check]` se repite: si sigue fallando, AppForge avisa de que la receta no dejó el
   resultado esperado.

Una receta detenida a medias puede volver a aplicarse: los pasos están pensados para
repetirse (ver [buenas prácticas](../desarrollo/buenas-practicas.md)).

## Privilegios

AppForge solo se ejecuta como superusuario, así que todo (pasos, `[check]` y
`[remove]`) corre como `root`, sin `sudo` ni contraseñas a mitad de lote.

## Parámetros y secretos

- Nunca se guardan. Solo existen en un fichero temporal `0600` que se borra al
  terminar el paso.
- Ese fichero lleva los `export` y el código del paso, así los valores **no aparecen
  en `ps`** (no van en la línea de comandos).
- Los valores de los parámetros `secret = true` se sustituyen por `••••••` en toda la
  salida: pantalla, registro y diffs del *dry-run*.

## Ficheros (`template` y `copy`)

| Caso | Acción |
|---|---|
| El destino no existe | Se crea con sus directorios (`install -D`) y el modo indicado |
| Contenido idéntico | «sin cambios»: no se reescribe ni se copia; solo se reaplica el modo |
| Contenido distinto | Copia del original en `<destino>.backup` (mismos permisos; reemplaza la copia anterior) y se escribe |

La copia queda anotada en el registro. Para recuperar el fichero anterior:

```bash
sudo cp -p /etc/ssh/sshd_config.d/50-appforge.conf.backup /etc/ssh/sshd_config.d/50-appforge.conf
```

## Dry-run

- `run`, `script` y `[remove]` se **muestran** (precedidos de `#`), no se ejecutan.
- `template` y `copy` calculan el contenido final y muestran un **diff** contra el
  destino actual.
- `[check]` **sí** se ejecuta (por eso debe ser de solo lectura).

## Cancelación

++ctrl+c++ en la pantalla de progreso termina el comando en curso **y todo lo que
haya lanzado**, y no empieza más pasos ni recetas.

Para conseguirlo, cada paso corre en un subshell con su propio grupo de procesos;
bash no atiende una señal mientras espera a un comando, pero `wait` sí:

```bash
set -m                                  # grupo de procesos propio
( <código del paso> ) &
trap 'kill -TERM -- "-$hijo"' TERM INT
wait "$hijo"
```

Como ante un fallo, una receta cancelada puede quedar a medias.

## Registro

Cada evento de la TUI se añade a `logs/appforge.log`, junto al binario, con fecha,
nivel e id de la receta:

```text
2026-10-29 18:10:03 INFO       ollama [tpl ] [4/7] Variables de entorno (optimización)
2026-10-29 18:10:03 INFO       ollama [tpl ] copia de seguridad: /opt/ollama/ollama.env.backup
2026-10-29 18:10:03 INFO       ollama [tpl ] escrito /opt/ollama/ollama.env (0644)
2026-10-29 18:10:04 WARNING    docker [run ] Pasos completados, pero [check] sigue fallando
```

El fichero rota a medianoche y se guardan 7 días. En la TUI, ++l++ lo abre.
