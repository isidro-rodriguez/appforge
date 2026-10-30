#!/usr/bin/env bash
# Patrón para repositorios APT de terceros firmados:
#   1. este script descarga la clave a un temporal y comprueba su huella;
#   2. solo entonces la instala en /etc/apt/keyrings/ (sin escritura para otros);
#   3. un paso `copy` instala el .sources (deb822) con `Signed-By:` a esa clave,
#      para que la clave valga solo para ese repositorio.
# Para otro repositorio, cambia las variables de abajo.
set -euo pipefail

KEY_URL=https://download.docker.com/linux/debian/gpg
KEYRING=/etc/apt/keyrings/docker.asc
# Huellas admitidas (todas las claves del fichero deben estar aquí) y la que
# debe estar presente (la que firma hoy el repositorio).
FINGERPRINTS=(9DC858229FC7DD38854AE2D88D81803C0EBFCD88)
REQUIRED=9DC858229FC7DD38854AE2D88D81803C0EBFCD88

. /etc/os-release
if [ "${VERSION_CODENAME:-}" != trixie ] || [ "$(dpkg --print-architecture)" != amd64 ]; then
  echo "Error: esta receta es para Debian 13 (trixie) amd64" >&2
  exit 1
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
curl -fsSL "$KEY_URL" -o "$tmp/key"

# Huellas de las claves principales del fichero descargado.
mapfile -t found < <(
  GNUPGHOME="$tmp" gpg --batch --show-keys --with-colons "$tmp/key" 2>/dev/null \
    | awk -F: '$1 == "pub" {want = 1; next} want && $1 == "fpr" {print $10; want = 0}'
)
if [ "${#found[@]}" -eq 0 ]; then
  echo "Error: $KEY_URL no contiene ninguna clave PGP" >&2
  exit 1
fi
for fpr in "${found[@]}"; do
  if ! printf '%s\n' "${FINGERPRINTS[@]}" | grep -qx "$fpr"; then
    echo "Error: huella inesperada en $KEY_URL: $fpr" >&2
    exit 1
  fi
done
if ! printf '%s\n' "${found[@]}" | grep -qx "$REQUIRED"; then
  echo "Error: $KEY_URL no contiene la clave $REQUIRED" >&2
  exit 1
fi
echo "Huella verificada: ${found[*]}"

install -d -m 0755 /etc/apt/keyrings
install -m 0644 "$tmp/key" "$KEYRING"
echo "Clave instalada en $KEYRING"
