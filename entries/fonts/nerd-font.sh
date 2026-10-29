#!/usr/bin/env bash
# Descarga JetBrainsMono Nerd Font ($nerd_version) y la instala para todo el sistema.
set -euo pipefail

DEST=/usr/local/share/fonts/nerd-fonts/JetBrainsMono
BASE="https://github.com/ryanoasis/nerd-fonts/releases/download/${nerd_version}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

curl -fsSL -o "$tmp/JetBrainsMono.tar.xz" "$BASE/JetBrainsMono.tar.xz"
if curl -fsSL -o "$tmp/SHA-256.txt" "$BASE/SHA-256.txt"; then
  expected="$(awk '$2 == "JetBrainsMono.tar.xz" {print $1}' "$tmp/SHA-256.txt")"
  if [ -n "$expected" ]; then
    echo "$expected  $tmp/JetBrainsMono.tar.xz" | sha256sum -c -
  else
    echo "SHA-256.txt no incluye JetBrainsMono.tar.xz: sin verificar"
  fi
else
  echo "La versión ${nerd_version} no publica SHA-256.txt: sin verificar"
fi

rm -rf "$DEST"
mkdir -p "$DEST"
tar -xJf "$tmp/JetBrainsMono.tar.xz" -C "$DEST" --wildcards '*.ttf'
chmod -R a+rX "$DEST"
echo "Instaladas $(find "$DEST" -name '*.ttf' | wc -l) variantes en $DEST"
