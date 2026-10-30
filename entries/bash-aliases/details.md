Instala `~/.bash_aliases` en tu usuario (modo 0644). El `~/.bashrc` de Debian ya lo
carga; si el tuyo no lo hace, la receta avisa.

| Grupo | Alias |
|---|---|
| Listados | `ls` (color), `ll`, `la`, `l`, `lt` (por fecha) |
| Búsqueda | `grep` con color |
| Navegación | `..`, `...` |
| Tamaños legibles | `df`, `du`, `free` con `-h` |
| Con confirmación | `cp -i`, `mv -i` |
| APT | `update`, `upgrade` (`full-upgrade`) |
| systemd | `sc` (`sudo systemctl`), `scs`, `failed`, `jf`, `jfu <servicio>`, `jerr` |

Abre una terminal nueva (o `source ~/.bash_aliases`) para usarlos.

Si ya tenías un `~/.bash_aliases` distinto, se guarda en `~/.bash_aliases.backup`
(sustituye a una copia anterior). Reaplicar la receta sustituye el fichero:
pon tus alias propios en otro sitio.

Desinstalar restaura `~/.bash_aliases.backup` si existe y, si no, borra el
fichero. Si lo has modificado después de aplicar la receta, no se toca.
