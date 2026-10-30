-- Opciones del editor.
local o = vim.opt

o.number = true
o.relativenumber = true
o.cursorline = true
o.signcolumn = "yes"
o.scrolloff = 8
o.sidescrolloff = 8
o.wrap = false
o.mouse = "a"
o.confirm = true
o.splitright = true
o.splitbelow = true
o.winborder = "rounded"

-- Tabulación: 4 espacios por defecto (los ftplugin y .editorconfig mandan).
o.expandtab = true
o.shiftwidth = 4
o.tabstop = 4
o.smartindent = true

-- Búsqueda.
o.ignorecase = true
o.smartcase = true
o.inccommand = "split"

-- Espacios visibles y persistencia.
o.list = true
o.listchars = { tab = "» ", trail = "·", nbsp = "␣" }
o.undofile = true
o.swapfile = false
o.updatetime = 250
o.timeoutlen = 400
o.completeopt = { "menu", "menuone", "noselect", "popup" }

-- Portapapeles del sistema (wl-clipboard o xclip); se activa tras el arranque
-- porque detectar el proveedor tarda.
vim.schedule(function()
  o.clipboard = "unnamedplus"
end)

-- Resalta lo copiado.
vim.api.nvim_create_autocmd("TextYankPost", {
  group = vim.api.nvim_create_augroup("appforge_yank", { clear = true }),
  callback = function()
    vim.hl.on_yank()
  end,
})
