#!/usr/bin/env bash
# Prueba una receta (o AppForge tal cual) en una máquina virtual o contenedor
# desechable con incus.
#
# Uso:
#   scripts/try-entry.sh [RECETA] [--distro D] [--container] [--keep] [--tar RUTA]
#
#   RECETA       id en ./entries (mi-receta) o ruta a su carpeta (…/mi-receta/,
#                con entry.toml y details.md). Sin ella, abre la TUI con las
#                recetas del paquete.
#   --distro D   imagen de incus (por defecto debian/13; p. ej. ubuntu/26.04).
#   --container  contenedor en lugar de VM: más rápido, sin systemd ni KVM.
#   --keep       no borrar la máquina de prueba al salir.
#   --tar RUTA   paquete appforge-*.tar.gz (por defecto, el más reciente de dist/).
#   --no-tui     solo prepara, sube y valida la receta (sin receta, todas) (p. ej.
#                en una CI).
#
# La primera vez por distro crea una base (appforge-base-…) con AppForge en /opt,
# un usuario «usuario» con sudo y una instantánea «limpio»; después solo la clona.
# La TUI se abre como «usuario» con sudo, así que APPFORGE_USER es «usuario».
set -euo pipefail

distro="debian/13"
kind="vm"
keep=0
tui=1
pkg=""
entry=""

die() { echo "try-entry: $*" >&2; exit 1; }
trap 'echo; die "interrumpido"' INT
say() { printf '\033[1m==> %s\033[0m\n' "$*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --distro) distro="${2:?falta la distro}"; shift 2 ;;
    --container) kind="container"; shift ;;
    --keep) keep=1; shift ;;
    --no-tui) tui=0; shift ;;
    --tar) pkg="${2:?falta la ruta del .tar.gz}"; shift 2 ;;
    -h | --help) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) die "opción desconocida: $1" ;;
    *) [ -z "$entry" ] || die "solo una receta"; entry="$1"; shift ;;
  esac
done
# --- Receta (opcional) -------------------------------------------------------
id=""
if [ -n "$entry" ]; then
  if [[ "$entry" == */* ]]; then
    files_dir="${entry%/}"
  else
    files_dir="entries/$entry"
  fi
  [ -f "$files_dir/entry.toml" ] || die "no existe $files_dir/entry.toml"
  files_dir="$(cd "$files_dir" && pwd)"
  id="$(basename "$files_dir")"
fi

# --- Requisitos --------------------------------------------------------------
command -v incus >/dev/null || die "falta incus (sudo apt install incus)"
if [ "$kind" = vm ] && [ ! -e /dev/kvm ]; then
  die "sin /dev/kvm no hay VM: activa la virtualización o usa --container"
fi
if ! info="$(incus info 2>&1)"; then
  die "no puedo usar incus: $(head -n 1 <<<"$info")
  ¿Estás en el grupo incus-admin en esta sesión? (id -nG; newgrp incus-admin o vuelve a entrar)"
fi
if [ "$kind" = vm ] && ! grep -q virtual-machine <<<"$info"; then
  die "incus no admite VM todavía. Con qemu-system-x86 y ovmf instalados, reinicia incus
  para que detecte QEMU: sudo systemctl restart incus (o usa --container)"
fi
if [ -z "$pkg" ]; then
  for f in dist/appforge-*-linux-x86_64.tar.gz; do  # el más reciente
    if [ -f "$f" ] && { [ -z "$pkg" ] || [ "$f" -nt "$pkg" ]; }; then pkg="$f"; fi
  done
  [ -n "$pkg" ] || die "no hay paquete en dist/: constrúyelo (uv run python scripts/build.py) o usa --tar"
fi
[ -f "$pkg" ] || die "no existe $pkg"
# El paquete lleva el programa que valida y aplica la receta: si es de otra versión
# que el código (p. ej. sin las claves nuevas del formato), la prueba no vale.
pkg_version="$(basename "$pkg" | sed -n 's/^appforge-\(.*\)-linux-.*\.tar\.gz$/\1/p')"
if [ -f pyproject.toml ] && [ -d src/appforge ]; then
  src_version="$(sed -n 's/^version = "\(.*\)"$/\1/p' pyproject.toml | head -n 1)"
  if [ -n "$pkg_version" ] && [ "$pkg_version" != "$src_version" ]; then
    die "el paquete es la versión $pkg_version y el código la $src_version.
  Reconstrúyelo (uv run python scripts/build.py) o indica otro con --tar"
  fi
  if [ -n "$(find src -newer "$pkg" -type f -print -quit)" ]; then
    echo "Aviso: hay cambios en src/ posteriores a $(basename "$pkg"); reconstrúyelo si afectan a la prueba"
  fi
fi
say "Paquete: $(basename "$pkg")"

validate_here() {
# Sobre una copia sin escritura para grupo/otros: aquí interesa el contenido. Los
# permisos de tu copia de trabajo dependen de tu umask (git no los guarda) y en la
# máquina de prueba se fijan al subir la receta.
check_dir="$(mktemp -d)"
mkdir "$check_dir/entries"
cp -r "$files_dir" "$check_dir/entries/"
chmod -R go-w "$check_dir"
if command -v uv >/dev/null && [ -f pyproject.toml ]; then
  validator=(uv run appforge)
elif command -v appforge >/dev/null; then
  validator=(appforge)
else
  validator=()
  echo "(sin appforge ni uv aquí: se valida solo dentro)"
fi
if [ "${#validator[@]}" -gt 0 ]; then
  rc=0
  "${validator[@]}" validate --strict --dir "$check_dir/entries" "$id" || rc=$?
  rm -rf "$check_dir"
  [ "$rc" = 0 ] || die "la receta no pasa la validación"
fi
rm -rf "$check_dir"
}
if [ -n "$id" ]; then
  say "Validando $id en este equipo"
  validate_here
fi

# --- Máquina base ------------------------------------------------------------
slug="$(tr -c 'a-zA-Z0-9\n' '-' <<<"$distro")"  # incus: solo letras, números y -
base="appforge-base-$slug"
[ "$kind" = vm ] && base="$base-vm"
try="appforge-try"
flag=()
[ "$kind" = vm ] && flag=(--vm)
pkg_sum="$(sha256sum "$pkg" | cut -d' ' -f1)"

wait_ready() {  # espera a poder ejecutar órdenes y a tener red
  local name="$1" ok=0
  printf '    esperando a que %s arranque' "$name"
  for _ in $(seq 90); do  # 3 min: una VM tarda en cargar su agente
    if incus exec "$name" -- true 2>/dev/null; then ok=1; break; fi
    printf '.'
    sleep 2
  done
  echo
  [ "$ok" = 1 ] || die "$name no responde tras 3 min. Mira: incus info $name --show-log"
  printf '    esperando red'
  ok=0
  for _ in $(seq 30); do  # 2 min como mucho, aunque el DNS no responda
    if incus exec "$name" -- timeout 3 getent hosts deb.debian.org >/dev/null 2>&1; then
      ok=1; break
    fi
    printf '.'
    sleep 1
  done
  echo
  [ "$ok" = 1 ] || die "$name no tiene red. Suele ser un cortafuegos o Docker bloqueando
  el puente de incus; ver «Sin red en la máquina» en docs/desarrollo/probar.md"
}

if incus info "$base" >/dev/null 2>&1; then
  if [ "$(incus config get "$base" user.appforge.pkg)" != "$pkg_sum" ]; then
    say "El paquete ha cambiado: rehaciendo $base"
    incus delete -f "$base"
  fi
fi
if ! incus info "$base" >/dev/null 2>&1; then
  say "Creando $base ($distro, $kind)"
  echo "    la primera vez descarga la imagen (unos cientos de MB)"
  incus launch "images:$distro" "$base" "${flag[@]}" \
    || die "no se pudo crear ($kind) $distro (¿hay imagen? incus image list images: $distro)"
  wait_ready "$base"
  incus file push "$pkg" "$base/tmp/appforge.tar.gz"
  incus exec "$base" -- sh -c '
    set -e
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -q
    apt-get install -y -q sudo
    tar -xzf /tmp/appforge.tar.gz -C /opt
    ln -sf /opt/appforge/appforge /usr/local/bin/appforge
    rm -f /tmp/appforge.tar.gz
    id usuario >/dev/null 2>&1 || useradd -m -s /bin/bash usuario
    echo "usuario ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/usuario
    chmod 0440 /etc/sudoers.d/usuario'
  incus stop "$base"
  incus snapshot create "$base" limpio
  incus config set "$base" user.appforge.pkg="$pkg_sum"
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

if [ -n "$id" ]; then
  say "Subiendo $id"
  incus file push -r "$files_dir" "$try/opt/appforge/custom-entries/"
  incus exec "$try" -- sh -c 'chown -R root:root /opt/appforge/custom-entries && chmod -R go-w /opt/appforge/custom-entries'
fi

say "Validando ${id:-las recetas del paquete} en $distro"
validate_args=(appforge validate --strict)
[ -z "$id" ] || validate_args+=("$id")
if [ "$tui" = 0 ]; then
  incus exec "$try" -- "${validate_args[@]}"
  exit 0
fi
incus exec "$try" -- "${validate_args[@]}" || echo "(sigue: revisa los avisos)"

say "Abriendo AppForge como «usuario» con sudo (q para salir)"
incus exec -t "$try" -- su - usuario -c "TERM='${TERM:-xterm-256color}' sudo appforge" || true

say "Final del registro"
incus exec "$try" -- tail -n 20 /opt/appforge/logs/appforge.log 2>/dev/null || echo "(sin registro)"
