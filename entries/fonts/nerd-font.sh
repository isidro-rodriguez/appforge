#!/usr/bin/env bash
# Descarga JetBrainsMono Nerd Font ($nerd_version), la verifica con el SHA-256.txt
# oficial (obligatorio) y la instala para todo el sistema.
set -euo pipefail

DEST=/usr/local/share/fonts/nerd-fonts/JetBrainsMono
BASE="https://github.com/ryanoasis/nerd-fonts/releases/download/${nerd_version}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

curl -fsSL -o "$tmp/JetBrainsMono.tar.xz" "$BASE/JetBrainsMono.tar.xz"
if ! curl -fsSL -o "$tmp/SHA-256.txt" "$BASE/SHA-256.txt"; then
  echo "No se pudo descargar SHA-256.txt de ${nerd_version}: ¿existe esa versión?" >&2
  exit 1
fi
expected="$(awk '$2 == "JetBrainsMono.tar.xz" {print $1}' "$tmp/SHA-256.txt")"
if [ -z "$expected" ]; then
  echo "La versión ${nerd_version} no publica la suma de JetBrainsMono.tar.xz" >&2
  exit 1
fi
echo "$expected  $tmp/JetBrainsMono.tar.xz" | sha256sum -c -

rm -rf "$DEST"
mkdir -p "$DEST"
tar -xJf "$tmp/JetBrainsMono.tar.xz" -C "$DEST" --wildcards '*.ttf'
chmod -R a+rX "$DEST"
echo "Instaladas $(find "$DEST" -name '*.ttf' | wc -l) variantes en $DEST"
