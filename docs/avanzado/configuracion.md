# Configuración

## Dónde busca AppForge su configuración

AppForge lee un único `config.toml` del **directorio base**, que se decide así:

| Prioridad | Origen |
|---|---|
| 1 | Variable `APPFORGE_HOME` |
| 2 | Directorio del binario, si se ejecuta empaquetado |
| 3 | Directorio de trabajo |

Así una misma instalación puede tener varios juegos de recetas:

```bash
APPFORGE_HOME=~/recetas/portatil appforge
APPFORGE_HOME=~/recetas/servidor appforge list
```

## `config.toml`

```toml title="config.toml"
# Rutas relativas al directorio base.
entries_dir = "entries"

# Opcional. Por defecto: $XDG_STATE_HOME/appforge/backups
# backups_dir = "~/copias/appforge"

[ui]
search = false       # buscador sobre la lista
categories = false   # panel de categorías
```

| Clave | Tipo | Por defecto | Descripción |
|---|---|---|---|
| `entries_dir` | ruta | — (obligatoria) | Directorio de recetas, relativo al directorio base. Debe existir |
| `backups_dir` | ruta | `$XDG_STATE_HOME/appforge/backups` | Destino de las copias de seguridad. Admite `~` |
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

## Directorios de estado

AppForge no guarda estado propio: si una receta está aplicada lo dice siempre su
`[check]`. Solo escribe dos cosas, ambas bajo `$XDG_STATE_HOME/appforge/`
(normalmente `~/.local/state/appforge/`):

| Ruta | Contenido |
|---|---|
| `backups/<id>/<AAAAMMDD-HHMMSS>/<ruta original>` | Copia de cada fichero antes de sobrescribirlo (`0600`) |
| `logs/appforge.log` | Registro de todas las ejecuciones; rota cada día y guarda 7 |

## Variables de entorno

| Variable | Efecto |
|---|---|
| `APPFORGE_HOME` | Directorio base (ver arriba) |
| `XDG_STATE_HOME` | Base de copias y registro |
| `NO_COLOR` | Desactiva los colores de la CLI |
| `APPFORGE_SUDO` | Sustituye el prefijo `sudo -n` de los pasos con root. Vacío = sin prefijo. Pensado para tests |
