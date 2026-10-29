# Formato de las recetas

Referencia completa. Para un recorrido paso a paso, ver [Crear una receta](nueva-entrada.md).

Cada opción del catálogo es un fichero `entries/<id>.toml`. Si necesita ficheros adicionales
(plantillas, scripts, iconos) van en `entries/<id>/`. El `<id>` es el nombre del fichero
sin extensión y es lo que se usa en la CLI (`appforge apply <id>`).

```text
entries/
├── ollama.toml
└── ollama/
    ├── ollama.env.tpl
    ├── ollama-toggle.sh
    ├── ollama.desktop
    └── ollama.png
```

## Referencia

### Cabecera

| Clave | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `name` | texto | sí | Nombre en el menú |
| `description` | texto | no | Una línea: resumen en el catálogo y en la ficha |
| `details` | texto (Markdown) | no | Descripción larga para la [página de detalle](../guia/interfaz.md#página-de-detalle). Usa `"""…"""` |
| `category` | texto | no | Agrupa la receta en el panel de categorías ([`[ui] categories`](../avanzado/configuracion.md#interfaz)) |
| `requires_root` | bool | no (`false`) | Los pasos y `[remove]` se ejecutan con `sudo` |

### `[[param]]`

Valores que se piden antes de aplicar. No se guardan en disco.

| Clave | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `name` | identificador | sí | `[A-Za-z_][A-Za-z0-9_]*`; no puede ser `PATH`, `HOME`, `USER`, … ni empezar por `APPFORGE_` |
| `prompt` | texto | no (`name`) | Pregunta |
| `default` | escalar | no | Sin default, el parámetro es obligatorio |
| `secret` | bool | no (`false`) | Entrada oculta; el valor se enmascara (`••••••`) en toda la salida |

### `[check]`

```toml
[check]
run = "test -x /opt/x/bin/x"
```

Código de salida 0 = aplicada (`aplicada` en el catálogo). Se ejecuta **sin root** y con los valores
por defecto de los parámetros, al pintar el menú y después de aplicar o eliminar. Debe
comprobar el **resultado final**, no un paso intermedio.

### `[[step]]`

Exactamente una de estas claves por paso:

| Tipo | Valor | Claves extra | Qué hace |
|---|---|---|---|
| `run` | comando bash | — | Ejecuta el comando |
| `script` | fichero en `entries/<id>/` | — | `bash entries/<id>/<fichero>` |
| `template` | fichero en `entries/<id>/` | `dest`, `mode` | Sustituye `$param` y escribe en `dest` |
| `copy` | fichero en `entries/<id>/` | `dest`, `mode` | Copia tal cual a `dest` |

Todas admiten `title`. `dest` debe ser absoluta. `mode` es texto octal (`"0600"`); por
defecto conserva el del fichero existente o `0644`. Los directorios padre se crean.

Las plantillas usan [`string.Template`](https://docs.python.org/3/library/string.html#template-strings):
`$nombre` o `${nombre}`, y `$$` para un `$` literal. Usar un parámetro no declarado es
un error de validación.

### `[remove]`

```toml
[remove]
run = "rm -rf /opt/x"
```

Opcional. Tras ejecutarlo, `[check]` debe fallar.

## Variables disponibles en `run` y `script`

| Variable | Valor |
|---|---|
| `$<param>` | Valor de cada parámetro |
| `APPFORGE_ENTRY` | `<id>` |
| `APPFORGE_ENTRY_DIR` | Ruta absoluta de `entries/<id>/` |
| `APPFORGE_DRY_RUN` | `0` (en dry-run los comandos no se ejecutan) |

El directorio de trabajo es `entries/<id>/` si existe.

## Ejemplo mínimo

```toml
name = "Alias de git"
description = "Configura alias globales de git"
category = "Desarrollo"

[[param]]
name = "editor"
prompt = "Editor por defecto"
default = "nano"

[check]
run = "git config --global --get alias.st"

[[step]]
title = "Alias y editor"
run = """
git config --global alias.st status
git config --global core.editor "$editor"
"""

[remove]
run = "git config --global --unset alias.st"
```

## Validación

AppForge marca la receta como `inválida` (no se puede aplicar) si:

- el TOML no es válido o tiene claves desconocidas o de tipo incorrecto;
- un paso tiene cero o varios tipos, o un `dest`/`mode` donde no corresponde;
- un fichero de origen falta, es absoluto o contiene `..`;
- una plantilla usa parámetros no declarados o un `$` mal formado;
- el `.toml`, su subdirectorio o cualquier fichero dentro son escribibles por grupo u
  otros, pertenecen a otro usuario (que no sea root) o son enlaces simbólicos.

`appforge show <id>` y la ficha de la TUI listan todos los problemas. El porqué de cada comprobación está en [Seguridad](../avanzado/seguridad.md).
