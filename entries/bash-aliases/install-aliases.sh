#!/usr/bin/env bash
# Instala ~/.bash_aliases (solo carga fragmentos) y los fragmentos de la receta en
# ~/.bash_aliases.d/ del usuario que ejecutó sudo. Como el destino depende del
# usuario, no son pasos `copy`: la copia .backup la hace este script, con la misma
# convención que el motor (sobrescribe la anterior). Solo gestiona base.sh y eza.sh;
# los demás fragmentos del directorio son del usuario.
set -euo pipefail

SRC="$APPFORGE_ENTRY_DIR"
DIR="$APPFORGE_USER_HOME/.bash_aliases.d"
group="$(id -gn "$APPFORGE_USER")"

for value in "$eza" "$eza_icons"; do
  case "$value" in
    yes | no) ;;
    *)
      echo "Error: valor no válido «$value» (se esperaba yes o no)" >&2
      exit 1
      ;;
  esac
done

# install_file <origen> <destino>: copia con .backup si el destino es distinto.
install_file() {
  if [ -f "$2" ] && cmp -s "$1" "$2"; then
    echo "$2: sin cambios"
    return
  fi
  if [ -e "$2" ]; then
    cp -p "$2" "$2.backup"
    echo "copia de seguridad: $2.backup"
  fi
  install -m 0644 -o "$APPFORGE_USER" -g "$group" "$1" "$2"
  echo "escrito $2"
}

if [ "$eza" = yes ]; then
  DEBIAN_FRONTEND=noninteractive apt-get install -y eza
fi

install -d -m 0755 -o "$APPFORGE_USER" -g "$group" "$DIR"
install_file "$SRC/bash_aliases" "$APPFORGE_USER_HOME/.bash_aliases"
install_file "$SRC/base.sh" "$DIR/base.sh"

if [ "$eza" = no ]; then
  rm -f "$DIR/eza.sh"
elif [ "$eza_icons" = yes ]; then
  install_file "$SRC/eza-icons.sh" "$DIR/eza.sh"
else
  install_file "$SRC/eza.sh" "$DIR/eza.sh"
fi

if ! grep -qs 'bash_aliases' "$APPFORGE_USER_HOME/.bashrc"; then
  echo "Aviso: $APPFORGE_USER_HOME/.bashrc no carga ~/.bash_aliases; añade: [ -f ~/.bash_aliases ] && . ~/.bash_aliases" >&2
fi
