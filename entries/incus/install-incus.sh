#!/usr/bin/env bash
# Instala Incus de Debian 13; con vms=yes, también QEMU y el firmware UEFI.
set -euo pipefail

case "$vms" in
  yes) packages=(incus qemu-system-x86 ovmf) ;;
  no) packages=(incus) ;;
  *)
    echo "Error: VM: escribe «yes» o «no» (recibido «$vms»)" >&2
    exit 1
    ;;
esac

if systemctl is-active --quiet docker 2>/dev/null; then
  echo "Aviso: Docker está activo y puede dejar sin red a las instancias de Incus (política FORWARD)" >&2
fi

DEBIAN_FRONTEND=noninteractive apt-get install -y "${packages[@]}"
