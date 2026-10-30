#!/usr/bin/env bash
# Prueba una receta en una máquina virtual (o contenedor) desechable con incus.
#
# Uso:
#   scripts/try-entry.sh RECETA [--distro D] [--container] [--keep] [--deb RUTA]
#
#   RECETA       id en ./entries (mi-receta) o ruta a su .toml (…/mi-receta.toml);
#                su subdirectorio <id>/, si existe, va con ella.
#   --distro D   imagen de incus (por defecto debian/13; p. ej. ubuntu/25.04).
#   --container  contenedor en lugar de VM: más rápido, sin systemd ni KVM.
#   --keep       no borrar la máquina de prueba al salir.
#   --deb RUTA   paquete a instalar (por defecto, el más reciente de dist/).
#   --no-tui     solo prepara, sube y valida la receta (p. ej. en una CI).
#
# La primera vez por distro crea una base (appforge-base-…) con el .deb instalado,
# un usuario «usuario» con sudo y una instantánea «limpio»; después solo la clona.
# La TUI se abre como «usuario» con sudo, así que APPFORGE_USER es «usuario».
set -euo pipefail

distro="debian/13"
kind="vm"
keep=0
tui=1
deb=""
entry=""

die() { echo "try-entry: $*" >&2; exit 1; }
say() { printf '\033[1m==> %s\033[0m\n' "$*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --distro) distro="${2:?falta la distro}"; shift 2 ;;
    --container) kind="container"; shift ;;
    --keep) keep=1; shift ;;
    --no-tui) tui=0; shift ;;
    --deb) deb="${2:?falta la ruta del .deb}"; shift 2 ;;
    -h | --help) sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) die "opción desconocida: $1" ;;
    *) [ -z "$entry" ] || die "solo una receta"; entry="$1"; shift ;;
  esac
done
[ -n "$entry" ] || die "indica la receta (scripts/try-entry.sh --help)"

# --- Receta ------------------------------------------------------------------
if [[ "$entry" == *.toml ]]; then
  toml="$entry"
else
  toml="entries/$entry.toml"
fi
[ -f "$toml" ] || die "no existe $toml"
id="$(basename "$toml" .toml)"
entries_dir="$(cd "$(dirname "$toml")" && pwd)"
files_dir="$entries_dir/$id"

# --- Requisitos --------------------------------------------------------------
command -v incus >/dev/null || die "falta incus (sudo apt install incus)"
if [ "$kind" = vm ] && [ ! -e /dev/kvm ]; then
  die "sin /dev/kvm no hay VM: activa la virtualización o usa --container"
fi
if [ "$kind" = vm ] && ! incus info 2>/dev/null | grep -q virtual-machine; then
  die "incus no puede crear VM: instala qemu-system-x86 y ovmf (o usa --container)"
fi
if [ -z "$deb" ]; then
  for f in dist/appforge_*_amd64.deb; do  # el más reciente
    if [ -f "$f" ] && { [ -z "$deb" ] || [ "$f" -nt "$deb" ]; }; then deb="$f"; fi
  done
  [ -n "$deb" ] || die "no hay .deb en dist/: constrúyelo (uv run python scripts/build.py) o usa --deb"
fi
[ -f "$deb" ] || die "no existe $deb"

say "Validando $id en este equipo"
if command -v uv >/dev/null && [ -f pyproject.toml ]; then
  uv run appforge validate --strict --dir "$entries_dir" "$id"
elif command -v appforge >/dev/null; then
  appforge validate --strict --dir "$entries_dir" "$id"
else
  echo "(sin appforge ni uv aquí: se valida solo dentro)"
fi

# --- Máquina base ------------------------------------------------------------
slug="$(tr -c 'a-zA-Z0-9\n' '-' <<<"$distro")"  # incus: solo letras, números y -
base="appforge-base-$slug"
[ "$kind" = vm ] && base="$base-vm"
try="appforge-try"
flag=()
[ "$kind" = vm ] && flag=(--vm)
deb_sum="$(sha256sum "$deb" | cut -d' ' -f1)"

wait_ready() {  # espera a poder ejecutar órdenes y a tener red
  local name="$1"
  for _ in $(seq 120); do
    incus exec "$name" -- true 2>/dev/null && break
    sleep 2
  done
  # shellcheck disable=SC2016  # se expande dentro de la máquina
  incus exec "$name" -- sh -c \
    'for i in $(seq 60); do getent hosts deb.debian.org >/dev/null && exit 0; sleep 2; done; exit 1' \
    || die "$name no tiene red"
}

if incus info "$base" >/dev/null 2>&1; then
  if [ "$(incus config get "$base" user.appforge.deb)" != "$deb_sum" ]; then
    say "El .deb ha cambiado: rehaciendo $base"
    incus delete -f "$base"
  fi
fi
if ! incus info "$base" >/dev/null 2>&1; then
  say "Creando $base ($distro, $kind)"
  incus launch "images:$distro" "$base" "${flag[@]}" \
    || die "no se pudo crear ($kind) $distro (¿hay imagen? incus image list images: $distro)"
  wait_ready "$base"
  incus file push "$deb" "$base/tmp/appforge.deb"
  incus exec "$base" -- sh -c '
    set -e
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -q
    apt-get install -y -q /tmp/appforge.deb
    rm -f /tmp/appforge.deb
    id usuario >/dev/null 2>&1 || useradd -m -s /bin/bash usuario
    echo "usuario ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/usuario
    chmod 0440 /etc/sudoers.d/usuario'
  incus stop "$base"
  incus snapshot create "$base" limpio
  incus config set "$base" user.appforge.deb="$deb_sum"
fi

# --- Copia desechable --------------------------------------------------------
incus delete -f "$try" >/dev/null 2>&1 || true
cleanup() {
  if [ "$keep" = 1 ]; then
    echo "Se conserva $try: incus exec $try -- bash  ·  incus delete -f $try"
  else
    incus delete -f "$try" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

say "Clonando $base/limpio en $try"
incus copy "$base/limpio" "$try"
incus start "$try"
wait_ready "$try"

say "Subiendo $id"
incus file push "$toml" "$try/etc/appforge/entries/"
[ -d "$files_dir" ] && incus file push -r "$files_dir" "$try/etc/appforge/entries/"
incus exec "$try" -- sh -c 'chown -R root:root /etc/appforge/entries && chmod -R go-w /etc/appforge/entries'

say "Validando $id en $distro"
if [ "$tui" = 0 ]; then
  incus exec "$try" -- appforge validate --strict "$id"
  exit 0
fi
incus exec "$try" -- appforge validate --strict "$id" || echo "(sigue: revisa los avisos)"

say "Abriendo AppForge como «usuario» con sudo (q para salir)"
incus exec -t "$try" -- su - usuario -c "TERM='${TERM:-xterm-256color}' sudo appforge" || true

say "Final del registro"
incus exec "$try" -- tail -n 20 /var/log/appforge/appforge.log 2>/dev/null || echo "(sin registro)"
