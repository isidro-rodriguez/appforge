-- Plugins de la comunidad, gestionados con vim.pack (incluido en Neovim 0.12).
-- Versiones fijadas en nvim-pack-lock.json; actualizar: :lua vim.pack.update()
local gh = function(repo)
  return "https://github.com/" .. repo
end

-- Tras actualizar nvim-treesitter, los parsers deben ir a la par.
vim.api.nvim_create_autocmd("PackChanged", {
  group = vim.api.nvim_create_augroup("appforge_pack", { clear = true }),
  callback = function(ev)
    if ev.data.spec.name == "nvim-treesitter" and ev.data.kind == "update" then
      if not ev.data.active then
        vim.cmd.packadd("nvim-treesitter")
      end
      vim.cmd("TSUpdate")
    end
  end,
})

vim.pack.add({
  gh("folke/tokyonight.nvim"),
  gh("nvim-mini/mini.nvim"),
  gh("folke/which-key.nvim"),
  gh("ibhagwan/fzf-lua"),
  { src = gh("nvim-treesitter/nvim-treesitter"), version = "main" },
  gh("neovim/nvim-lspconfig"),
  gh("mason-org/mason.nvim"),
  gh("mason-org/mason-lspconfig.nvim"),
  { src = gh("saghen/blink.cmp"), version = vim.version.range("1.*") },
  gh("rafamadriz/friendly-snippets"),
  gh("lewis6991/gitsigns.nvim"),
  gh("stevearc/conform.nvim"),
}, { confirm = false })

local map = vim.keymap.set

-- Tema ------------------------------------------------------------------
require("tokyonight").setup({ style = "night" })
vim.cmd.colorscheme("tokyonight")

-- mini.nvim: iconos, barra de estado, pares, surround, objetos de texto,
-- explorador de ficheros, sangría y notificaciones -------------------------
require("mini.icons").setup()
MiniIcons.mock_nvim_web_devicons()
require("mini.statusline").setup()
require("mini.tabline").setup()
require("mini.pairs").setup()
require("mini.surround").setup()
require("mini.ai").setup({ n_lines = 500 })
require("mini.indentscope").setup({ symbol = "│" })
require("mini.notify").setup()
vim.notify = require("mini.notify").make_notify()
require("mini.files").setup({ windows = { preview = true } })
map("n", "<leader>fe", function()
  local path = vim.api.nvim_buf_get_name(0)
  MiniFiles.open(path ~= "" and path or nil)
end, { desc = "Explorador de ficheros" })

-- which-key: muestra los atajos disponibles al pulsar <leader> ---------------
require("which-key").setup({ preset = "modern" })
require("which-key").add({
  { "<leader>f", group = "Buscar" },
  { "<leader>g", group = "Git" },
  { "<leader>c", group = "Código" },
})

-- fzf-lua: buscador difuso (ficheros, texto, LSP...) -------------------------
local fzf = require("fzf-lua")
fzf.setup({ "default-title" })
fzf.register_ui_select()
map("n", "<leader><leader>", fzf.buffers, { desc = "Buffers abiertos" })
map("n", "<leader>ff", fzf.files, { desc = "Ficheros" })
map("n", "<leader>fg", fzf.live_grep, { desc = "Texto en el proyecto" })
map("n", "<leader>fw", fzf.grep_cword, { desc = "Palabra bajo el cursor" })
map("n", "<leader>fr", fzf.oldfiles, { desc = "Recientes" })
map("n", "<leader>fh", fzf.helptags, { desc = "Ayuda" })
map("n", "<leader>fk", fzf.keymaps, { desc = "Atajos" })
map("n", "<leader>fd", fzf.diagnostics_workspace, { desc = "Diagnósticos" })
map("n", "<leader>fs", fzf.lsp_document_symbols, { desc = "Símbolos del fichero" })
map("n", "<leader>f.", fzf.resume, { desc = "Repetir la última búsqueda" })
map("n", "<leader>/", fzf.blines, { desc = "Buscar en el buffer" })

-- Tree-sitter: resaltado, sangría y plegado por sintaxis ---------------------
require("appforge.treesitter").setup()

-- Autocompletado ------------------------------------------------------------
require("blink.cmp").setup({
  keymap = { preset = "default" }, -- <C-y> acepta, <C-n>/<C-p> navegan
  completion = { documentation = { auto_show = true } },
  signature = { enabled = true },
  sources = { default = { "lsp", "path", "snippets", "buffer" } },
  -- Implementación en Lua: sin descargar el binario precompilado.
  fuzzy = { implementation = "lua" },
})

-- Git -----------------------------------------------------------------------
require("gitsigns").setup({
  on_attach = function(buf)
    local gs = require("gitsigns")
    local function bmap(lhs, rhs, desc)
      map("n", lhs, rhs, { buffer = buf, desc = desc })
    end
    bmap("]h", function()
      gs.nav_hunk("next")
    end, "Siguiente cambio")
    bmap("[h", function()
      gs.nav_hunk("prev")
    end, "Cambio anterior")
    bmap("<leader>gs", gs.stage_hunk, "Preparar el cambio (stage)")
    bmap("<leader>gr", gs.reset_hunk, "Descartar el cambio")
    bmap("<leader>gp", gs.preview_hunk, "Ver el cambio")
    bmap("<leader>gb", gs.blame_line, "Autor de la línea (blame)")
    bmap("<leader>gd", gs.diffthis, "Diff del fichero")
  end,
})
map("n", "<leader>gc", fzf.git_commits, { desc = "Commits" })
map("n", "<leader>gS", fzf.git_status, { desc = "Estado (status)" })

-- Formateo ------------------------------------------------------------------
-- Usa el formateador del lenguaje si está instalado (:Mason) y, si no, el LSP.
require("conform").setup({
  formatters_by_ft = {
    lua = { "stylua" },
    python = { "ruff_format" },
    sh = { "shfmt" },
    bash = { "shfmt" },
    javascript = { "prettier" },
    typescript = { "prettier" },
    json = { "prettier" },
    yaml = { "prettier" },
    markdown = { "prettier" },
  },
  default_format_opts = { lsp_format = "fallback" },
})
map({ "n", "v" }, "<leader>cf", function()
  require("conform").format({ async = true })
end, { desc = "Formatear" })
