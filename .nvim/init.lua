-- GEEST Project Neovim Configuration
-- Minimal but functional setup for Python development

-- Set leader key early
vim.g.mapleader = " "
vim.g.maplocalleader = " "

-- Debug function for checking tools availability
local function check_tools()
    local tools = {
        "black", "flake8", "mypy", "shellcheck", "shfmt", "luacheck", "stylua"
    }

    local function log_tool_status(tool)
        if vim.fn.executable(tool) == 1 then
            vim.notify("✓ " .. tool .. " found", vim.log.levels.INFO)
        else
            vim.notify("✗ " .. tool .. " not found in PATH", vim.log.levels.WARN)
        end
    end

    vim.notify("=== Tool Availability Check ===", vim.log.levels.INFO)
    for _, tool in ipairs(tools) do
        log_tool_status(tool)
    end
    vim.notify("=== End Tool Check ===", vim.log.levels.INFO)
end

-- Create command to check tools manually
vim.api.nvim_create_user_command("CheckTools", check_tools, { desc = "Check external tool availability" })

-- Automatically check tools on startup (optional - comment out if too noisy)
vim.api.nvim_create_autocmd("VimEnter", {
    callback = function()
        -- Delay the check to avoid startup message clutter
        vim.defer_fn(check_tools, 2000) -- 2 second delay
    end,
})

-- Bootstrap lazy.nvim plugin manager
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
  vim.fn.system({
    "git",
    "clone",
    "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git",
    "--branch=stable", -- latest stable release
    lazypath,
  })
end
vim.opt.rtp:prepend(lazypath)

-- Load configuration modules
require("config.options")
require("config.keymaps")
require("config.autocmds")

-- Setup plugins
require("lazy").setup({
  -- Import all plugin configurations
  { import = "plugins" },
}, {
  change_detection = {
    notify = false,
  },
})
