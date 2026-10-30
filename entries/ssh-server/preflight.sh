#!/usr/bin/env bash
# Comprobaciones antes de tocar nada: parámetros válidos y que el usuario no se
# quede fuera. Guarda el 50-appforge.conf actual para que apply.sh pueda
# restaurarlo si `sshd -t` falla.
set -euo pipefail

CONF=/etc/ssh/sshd_config.d/50-appforge.conf
SNAPSHOT_DIR=/run/appforge/ssh-server

fail() {
  echo "Error: $*" >&2
  exit 1
}

[[ "$port" =~ ^[1-9][0-9]{0,4}$ ]] && [ "$port" -le 65535 ] \
  || fail "puerto no válido: «$port» (1-65535)"
[[ "$password_auth" =~ ^(yes|no)$ ]] \
  || fail "contraseña: escribe «yes» o «no» (recibido «$password_auth»)"
[ "$APPFORGE_USER" != root ] \
  || fail "ejecuta AppForge con sudo desde tu usuario: con PermitRootLogin no y AllowUsers root nadie podría entrar"

keys="$APPFORGE_USER_HOME/.ssh/authorized_keys"
if [ "$password_auth" = no ] && ! grep -qE '^[[:space:]]*[^#[:space:]]' "$keys" 2>/dev/null; then
  fail "$keys no existe o no tiene claves: copia antes tu clave pública (ssh-copy-id) o aplica con contraseña «yes»"
fi

mkdir -p "$SNAPSHOT_DIR"
chmod 0700 "$SNAPSHOT_DIR"
if [ -f "$CONF" ]; then
  cp -p "$CONF" "$SNAPSHOT_DIR/previous.conf"
else
  rm -f "$SNAPSHOT_DIR/previous.conf"
fi
echo "Parámetros correctos; configuración actual guardada en $SNAPSHOT_DIR"
