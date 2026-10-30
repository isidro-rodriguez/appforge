#!/usr/bin/env bash
# Prepara Neovim para el usuario que ejecutó sudo, sin abrir el editor: clona los
# plugins (versiones de nvim-pack-lock.json), compila los parsers de tree-sitter e
# instala los servidores LSP base con Mason. Necesita red; reejecutarlo solo
# instala lo que falte.
set -euo pipefail

cd "$APPFORGE_USER_HOME"
runuser -u "$APPFORGE_USER" -- env \
  -u XDG_CONFIG_HOME -u XDG_DATA_HOME -u XDG_STATE_HOME -u XDG_CACHE_HOME \
  HOME="$APPFORGE_USER_HOME" PATH=/usr/local/bin:/usr/bin:/bin \
  /opt/nvim/bin/nvim --headless --cmd 'let g:appforge_bootstrap = 1' \
  '+lua require("appforge.bootstrap")'
echo
echo "Plugins, parsers y servidores LSP listos"
