# ~/.bash_aliases.d/eza.sh — instalado por AppForge (receta bash-aliases).
# ls → eza solo en la shell interactiva; \ls o «command ls» dan el original.
# Con iconos: necesita una Nerd Font en el terminal.

if command -v eza >/dev/null 2>&1; then
  alias ls='eza --icons=auto --group-directories-first'
  alias l='ls'
  alias ll='eza -l --icons=auto --group-directories-first --git'
  alias la='eza -la --icons=auto --group-directories-first'
  alias lt='eza --tree --level=2 --icons=auto'
fi
