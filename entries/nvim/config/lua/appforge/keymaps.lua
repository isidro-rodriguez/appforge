-- Atajos generales. Los de cada plugin están en plugins.lua y lsp.lua.
-- <leader> es la barra espaciadora; which-key muestra el resto al pulsarla.
local map = vim.keymap.set

map("n", "<Esc>", "<cmd>nohlsearch<CR>", { desc = "Quitar resaltado de búsqueda" })
map("n", "<leader>w", "<cmd>write<CR>", { desc = "Guardar" })
map("n", "<leader>q", "<cmd>confirm qall<CR>", { desc = "Salir" })

-- Ventanas.
map("n", "<C-h>", "<C-w>h", { desc = "Ventana izquierda" })
map("n", "<C-j>", "<C-w>j", { desc = "Ventana inferior" })
map("n", "<C-k>", "<C-w>k", { desc = "Ventana superior" })
map("n", "<C-l>", "<C-w>l", { desc = "Ventana derecha" })

-- Mover líneas seleccionadas.
map("v", "J", ":m '>+1<CR>gv=gv", { desc = "Bajar selección", silent = true })
map("v", "K", ":m '<-2<CR>gv=gv", { desc = "Subir selección", silent = true })

-- Diagnósticos ([d / ]d ya vienen en Neovim).
map("n", "<leader>e", vim.diagnostic.open_float, { desc = "Diagnóstico de la línea" })

-- Terminal integrada.
map("n", "<leader>t", "<cmd>botright 12split | terminal<CR>", { desc = "Terminal" })
map("t", "<Esc><Esc>", "<C-\\><C-n>", { desc = "Salir del modo terminal" })
