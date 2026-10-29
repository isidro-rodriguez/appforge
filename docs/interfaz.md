# Interfaz y tema

## Pantalla principal

```text
╭──────────────────────────────── AppForge ─────────────────────── v0.2.0 ╮
╭ Buscar ─────────────────────────────────────────────────────────────────╮  ← [ui].search
╭ Categorías ──╮╭ Aplicaciones ───────────────────╮╭ Detalle ──────────────╮
│ Todas      6 ││ ✔  Docker Engine           user ││ Estado    no aplicada │
│ Desarrollo 2 ││    Firefox             aplicada ││ Categoría Desarrollo  │
│ ...          ││ ✔  Ollama (bajo demanda)   root ││ ...                   │
╰──────────────╯╰─────────────────────────────────╯│ Seleccionadas: 2      │
  ↑ [ui].categories                                ╰───────────────────────╯
tab Cambiar panel  space Marcar  i Instalar  u Desinstalar  d Dry-run  / Buscar  q Salir
```

| Panel | Contenido |
|---|---|
| Buscar | Filtra por nombre, id, descripción y categoría mientras escribes. Solo con `[ui].search = true` |
| Categorías | `Todas` y una fila por `category` (las entradas sin ella van a «Sin categoría»), con contador. Solo con `[ui].categories = true` |
| Aplicaciones | Casilla de selección, nombre y etiqueta: `aplicada`, `root`/`user` (si necesita sudo) o `inválida` |
| Detalle | Datos leídos del TOML, problemas de validación y la lista de seleccionadas |

```toml
# config.toml
[ui]
search = true
categories = true
```

## Teclas

| Tecla | Acción |
|---|---|
| `espacio` / `Enter` | Marcar o desmarcar la entrada resaltada |
| `i` | Instalar las marcadas (o la resaltada si no hay ninguna) |
| `u` | Desinstalar (`[remove]`) las marcadas o la resaltada |
| `d` | Dry-run de instalación; no consume la selección |
| `/` | Ir al buscador (`Esc` o `Enter` vuelve a la lista) |
| `tab` | Cambiar de panel |
| `r` | Recargar entradas |
| `q` | Salir |

Antes de ejecutar se piden los parámetros de cada entrada (una ventana por entrada), se
confirma el lote y, si alguna necesita root, se pide la contraseña de sudo una vez.

## Pantalla de progreso

| Zona | Contenido |
|---|---|
| Progreso `i / N` | Una fila por entrada: `▶` en curso, `✔` bien, `✘` fallo, `!` cancelada; paso actual y duración |
| Barra | Pasos completados del lote |
| Registro | Salida en vivo; cada línea lleva el tipo de paso (`[run ]`, `[tpl ]`, `[copy]`, `[scr ]`, `[rm  ]`, `[chk ]`) |

| Tecla | Acción |
|---|---|
| `ctrl+c` | Cancelar: termina el comando en curso y no empieza más pasos ni entradas |
| `l` | Ver el registro completo |
| `Esc` | Volver (cuando ha terminado) |

Si una entrada falla, el lote sigue con la siguiente. Las que terminan bien se desmarcan.

## Registro

Cada ejecución (TUI y CLI) se añade a `~/.local/state/appforge/logs/appforge.log`, con
rotación diaria y 7 días de histórico ([`acodo.logger`](https://isidro-rodriguez.github.io/acodo/)).
Los secretos ya llegan enmascarados.

## Tema

Los colores salen del icono (`src/appforge/resources/appforge-512.png`) y viven en
`src/appforge/theme.py`, que define un tema de Textual (TUI) y uno de Rich (CLI).

| Nombre | Color | Origen | Uso |
|---|---|---|---|
| `BACKGROUND` | `#14171b` | Fondo exterior | Fondo de la TUI |
| `SURFACE` | `#1a202b` | Tarjeta | Diálogos |
| `PANEL` | `#1d232f` | Tarjeta, zona clara | Fondo de la barra |
| `CREAM` | `#f8f0e5` | Terminal del icono | Texto |
| `SPARK` | `#fea31d` | Chispas | Títulos de panel, teclas, pasos, avisos |
| `PRIMARY` | `#6a85b0` | Yunque, aclarado | Bordes con foco, barra |
| `ANVIL` / `ANVIL_DARK` / `ANVIL_DEEP` | `#546278` / `#37496a` / `#222e46` | Yunque | Bordes sin foco, cursor, casillas |
| `MUTED` | `#8a94a6` | Derivado | Texto secundario |
| `SUCCESS` / `ERROR` | `#7cc47f` / `#e5604d` | Añadidos para contraste | Correcto / error |

En la CLI el texto normal usa el color de tu terminal; solo los eventos (pasos, avisos,
errores, estado) se colorean. Respeta `NO_COLOR`.
