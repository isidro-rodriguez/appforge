#!/usr/bin/env bash
# Instala ~/.bash_aliases del usuario que ejecutó sudo. Como el destino depende
# del usuario, no es un paso `copy`: la copia .backup la hace este script, con
# la misma convención que el motor (sobrescribe la anterior).
set -euo pipefail

SRC="$APPFORGE_ENTRY_DIR/bash_aliases"
DEST="$APPFORGE_USER_HOME/.bash_aliases"
group="$(id -gn "$APPFORGE_USER")"

if [ -f "$DEST" ] && cmp -s "$SRC" "$DEST"; then
  echo "$DEST: sin cambios"
else
  if [ -e "$DEST" ]; then
    cp -p "$DEST" "$DEST.backup"
    echo "copia de seguridad: $DEST.backup"
  fi
  install -m 0644 -o "$APPFORGE_USER" -g "$group" "$SRC" "$DEST"
  echo "escrito $DEST"
fi

if ! grep -qs 'bash_aliases' "$APPFORGE_USER_HOME/.bashrc"; then
  echo "Aviso: $APPFORGE_USER_HOME/.bashrc no carga ~/.bash_aliases; añade: [ -f ~/.bash_aliases ] && . ~/.bash_aliases" >&2
fi
