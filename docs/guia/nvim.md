# Receta incluida: Neovim

Instala [Neovim](https://neovim.io) en `/opt/nvim`, lo pone en lugar de `vi` y `vim`
y deja una configuración de IDE ligero de terminal para el usuario que ejecutó
`sudo appforge`.

## Qué instala

| Elemento | Dónde |
|---|---|
| Neovim (Release oficial de GitHub) | `/opt/nvim`, enlace `/usr/local/bin/nvim` |
| `tree-sitter-cli` (compila los parsers) | `/opt/nvim/bin/tree-sitter`, enlace `/usr/local/bin/tree-sitter` |
| `vi`, `vim`, `view`, `vimdiff` | `update-alternatives`, apuntando a Neovim |
| Configuración | `~/.config/nvim` (copia de referencia en `/opt/nvim/appforge/config`) |
| Plugins, parsers y servidores LSP | `~/.local/share/nvim` |
| Paquetes de Debian | `git`, `gcc`, `ripgrep`, `fd-find`, `fzf`, `jq`, `nodejs`, `npm`, `python3-venv`, `wl-clipboard`, `xclip` |

## Antes de instalar

- Neovim y `tree-sitter` no publican un fichero de sumas. La descarga se verifica
  con el **SHA-256 que GitHub publica para cada fichero de la Release** (inmutable);
  sin suma, no se instala.
- Si ya tienes `~/.config/nvim`, se mueve a `~/.config/nvim.backup-<fecha>`.
- Al aplicar se clonan los plugins, se compilan los parsers y se instalan los
  servidores de Lua y Bash: hace falta red y tarda unos minutos.
- Para ver los iconos, usa en la terminal una Nerd Font (por ejemplo, la de la
  receta [fuentes](fuentes.md)).

## Parámetros

| Parámetro | Por defecto | Uso |
|---|---|---|
| `version` | `v0.12.6` | Versión de Neovim; el formulario enlaza a sus [Releases](https://github.com/neovim/neovim/releases) |
| `ts_version` | `v0.27.1` | Versión de `tree-sitter-cli` ([Releases](https://github.com/tree-sitter/tree-sitter/releases)) |
| `arch` | `amd64` | `amd64` o `arm64` |

## La configuración

Usa el gestor de plugins incluido en Neovim (`vim.pack`), con las versiones fijadas
en `~/.config/nvim/nvim-pack-lock.json`.

| Función | Plugin |
|---|---|
| Tema | tokyonight.nvim |
| Barra de estado, pestañas, pares, *surround*, explorador, notificaciones | mini.nvim |
| Ayuda de atajos | which-key.nvim |
| Buscador de ficheros, texto y símbolos | fzf-lua |
| Resaltado, sangría y plegado por sintaxis | nvim-treesitter |
| LSP e instalación de servidores | nvim-lspconfig, mason.nvim, mason-lspconfig.nvim |
| Autocompletado y *snippets* | blink.cmp, friendly-snippets |
| Git | gitsigns.nvim |
| Formateo | conform.nvim |

### Atajos principales

La tecla líder es `Espacio`: púlsala y espera para ver todos los atajos.

| Atajo | Acción |
|---|---|
| `Espacio ff` / `Espacio fg` | Buscar ficheros / texto en el proyecto |
| `Espacio Espacio` | Buffers abiertos |
| `Espacio fe` | Explorador de ficheros |
| `gd`, `K`, `grr`, `grn` | Definición, documentación, referencias, renombrar |
| `Espacio ca` / `Espacio cf` | Acciones de código / formatear |
| `]h`, `[h`, `Espacio gp` | Navegar y ver cambios de git |
| `Espacio t` | Terminal |

Más servidores de lenguaje y formateadores: `:Mason`. Actualizar los plugins:
`:lua vim.pack.update()`.

### Tus ajustes

Van en `~/.config/nvim/lua/local.lua`. Reaplicar la receta sobrescribe `init.lua` y
`lua/appforge/`, pero no `local.lua` ni `nvim-pack-lock.json`.

## Desinstalar

Quita `/opt/nvim` y sus enlaces; `vi` y `vim` vuelven a la alternativa anterior, si
la hay. Se conservan tu configuración y `~/.local/share/nvim`.
