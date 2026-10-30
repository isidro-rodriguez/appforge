#!/usr/bin/env bash
# Funciones comunes (se carga con `source`): descarga un fichero de una Release de
# GitHub y lo verifica con el SHA-256 que GitHub publica para ese fichero (campo
# `digest` de la API de Releases, inmutable). Neovim y tree-sitter no publican un
# fichero de sumas propio. Sin suma, no se instala.

# fetch_verified <owner/repo> <tag> <asset> <destino>
fetch_verified() {
  local repo="$1" tag="$2" asset="$3" dest="$4" meta digest
  meta="$(mktemp)"
  if ! curl -fsSL -H 'Accept: application/vnd.github+json' \
    -o "$meta" "https://api.github.com/repos/${repo}/releases/tags/${tag}"; then
    rm -f "$meta"
    echo "No se pudo consultar la Release ${tag} de ${repo}: ¿existe esa versión?" >&2
    return 1
  fi
  digest="$(jq -r --arg a "$asset" \
    '.assets[] | select(.name == $a) | .digest // empty' "$meta")"
  rm -f "$meta"
  digest="${digest#sha256:}"
  if ! [[ "$digest" =~ ^[0-9a-f]{64}$ ]]; then
    echo "${repo} ${tag} no publica el SHA-256 de ${asset}: no se instala" >&2
    return 1
  fi
  echo "Descargando ${asset} (${repo} ${tag})…"
  curl -fSL --progress-bar -o "$dest" \
    "https://github.com/${repo}/releases/download/${tag}/${asset}"
  echo "$digest  $dest" | sha256sum -c -
}
