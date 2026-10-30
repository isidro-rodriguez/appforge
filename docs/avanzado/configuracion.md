# Configuración

## Dónde está

AppForge lee el `config.toml` que está junto al programa: `/opt/appforge/config.toml`
si lo extrajiste ahí. Las rutas relativas se resuelven desde esa carpeta, también si
lanzas AppForge desde un enlace (`/usr/local/bin/appforge`).

Se edita como superusuario (`sudo editor /opt/appforge/config.toml`). AppForge se
niega a arrancar si es un enlace simbólico o si lo pueden modificar otros usuarios.

## `config.toml`

```toml title="config.toml"
# Relativo a la carpeta de AppForge.
entries_dir = "entries"

[ui]
search = false       # buscador sobre la lista
categories = false   # panel de categorías
```

| Clave | Tipo | Por defecto | Descripción |
|---|---|---|---|
| `entries_dir` | ruta | — (obligatoria) | Directorio de recetas, relativo a la carpeta de AppForge. Debe existir |
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
| `logs/appforge.log`, en la carpeta de AppForge | Registro de todas las ejecuciones, copias incluidas; rota cada día y guarda 7 |

## Colores

La línea de comandos respeta `NO_COLOR`: con la variable definida no usa colores.

## Actualizar

Una versión nueva se extrae igual, encima de la anterior. Eso **sobrescribe**
`config.toml` y las recetas de ejemplo; tus recetas propias (ficheros que el paquete
no trae) se conservan. Si cambiaste algo del paquete, guárdalo antes:

```bash
sudo cp -a /opt/appforge/config.toml /opt/appforge/config.toml.mio
sudo tar -xzf appforge-<versión>-linux-x86_64.tar.gz -C /opt
```
