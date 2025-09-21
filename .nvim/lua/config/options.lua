-- Basic Neovim options for Python development
local opt = vim.opt

-- Line numbers
opt.number = true
opt.relativenumber = true

-- Indentation (following Python standards)
opt.tabstop = 4
opt.shiftwidth = 4
opt.expandtab = true
opt.smartindent = true
opt.autoindent = true

-- Search
opt.ignorecase = true
opt.smartcase = true
opt.hlsearch = true
opt.incsearch = true

-- Display
opt.wrap = false
opt.cursorline = true
opt.signcolumn = "yes"
opt.colorcolumn = "88" -- PEP 8 line length for Python
opt.scrolloff = 8
opt.sidescrolloff = 8

-- Files and backup
opt.backup = false
opt.writebackup = false
opt.swapfile = false
opt.undofile = true
opt.undodir = vim.fn.stdpath("data") .. "/undo"

-- Splits
opt.splitbelow = true
opt.splitright = true

-- Clipboard
opt.clipboard = "unnamedplus"

-- Mouse
opt.mouse = "a"

-- Completion
opt.completeopt = "menu,menuone,noselect"

-- Update time
opt.updatetime = 50

-- Terminal colors
opt.termguicolors = true

-- Show matching brackets
opt.showmatch = true

-- Folding
opt.foldmethod = "indent"
opt.foldlevel = 99

-- File encoding
opt.encoding = "utf-8"
opt.fileencoding = "utf-8"
