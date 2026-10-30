# ~/.bash_aliases.d/eza.sh — instalado por AppForge (receta bash-aliases).
# ls → eza solo en la shell interactiva; \ls o «command ls» dan el original.

if command -v eza >/dev/null 2>&1; then
  alias ls='eza --group-directories-first'
  alias l='ls'
  alias ll='eza -l --group-directories-first --git'
  alias la='eza -la --group-directories-first'
  alias lt='eza --tree --level=2'
fi
