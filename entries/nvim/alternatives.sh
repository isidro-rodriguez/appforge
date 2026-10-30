#!/usr/bin/env bash
# Sustituye vi y vim por Neovim con update-alternatives (los paquetes vim-tiny o
# vim, si están, se quedan como alternativa de reserva). Neovim no cambia de modo
# según el nombre con que se le llama, así que view y vimdiff van con envoltorios.
set -euo pipefail

register() { # <nombre> <ruta>
  update-alternatives --install "/usr/bin/$1" "$1" "$2" 100
  update-alternatives --set "$1" "$2" # también si estaba en modo manual
}

register vi /opt/nvim/bin/nvim
register vim /opt/nvim/bin/nvim
register view /opt/nvim/libexec/view
register vimdiff /opt/nvim/libexec/vimdiff
