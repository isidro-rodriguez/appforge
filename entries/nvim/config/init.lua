-- Configuración de Neovim instalada por AppForge (receta «nvim»).
-- Reaplicar la receta sobrescribe init.lua y lua/appforge/. Tus cambios van en
-- lua/local.lua, que AppForge crea vacío una vez y no vuelve a tocar.

vim.g.mapleader = " "
vim.g.maplocalleader = "\\"

require("appforge.options")
require("appforge.keymaps")
require("appforge.plugins")
require("appforge.lsp")

if vim.uv.fs_stat(vim.fn.stdpath("config") .. "/lua/local.lua") then
  require("local")
end
