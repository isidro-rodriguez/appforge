-- LSP: nvim-lspconfig aporta la configuración de cada servidor; Mason los
-- instala (:Mason) y mason-lspconfig activa los instalados (vim.lsp.enable).
-- Atajos de Neovim: K ayuda, grn renombrar, gra acciones, grr referencias,
-- gri implementación, gO símbolos, [d / ]d diagnósticos.

vim.diagnostic.config({
  severity_sort = true,
  virtual_text = { spacing = 2 },
  float = { source = "if_many" },
  signs = {
    text = {
      [vim.diagnostic.severity.ERROR] = "E",
      [vim.diagnostic.severity.WARN] = "W",
      [vim.diagnostic.severity.INFO] = "I",
      [vim.diagnostic.severity.HINT] = "H",
    },
  },
})

-- Lua con la API de Neovim (para editar esta misma configuración).
vim.lsp.config("lua_ls", {
  settings = {
    Lua = {
      runtime = { version = "LuaJIT" },
      diagnostics = { globals = { "vim" } },
      workspace = { checkThirdParty = false, library = { vim.env.VIMRUNTIME } },
    },
  },
})

require("mason").setup()
require("mason-lspconfig").setup({
  ensure_installed = { "lua_ls", "bashls" },
  automatic_enable = true,
})

vim.api.nvim_create_autocmd("LspAttach", {
  group = vim.api.nvim_create_augroup("appforge_lsp", { clear = true }),
  callback = function(ev)
    local fzf = require("fzf-lua")
    local function bmap(lhs, rhs, desc)
      vim.keymap.set("n", lhs, rhs, { buffer = ev.buf, desc = desc })
    end
    bmap("gd", fzf.lsp_definitions, "Ir a la definición")
    bmap("gD", vim.lsp.buf.declaration, "Ir a la declaración")
    bmap("<leader>ca", vim.lsp.buf.code_action, "Acciones de código")
    bmap("<leader>cr", vim.lsp.buf.rename, "Renombrar")
    bmap("<leader>ch", function()
      vim.lsp.inlay_hint.enable(not vim.lsp.inlay_hint.is_enabled({ bufnr = ev.buf }))
    end, "Pistas de tipos (on/off)")
  end,
})
