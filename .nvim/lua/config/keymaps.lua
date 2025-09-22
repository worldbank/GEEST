-- Key mappings for enhanced productivity

local keymap = vim.keymap
local opts = { noremap = true, silent = true }

-- Clear search highlighting
keymap.set("n", "<leader>h", ":nohlsearch<CR>", { noremap = true, silent = true, desc = "Clear search highlighting" })

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
keymap.set("n", "<leader>bd", ":bdelete<CR>", { noremap = true, silent = true, desc = "Delete buffer" })

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
keymap.set("n", "<leader>w", ":w<CR>", { noremap = true, silent = true, desc = "Save file" })
keymap.set("n", "<leader>q", ":q<CR>", { noremap = true, silent = true, desc = "Quit" })
keymap.set("n", "<leader>Q", ":qa!<CR>", { noremap = true, silent = true, desc = "Force quit all" })

-- Split windows
keymap.set("n", "<leader>sv", ":vsplit<CR>", { noremap = true, silent = true, desc = "Split vertically" })
keymap.set("n", "<leader>sh", ":split<CR>", { noremap = true, silent = true, desc = "Split horizontally" })

-- Terminal
keymap.set("n", "<leader>t", ":terminal<CR>", { noremap = true, silent = true, desc = "Open terminal" })
keymap.set("t", "<Esc>", "<C-\\><C-n>", opts)

-- Better paste
keymap.set("v", "p", '"_dP', opts)

-- Quick fix list
keymap.set("n", "<leader>co", ":copen<CR>", { noremap = true, silent = true, desc = "Open quickfix" })
keymap.set("n", "<leader>cc", ":cclose<CR>", { noremap = true, silent = true, desc = "Close quickfix" })
keymap.set("n", "<leader>cn", ":cnext<CR>", { noremap = true, silent = true, desc = "Next quickfix" })
keymap.set("n", "<leader>cp", ":cprevious<CR>", { noremap = true, silent = true, desc = "Previous quickfix" })

-- Location list
keymap.set("n", "<leader>lo", ":lopen<CR>", { noremap = true, silent = true, desc = "Open location list" })
keymap.set("n", "<leader>lc", ":lclose<CR>", { noremap = true, silent = true, desc = "Close location list" })
keymap.set("n", "<leader>ln", ":lnext<CR>", { noremap = true, silent = true, desc = "Next location" })
keymap.set("n", "<leader>lp", ":lprevious<CR>", { noremap = true, silent = true, desc = "Previous location" })
