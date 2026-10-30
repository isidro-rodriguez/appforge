-- Tree-sitter (rama main de nvim-treesitter): compila los parsers con
-- tree-sitter-cli y gcc. Añade lenguajes a `parsers` o usa :TSInstall <lenguaje>.
local M = {}

M.parsers = {
  "bash", "c", "css", "diff", "dockerfile", "git_config", "gitcommit",
  "gitignore", "go", "html", "javascript", "json", "lua", "luadoc",
  "make", "markdown", "markdown_inline", "python", "query", "regex",
  "rust", "toml", "typescript", "vim", "vimdoc", "yaml",
}

function M.setup()
  local ts = require("nvim-treesitter")
  -- Instala en segundo plano lo que falte; no hace nada si ya están.
  -- Durante la preparación de AppForge lo hace bootstrap.lua, esperando.
  if not vim.g.appforge_bootstrap then
    ts.install(M.parsers)
  end

  vim.api.nvim_create_autocmd("FileType", {
    group = vim.api.nvim_create_augroup("appforge_treesitter", { clear = true }),
    callback = function(ev)
      if not pcall(vim.treesitter.start, ev.buf) then
        return -- sin parser para este tipo de fichero
      end
      vim.bo[ev.buf].indentexpr = "v:lua.require'nvim-treesitter'.indentexpr()"
      vim.wo[0][0].foldmethod = "expr"
      vim.wo[0][0].foldexpr = "v:lua.vim.treesitter.foldexpr()"
      vim.wo[0][0].foldlevel = 99
    end,
  })
end

return M
