#!/usr/bin/env bash
# Configuración global de git del usuario que ejecutó sudo, escrita como ese
# usuario (el ~/.gitconfig sigue siendo suyo). `git config` sustituye el valor
# anterior, así que reaplicar no duplica nada.
set -euo pipefail

# «-» en el editor significa «no cambiar» (un parámetro no puede quedar vacío).
[ "$editor" != - ] || editor=""

fail() {
  echo "Error: $*" >&2
  exit 1
}

[ -n "${user_name//[[:space:]]/}" ] || fail "el nombre no puede estar vacío"
[[ "$user_email" =~ ^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:].]+$ ]] \
  || fail "email no válido: «$user_email»"
git check-ref-format --branch "$default_branch" >/dev/null 2>&1 \
  || fail "nombre de rama no válido: «$default_branch»"
if [ -n "$editor" ] && ! command -v "${editor%% *}" >/dev/null; then
  echo "Aviso: «${editor%% *}» no está instalado; git lo usará cuando exista" >&2
fi

as_user() { runuser -u "$APPFORGE_USER" -- env HOME="$APPFORGE_USER_HOME" "$@"; }

as_user git config --global user.name "$user_name"
as_user git config --global user.email "$user_email"
as_user git config --global init.defaultBranch "$default_branch"
as_user git config --global pull.rebase false
if [ -n "$editor" ]; then
  as_user git config --global core.editor "$editor"
fi

# Alias de aliases.conf (<nombre> <valor>); git config sustituye el valor anterior.
if [ "$aliases" = yes ]; then
  while read -r name value; do
    case "$name" in "" | "#"*) continue ;; esac
    as_user git config --global "alias.$name" "$value"
  done <"$APPFORGE_ENTRY_DIR/aliases.conf"
  echo "alias de git instalados (lista: git config --global --get-regexp '^alias')"
fi

# gh como gestor de credenciales de github.com; --force porque el usuario aún
# no ha hecho `gh auth login`.
as_user gh auth setup-git --hostname github.com --force
echo "git configurado para $APPFORGE_USER ($user_email)"
