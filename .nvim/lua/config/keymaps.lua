-- Key mappings for enhanced productivity

local keymap = vim.keymap
local opts = { noremap = true, silent = true }

-- Clear search highlighting
keymap.set("n", "<leader>h", ":nohlsearch<CR>", opts)

-- Better window navigation
keymap.set("n", "<C-h>", "<C-w>h", opts)
keymap.set("n", "<C-j>", "<C-w>j", opts)
keymap.set("n", "<C-k>", "<C-w>k", opts)
keymap.set("n", "<C-l>", "<C-w>l", opts)

-- Resize windows
keymap.set("n", "<C-Up>", ":resize +2<CR>", opts)
keymap.set("n", "<C-Down>", ":resize -2<CR>", opts)
keymap.set("n", "<C-Left>", ":vertical resize -2<CR>", opts)
keymap.set("n", "<C-Right>", ":vertical resize +2<CR>", opts)

-- Navigate buffers
keymap.set("n", "<S-l>", ":bnext<CR>", opts)
keymap.set("n", "<S-h>", ":bprevious<CR>", opts)
keymap.set("n", "<leader>bd", ":bdelete<CR>", opts)

-- Move text up and down
keymap.set("v", "<A-j>", ":m .+1<CR>==", opts)
keymap.set("v", "<A-k>", ":m .-2<CR>==", opts)
keymap.set("v", "p", '"_dP', opts)

-- Visual Block mode
keymap.set("n", "<A-j>", "<Esc>:m .+1<CR>==gi", opts)
keymap.set("n", "<A-k>", "<Esc>:m .-2<CR>==gi", opts)

-- Stay in indent mode
keymap.set("v", "<", "<gv", opts)
keymap.set("v", ">", ">gv", opts)

-- File operations
keymap.set("n", "<leader>w", ":w<CR>", opts)
keymap.set("n", "<leader>q", ":q<CR>", opts)
keymap.set("n", "<leader>Q", ":qa!<CR>", opts)

-- Split windows
keymap.set("n", "<leader>sv", ":vsplit<CR>", opts)
keymap.set("n", "<leader>sh", ":split<CR>", opts)

-- Terminal
keymap.set("n", "<leader>t", ":terminal<CR>", opts)
keymap.set("t", "<Esc>", "<C-\\><C-n>", opts)

-- Better paste
keymap.set("v", "p", '"_dP', opts)

-- Quick fix list
keymap.set("n", "<leader>co", ":copen<CR>", opts)
keymap.set("n", "<leader>cc", ":cclose<CR>", opts)
keymap.set("n", "<leader>cn", ":cnext<CR>", opts)
keymap.set("n", "<leader>cp", ":cprevious<CR>", opts)

-- Location list
keymap.set("n", "<leader>lo", ":lopen<CR>", opts)
keymap.set("n", "<leader>lc", ":lclose<CR>", opts)
keymap.set("n", "<leader>ln", ":lnext<CR>", opts)
keymap.set("n", "<leader>lp", ":lprevious<CR>", opts)
