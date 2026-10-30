#!/usr/bin/env bash
# Valida todas las excepciones antes de tocar nada; después fija la política
# (entrada denegada, salida permitida), añade las reglas y activa ufw.
# ufw no duplica reglas existentes («Skipping adding existing rule»).
set -euo pipefail

# «-» significa «ninguna» (un parámetro no puede quedar vacío).
allow="${allow:--}"
allow_from="${allow_from:--}"
[ "$allow" != - ] || allow=""
[ "$allow_from" != - ] || allow_from=""

fail() {
  echo "Error: $*" >&2
  exit 1
}

# Puerto 1-65535, sin ceros a la izquierda.
valid_port() {
  [[ "$1" =~ ^[1-9][0-9]{0,4}$ ]] && [ "$1" -le 65535 ]
}

# Formatos admitidos: 22, 22/tcp, 60000:61000/udp, ssh, https/tcp.
valid_rule() {
  local rule="$1" spec proto=""
  spec="${rule%%/*}"
  if [[ "$rule" == */* ]]; then
    proto="${rule#*/}"
    [[ "$proto" =~ ^(tcp|udp)$ ]] || return 1
  fi
  if [[ "$spec" =~ ^([0-9]+):([0-9]+)$ ]]; then
    [ -n "$proto" ] || return 1 # ufw exige protocolo en los rangos
    local first="${BASH_REMATCH[1]}" last="${BASH_REMATCH[2]}"
    valid_port "$first" && valid_port "$last" && [ "$first" -lt "$last" ]
  elif [[ "$spec" =~ ^[0-9]+$ ]]; then
    valid_port "$spec"
  elif [[ "$spec" =~ ^[a-z][a-z0-9-]*$ ]]; then
    getent services "$spec" >/dev/null
  else
    return 1
  fi
}

read -r -a rules <<<"$allow"
for rule in "${rules[@]}"; do
  valid_rule "$rule" || fail "excepción no válida: «$rule» (ejemplos: 22/tcp, 443, 60000:61000/udp, ssh)"
  # Segunda opinión: el propio analizador de ufw, sin aplicar nada.
  ufw --dry-run allow "$rule" >/dev/null 2>&1 || fail "ufw rechaza la excepción «$rule»"
done

if [ -n "$allow_from" ]; then
  [[ "$allow_from" =~ ^[0-9a-fA-F.:/]+$ ]] || fail "red de confianza no válida: «$allow_from»"
  ufw --dry-run allow from "$allow_from" >/dev/null 2>&1 \
    || fail "ufw rechaza la red de confianza «$allow_from» (ejemplo: 192.168.1.0/24)"
fi

echo "Excepciones válidas: ${rules[*]:-ninguna}; red de confianza: ${allow_from:-ninguna}"

ufw default deny incoming
ufw default allow outgoing
for rule in "${rules[@]}"; do
  ufw allow "$rule"
done
if [ -n "$allow_from" ]; then
  ufw allow from "$allow_from"
fi
ufw --force enable
LC_ALL=C ufw status verbose
