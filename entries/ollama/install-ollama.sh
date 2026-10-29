#!/usr/bin/env bash
# Descarga Ollama $version ($arch), verifica su SHA-256 con el sha256sum.txt
# oficial de esa versión y lo extrae en /opt/ollama. Sin suma, no instala.
set -euo pipefail

ASSET="ollama-linux-${arch}.tar.zst"
BASE="https://github.com/ollama/ollama/releases/download/${version}"
BIN=/opt/ollama/bin/ollama

if [ -x "$BIN" ] && "$BIN" --version 2>/dev/null | grep -qF "${version#v}"; then
  echo "Ollama ${version} ya está instalado"
  exit 0
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

if ! curl -fsSL -o "$tmp/sha256sum.txt" "$BASE/sha256sum.txt"; then
  echo "No se pudo descargar sha256sum.txt de ${version}: ¿existe esa versión?" >&2
  exit 1
fi
expected="$(awk -v a="$ASSET" '$2 == a || $2 == "./" a {print $1}' "$tmp/sha256sum.txt")"
if [ -z "$expected" ]; then
  echo "La versión ${version} no publica la suma de ${ASSET}: no se instala" >&2
  exit 1
fi

echo "Descargando ${ASSET} (${version})…"
curl -fSL --progress-bar -o "$tmp/$ASSET" "$BASE/$ASSET"
echo "$expected  $tmp/$ASSET" | sha256sum -c -

mkdir -p /opt/ollama/models
rm -rf /opt/ollama/bin /opt/ollama/lib  # sin restos de la versión anterior
tar --zstd -x -C /opt/ollama -f "$tmp/$ASSET"
test -x "$BIN"
"$BIN" --version 2>/dev/null || true
