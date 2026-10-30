#!/usr/bin/env bash
# Instala Neovim $version ($arch) en /opt/nvim y tree-sitter-cli $ts_version
# (lo necesita nvim-treesitter para compilar parsers) en /opt/nvim/bin.
# Ambos se verifican con el SHA-256 de GitHub; enlaces en /usr/local/bin.
set -euo pipefail
source "$APPFORGE_ENTRY_DIR/github-asset.sh"

case "$arch" in
  amd64) nvim_arch=x86_64 ts_arch=x64 ;;
  arm64) nvim_arch=arm64 ts_arch=arm64 ;;
  *) echo "Arquitectura no soportada: $arch (amd64 | arm64)" >&2; exit 1 ;;
esac

PREFIX=/opt/nvim
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$PREFIX/bin"

# Neovim
if "$PREFIX/bin/nvim" --version 2>/dev/null | head -1 | grep -qxF "NVIM ${version}"; then
  echo "Neovim ${version} ya está instalado"
else
  asset="nvim-linux-${nvim_arch}.tar.gz"
  fetch_verified neovim/neovim "$version" "$asset" "$tmp/$asset"
  # Sin restos de la versión anterior (conserva bin/tree-sitter y lo de AppForge).
  rm -rf "$PREFIX/lib" "$PREFIX/share" "$PREFIX/bin/nvim"
  tar -xzf "$tmp/$asset" -C "$PREFIX" --strip-components=1
  "$PREFIX/bin/nvim" --version | head -1
fi

# tree-sitter-cli
if "$PREFIX/bin/tree-sitter" --version 2>/dev/null | grep -qF "${ts_version#v}"; then
  echo "tree-sitter ${ts_version} ya está instalado"
else
  asset="tree-sitter-linux-${ts_arch}.gz"
  fetch_verified tree-sitter/tree-sitter "$ts_version" "$asset" "$tmp/$asset"
  gunzip -c "$tmp/$asset" >"$tmp/tree-sitter"
  install -m 0755 "$tmp/tree-sitter" "$PREFIX/bin/tree-sitter"
  "$PREFIX/bin/tree-sitter" --version
fi

ln -sfn "$PREFIX/bin/nvim" /usr/local/bin/nvim
ln -sfn "$PREFIX/bin/tree-sitter" /usr/local/bin/tree-sitter
