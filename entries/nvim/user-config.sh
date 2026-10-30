#!/usr/bin/env bash
# Instala la configuración de /opt/nvim/appforge/config en ~/.config/nvim del
# usuario que ejecutó sudo. Si ya tenía una configuración que no es de AppForge,
# se mueve a ~/.config/nvim.backup-<fecha> antes de instalar la nueva.
# lua/local.lua y nvim-pack-lock.json solo se crean si no existen (son del usuario).
set -euo pipefail

SRC=/opt/nvim/appforge/config
DEST="$APPFORGE_USER_HOME/.config/nvim"
as_user() { runuser -u "$APPFORGE_USER" -- "$@"; }

if [ -e "$DEST" ] && [ ! -d "$DEST/lua/appforge" ]; then
  backup="$DEST.backup-$(date +%Y%m%d-%H%M%S)"
  as_user mv "$DEST" "$backup"
  echo "Configuración anterior de Neovim movida a $backup"
fi

as_user mkdir -p "$DEST/lua/appforge"
as_user install -m 0644 "$SRC/init.lua" "$DEST/init.lua"
for f in options keymaps plugins treesitter lsp bootstrap; do
  as_user install -m 0644 "$SRC/lua/appforge/$f.lua" "$DEST/lua/appforge/$f.lua"
done
for f in lua/local.lua nvim-pack-lock.json; do
  if [ ! -e "$DEST/$f" ]; then
    as_user install -m 0644 "$SRC/$f" "$DEST/$f"
  fi
done
echo "Configuración instalada en $DEST"
