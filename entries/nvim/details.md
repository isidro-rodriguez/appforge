Instala [Neovim](https://neovim.io) desde sus Releases de GitHub en `/opt/nvim`,
lo pone en lugar de **vi** y **vim** y deja una configuración de IDE ligero para el
usuario que ejecutó `sudo appforge`.

La versión es un parámetro. Neovim no publica un fichero de sumas: la descarga se
**verifica con el SHA-256 que GitHub publica para cada fichero de la Release**; sin
suma no se instala. Lo mismo vale para `tree-sitter-cli`. Para actualizar, vuelve a
aplicar la receta con otra versión.

### Qué deja instalado

- `/opt/nvim` con `nvim` y `tree-sitter`, enlazados en `/usr/local/bin`.
- `vi`, `vim`, `view` y `vimdiff` apuntan a Neovim (`update-alternatives`). Si
  tenías `vim` o `vim-tiny`, siguen instalados como reserva.
- Herramientas que usan los plugins: `git`, `gcc`, `ripgrep`, `fd-find`, `fzf`,
  Node.js y `npm`, `python3-venv`, `wl-clipboard` y `xclip`.
- La configuración en `~/.config/nvim`. Si ya tenías una, se mueve a
  `~/.config/nvim.backup-<fecha>`.

### La configuración

Usa el gestor de plugins de Neovim (`vim.pack`) con las versiones fijadas en
`nvim-pack-lock.json`:

| Función | Plugin |
|---|---|
| Tema | tokyonight.nvim |
| Barra de estado, pestañas, pares, *surround*, explorador, notificaciones | mini.nvim |
| Ayuda de atajos | which-key.nvim |
| Buscador de ficheros, texto y símbolos | fzf-lua |
| Resaltado y sangría por sintaxis | nvim-treesitter |
| LSP e instalación de servidores | nvim-lspconfig, mason.nvim, mason-lspconfig.nvim |
| Autocompletado y *snippets* | blink.cmp, friendly-snippets |
| Git | gitsigns.nvim |
| Formateo | conform.nvim |

Al aplicar se clonan los plugins, se compilan los parsers de tree-sitter y se
instalan los servidores de Lua y Bash: hace falta red y tarda unos minutos.

### Uso

`Espacio` es la tecla líder: púlsala y espera para ver todos los atajos. Los iconos
necesitan una Nerd Font en la terminal (receta «Fuentes adicionales»).

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

Tus ajustes van en `~/.config/nvim/lua/local.lua`. Reaplicar la receta sobrescribe
`init.lua` y `lua/appforge/`, pero no `local.lua` ni `nvim-pack-lock.json`.

Desinstalar quita `/opt/nvim` y sus enlaces; `vi` y `vim` vuelven a la alternativa
anterior, si la hay. Se conservan tu configuración y `~/.local/share/nvim`.
