-- Lo ejecuta AppForge al aplicar la receta (nvim --headless con
-- g:appforge_bootstrap): init.lua ya clonó los plugins; aquí se instalan los
-- parsers y los servidores LSP base para que el primer arranque sea inmediato.
-- Sale con error si algo falla.
local function fail(msg)
  io.stderr:write("appforge: " .. msg .. "\n")
  vim.cmd("cquit 1")
end

local parsers = require("appforge.treesitter").parsers
local ok, err = pcall(function()
  require("nvim-treesitter").install(parsers):wait(30 * 60 * 1000)
end)
if not ok then
  fail("no se pudieron instalar los parsers: " .. tostring(err))
end
local missing = vim.tbl_filter(function(lang)
  return #vim.api.nvim_get_runtime_file("parser/" .. lang .. ".so", false) == 0
end, parsers)
if #missing > 0 then
  fail("faltan parsers: " .. table.concat(missing, ", "))
end

-- En modo headless :MasonInstall es síncrono.
local servers = { "lua-language-server", "bash-language-server" }
ok, err = pcall(vim.cmd, "MasonInstall " .. table.concat(servers, " "))
if not ok then
  fail("no se pudieron instalar los servidores LSP: " .. tostring(err))
end
for _, bin in ipairs(servers) do
  if vim.fn.executable(vim.fn.stdpath("data") .. "/mason/bin/" .. bin) == 0 then
    fail("Mason no instaló " .. bin)
  end
end
vim.cmd("qall!")
