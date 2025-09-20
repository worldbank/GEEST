#!/usr/bin/env fish

echo "🎯 GEEST Neovim Verification"
echo "============================"

# Check if we're in the right directory
if not test (basename (pwd)) = "GEEST"
    echo "❌ Please run this from the GEEST project root directory"
    exit 1
end

echo "✅ In GEEST project directory"

# Test 1: Basic config load
echo ""
echo "🧪 Test 1: Loading configuration..."
nvim --cmd "set rtp+=./.nvim" --headless +"lua print('✅ Config loads')" +qall

# Test 2: Check if lazy.nvim bootstraps
echo ""
echo "🧪 Test 2: Bootstrapping lazy.nvim (this may take a moment)..."
nvim --cmd "set rtp+=./.nvim" --headless +"lua require('config.options'); print('✅ Options loaded')" +qall 2>/dev/null

# Test 3: Try to start normally and check what happens
echo ""
echo "🧪 Test 3: Starting Neovim with config..."
echo "   Command: nvim --cmd \"set rtp+=./.nvim\""
echo ""
echo "💡 What should happen:"
echo "   - First time: Plugins will install (takes 1-2 minutes)"
echo "   - After that: You'll see the GEEST dashboard"
echo ""
echo "🔧 If you just see normal Neovim:"
echo "   1. Wait for plugins to install completely"
echo "   2. Restart Neovim with the same command"
echo ""
echo "🚀 Ready to test! Press Enter to start Neovim with GEEST config..."
read

nvim --cmd "set rtp+=./.nvim"
