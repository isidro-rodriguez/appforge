# Configuración

## Dónde está

AppForge lee `config.toml` del directorio del binario (`/opt/appforge/` si seguiste la
[instalación](../guia/instalacion.md)). Todas las rutas relativas se resuelven desde
ahí.

## `config.toml`

```toml title="config.toml"
# Relativo al directorio del binario.
entries_dir = "entries"

[ui]
search = false       # buscador sobre la lista
categories = false   # panel de categorías
```

| Clave | Tipo | Por defecto | Descripción |
|---|---|---|---|
| `entries_dir` | ruta | — (obligatoria) | Directorio de recetas, relativo al del binario. Debe existir |
| `[ui] search` | bool | `false` | Muestra el buscador (++slash++) |
| `[ui] categories` | bool | `false` | Muestra el panel de categorías |

Cualquier clave desconocida o de tipo incorrecto es un error: AppForge no arranca y
dice cuál (código de salida 2). Así una errata como `categores = true` no pasa
desapercibida.

### Interfaz

Con pocas recetas basta la lista. Cuando crecen, activa las dos ayudas:

```toml
[ui]
search = true
categories = true
```

<figure class="af-shot" markdown>
![Catálogo con buscador y categorías](../assets/images/screenshots/catalogo.svg)
</figure>

Las categorías salen de la clave [`category`](../desarrollo/formato.md#cabecera) de
cada receta; las que no la tienen se agrupan en «Sin categoría».

## Qué escribe AppForge

AppForge no guarda estado propio: si una receta está aplicada lo dice siempre su
`[check]`. Solo escribe dos cosas:

| Ruta | Contenido |
|---|---|
| `<fichero>.backup`, junto al original | Copia de un fichero antes de que `template` o `copy` lo sobrescriba. Mismos permisos que el original; si ya había una, se reemplaza |
| `logs/appforge.log`, junto al binario | Registro de todas las ejecuciones, copias incluidas; rota cada día y guarda 7 |

## Colores

La línea de comandos respeta `NO_COLOR`: con la variable definida no usa colores.
