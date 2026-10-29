#!/usr/bin/env bash
# Habilita contrib y non-free si los paquetes de fuentes no tienen candidato.
# Solo añade los componentes que falten, en un fichero propio de AppForge, para
# no tocar /etc/apt/sources.list.d/debian.sources.
set -euo pipefail

SOURCES=/etc/apt/sources.list.d/appforge-fonts.sources
PACKAGES=(ttf-mscorefonts-installer fonts-ubuntu fonts-firacode)

has_candidate() {
  apt-cache policy "$1" 2>/dev/null | grep -q 'Candidate: [^(]'
}

missing=0
for pkg in "${PACKAGES[@]}"; do
  has_candidate "$pkg" || missing=1
done
if [ "$missing" -eq 0 ]; then
  echo "Todos los paquetes de fuentes están disponibles"
  exit 0
fi

present="$(apt-get indextargets --format '$(COMPONENT)' | sort -u)"
wanted=()
for component in contrib non-free; do
  grep -qx "$component" <<<"$present" || wanted+=("$component")
done
if [ "${#wanted[@]}" -eq 0 ]; then
  echo "contrib y non-free ya están configurados; actualizando índices"
  apt-get update
  exit 0
fi

. /etc/os-release
# Mismo espejo y misma clave que las fuentes de Debian existentes: APT rechaza
# dos Signed-By distintos para el mismo repositorio.
DEBIAN_SOURCES=/etc/apt/sources.list.d/debian.sources
field() { awk -v k="$1:" '$1 == k {sub(/^[^:]+: */, ""); print; exit}' "$DEBIAN_SOURCES" 2>/dev/null || true; }
uris="$(field URIs)"
signed_by="$(field Signed-By)"

echo "Añadiendo ${wanted[*]} en $SOURCES"
{
  echo "# Añadido por AppForge (entrada fonts)"
  echo "Types: deb"
  echo "URIs: ${uris:-http://deb.debian.org/debian}"
  echo "Suites: ${VERSION_CODENAME} ${VERSION_CODENAME}-updates"
  echo "Components: ${wanted[*]}"
  if [ -n "$signed_by" ]; then echo "Signed-By: $signed_by"; fi
} >"$SOURCES"
apt-get update
