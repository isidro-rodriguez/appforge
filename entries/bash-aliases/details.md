Instala alias de bash para tu usuario en dos piezas:

- `~/.bash_aliases`: solo carga los fragmentos `~/.bash_aliases.d/*.sh`. El
  `~/.bashrc` de Debian ya lo carga; si el tuyo no lo hace, la receta avisa.
- `~/.bash_aliases.d/`: un fragmento por grupo. La receta solo gestiona `base.sh` y
  `eza.sh` (modo 0644).

| Fragmento | Alias | Cuándo |
|---|---|---|
| `base.sh` | `..`, `...`, `cp -i`, `mv -i`, `mkdir -pv`, `df` (sin tmpfs), `du1` (tamaño de cada subdirectorio), `ports` (`ss -tulpn`), `path` (el `PATH` por líneas), `jlog` (avisos del arranque actual) | Siempre |
| `eza.sh` | `ls`, `l`, `ll` (con estado de git), `la`, `lt` (árbol a dos niveles) con [eza](https://github.com/eza-community/eza) | Parámetro de eza (sí). Instala el paquete `eza` de Debian |

### eza e iconos

- `ls` → eza solo afecta a la shell interactiva: los scripts siguen usando `ls`. Para
  el original, `\ls` o `command ls`.
- Si `eza` no está instalado, el fragmento no define nada.
- Con el parámetro de iconos (`--icons=auto`) el terminal necesita una **Nerd Font**
  (p. ej. JetBrainsMono Nerd Font, de la receta **Fuentes adicionales**); si no,
  salen cuadros. La receta no configura el terminal: elige la fuente en sus
  preferencias.

### Tus propios alias

Ponlos en `~/.bash_aliases.d/<nombre>.sh`: la receta no los toca, ni al reaplicarla
ni al desinstalarla. Abre una terminal nueva (o `source ~/.bash_aliases`) para
usarlos.

Los alias de git están en la receta **Git y GitHub CLI** (`git st`, `git lg`…), en
`~/.gitconfig`.

### Copias y desinstalación

Si ya tenías un `~/.bash_aliases` distinto, se guarda en `~/.bash_aliases.backup`
(sustituye a una copia anterior); lo mismo con `base.sh` y `eza.sh`.

Desinstalar restaura `~/.bash_aliases.backup` si existe (si no, borra el fichero),
borra `base.sh` y `eza.sh`, y el directorio si queda vacío. Lo que hayas modificado
después de aplicar la receta no se toca. No desinstala `eza`.
