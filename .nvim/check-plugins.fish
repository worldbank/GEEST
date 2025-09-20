#!/usr/bin/env fish

echo "🎯 GEEST Neovim Plugin Status Check"
echo "==================================="
echo ""

echo "💡 Commands to check plugins once Neovim is running:"
echo ""
echo "1. Open Lazy UI:        :Lazy"
echo "2. List plugins:        :Lazy show"
echo "3. Plugin info:         :Lazy show <plugin-name>"
echo "4. Update plugins:      :Lazy update"
echo "5. Clean unused:        :Lazy clean"
echo ""

echo "🔍 Your configured plugins should include:"
echo "  • alpha-nvim (dashboard)"
echo "  • telescope.nvim (fuzzy finder)"
echo "  • nvim-treesitter (syntax highlighting)"
echo "  • nvim-lspconfig (language server)"
echo "  • nvim-cmp (completion)"
echo "  • nvim-tree.lua (file explorer)"
echo "  • gitsigns.nvim (git integration)"
echo "  • lualine.nvim (status line)"
echo "  • tokyonight.nvim (colorscheme)"
echo "  • and more..."
echo ""

echo "🚀 Starting Neovim to check plugins..."
echo "   Once inside, type: :Lazy"
echo ""

nvim --cmd "set rtp+=./.nvim" +"lua print('🎯 GEEST Config Loaded! Type :Lazy to see plugins')"
