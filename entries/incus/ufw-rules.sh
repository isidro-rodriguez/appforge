#!/usr/bin/env bash
# Permite el tráfico del puente incusbr0 (DHCP, DNS y reenvío de las
# instancias). ufw no duplica reglas existentes. Sin ufw, no hace nada.
set -euo pipefail

if ! command -v ufw >/dev/null; then
  echo "ufw no está instalado: nada que hacer"
  exit 0
fi
ufw allow in on incusbr0
ufw route allow in on incusbr0
ufw route allow out on incusbr0
