#!/usr/bin/env bash
# Valida la configuración completa con `sshd -t`. Si falla, restaura el
# 50-appforge.conf que guardó preflight.sh (o lo borra si no había) y aborta.
# Si es válida, abre el puerto en ufw (si está activo) y recarga el servicio.
set -euo pipefail

CONF=/etc/ssh/sshd_config.d/50-appforge.conf
SNAPSHOT=/run/appforge/ssh-server/previous.conf

if ! sshd -t; then
  if [ -f "$SNAPSHOT" ]; then
    cp -p "$SNAPSHOT" "$CONF"
    echo "Configuración no válida: restaurado el $CONF anterior" >&2
  else
    rm -f "$CONF"
    echo "Configuración no válida: borrado $CONF" >&2
  fi
  exit 1
fi
rm -f "$SNAPSHOT"

if command -v ufw >/dev/null && LC_ALL=C ufw status | grep -q '^Status: active'; then
  ufw allow "$port/tcp"
fi

systemctl enable ssh
if systemctl is-active --quiet ssh; then
  systemctl reload ssh
else
  systemctl start ssh
fi

# Otro fichero de sshd_config.d leído antes puede imponer su valor.
effective="$(sshd -T -C "user=$APPFORGE_USER,host=localhost,addr=127.0.0.1")"
for expected in "port $port" "permitrootlogin no" "passwordauthentication $password_auth"; do
  grep -qx "$expected" <<<"$effective" \
    || echo "Aviso: el valor efectivo no es «$expected»; revisa otros ficheros de /etc/ssh/sshd_config.d" >&2
done
echo "sshd escuchando en el puerto $port"
