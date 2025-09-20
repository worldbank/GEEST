-- Autocommands for better development experience

local augroup = vim.api.nvim_create_augroup
local autocmd = vim.api.nvim_create_autocmd

-- General autocommands
local general = augroup("General", { clear = true })

-- Highlight on yank
autocmd("TextYankPost", {
  group = general,
  callback = function()
    vim.highlight.on_yank({ higroup = "Visual", timeout = 200 })
  end,
})

-- Remove trailing whitespace on save
autocmd("BufWritePre", {
  group = general,
  pattern = "*",
  command = [[%s/\s\+$//e]],
})

-- Python specific autocommands
local python = augroup("Python", { clear = true })

-- Set Python specific options
autocmd("FileType", {
  group = python,
  pattern = "python",
  callback = function()
    vim.opt_local.colorcolumn = "88"  -- Black formatter line length
    vim.opt_local.textwidth = 88
  end,
})

-- Auto-close brackets and quotes
autocmd("FileType", {
  group = python,
  pattern = "python",
  callback = function()
    local opts = { buffer = true }
    vim.keymap.set("i", "(", "()<left>", opts)
    vim.keymap.set("i", "[", "[]<left>", opts)
    vim.keymap.set("i", "{", "{}<left>", opts)
    vim.keymap.set("i", '"', '""<left>', opts)
    vim.keymap.set("i", "'", "''<left>", opts)
  end,
})

-- Remember cursor position
autocmd("BufReadPost", {
  group = general,
  callback = function()
    local mark = vim.api.nvim_buf_get_mark(0, '"')
    local lcount = vim.api.nvim_buf_line_count(0)
    if mark[1] > 0 and mark[1] <= lcount then
      pcall(vim.api.nvim_win_set_cursor, 0, mark)
    end
  end,
})

-- Auto-create directories when writing files
autocmd("BufWritePre", {
  group = general,
  callback = function()
    local dir = vim.fn.expand("<afile>:p:h")
    if vim.fn.isdirectory(dir) == 0 then
      vim.fn.mkdir(dir, "p")
    end
  end,
})
