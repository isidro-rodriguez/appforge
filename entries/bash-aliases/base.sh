# ~/.bash_aliases.d/base.sh — instalado por AppForge (receta bash-aliases).
# Reaplicar la receta lo sustituye: pon tus alias en otro fragmento.

# --- Navegación -------------------------------------------------------------
alias ..='cd ..'
alias ...='cd ../..'

# --- Ficheros ---------------------------------------------------------------
alias cp='cp -i'
alias mv='mv -i'
alias mkdir='mkdir -pv'

# --- Discos -----------------------------------------------------------------
alias df='df -hT -x tmpfs -x devtmpfs'
alias du1='du -h --max-depth=1 | sort -h'   # tamaño de cada subdirectorio

# --- Sistema ----------------------------------------------------------------
alias ports='ss -tulpn'                      # puertos a la escucha
alias path='tr ":" "\n" <<< "$PATH"'         # un directorio del PATH por línea
alias jlog='journalctl -b -p warning --no-pager | tail -50'
