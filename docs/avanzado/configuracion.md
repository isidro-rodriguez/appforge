# Configuración

## Dónde está

AppForge lee el `config.toml` que está junto al programa: `/opt/appforge/config.toml`
si lo extrajiste ahí. Las rutas relativas se resuelven desde esa carpeta, también si
lanzas AppForge desde un enlace (`/usr/local/bin/appforge`).

Se edita como superusuario (`sudo editor /opt/appforge/config.toml`). AppForge se
niega a arrancar si es un enlace simbólico o si lo pueden modificar otros usuarios.

## `config.toml`

```toml title="config.toml"
# Relativas a la carpeta de AppForge, en orden.
entries_dirs = ["appforge-entries", "custom-entries"]

[ui]
search = true        # buscador sobre la lista
categories = true    # panel de categorías
```

| Clave | Tipo | Por defecto | Descripción |
|---|---|---|---|
| `entries_dirs` | lista de rutas | — (obligatoria) | Directorios de recetas, en orden, relativos a la carpeta de AppForge (admite `~` y rutas absolutas). Deben existir |
| `[ui] search` | bool | `false` | Muestra el buscador (++slash++) |
| `[ui] categories` | bool | `false` | Muestra el panel de categorías |

Cualquier clave desconocida o de tipo incorrecto es un error: AppForge no arranca y
dice cuál (código de salida 2). Así una errata como `categores = true` no pasa
desapercibida.

### Directorios de recetas

| Directorio | Para qué | `appforge update` |
|---|---|---|
| `appforge-entries/` | Recetas de ejemplo que trae el paquete | Las actualiza; si cambiaste una, la conserva y deja la nueva en `.new` |
| `custom-entries/` | Tus recetas | Nunca lo toca |

Puedes añadir más directorios a la lista (por ejemplo, un repositorio de recetas de tu
equipo). Si dos directorios tienen una receta con el mismo nombre de fichero,
**vale la del último**: para sustituir una de ejemplo sin tocarla, copia su `.toml`
**y su subdirectorio** a `custom-entries/` y cámbiala ahí. `appforge validate` avisa
de cada sustitución.

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
| `logs/appforge.log`, en la carpeta de AppForge | Registro de todas las ejecuciones, copias incluidas; rota cada día y guarda 7 |

## Colores

La línea de comandos respeta `NO_COLOR`: con la variable definida no usa colores.

## Actualizar

```bash
sudo /opt/appforge/appforge update
```

Descarga la última versión, la verifica y la instala **sin pisar tus cambios**: ver
[`appforge update`](../guia/cli.md#appforge-update). Con `--dry-run` muestra antes
qué va a hacer.
