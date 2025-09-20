#!/usr/bin/env fish

# GEEST Neovim Configuration Test Script
echo "🧪 Testing GEEST Neovim Configuration..."
echo ""

# Change to project directory
cd /home/timlinux/dev/python/GEEST

echo "📁 Current directory: "(pwd)
echo ""

# Test 1: Check if configuration files exist
echo "✅ Configuration Files:"
if test -f ".nvim/init.lua"
    echo "  ✓ .nvim/init.lua exists"
else
    echo "  ❌ .nvim/init.lua missing"
end

if test -d ".nvim/lua/config"
    echo "  ✓ Config directory exists"
else
    echo "  ❌ Config directory missing"
end

if test -d ".nvim/lua/plugins"
    echo "  ✓ Plugins directory exists"
else
    echo "  ❌ Plugins directory missing"
end

echo ""

# Test 2: Count plugin files
set plugin_count (ls .nvim/lua/plugins/*.lua 2>/dev/null | wc -l)
echo "📦 Found $plugin_count plugin configuration files"

echo ""

# Test 3: Syntax check the main init.lua
echo "🔍 Syntax Check:"
if luajit -bl .nvim/init.lua >/dev/null 2>&1
    echo "  ✓ init.lua syntax is valid"
else
    echo "  ❌ init.lua has syntax errors"
end

echo ""

# Test 4: Check if we can start Neovim with config (headless mode)
echo "🚀 Testing Neovim startup with configuration:"
echo "   Running: nvim --headless --cmd 'set rtp+=./.nvim' +q"

if nvim --headless --cmd "set rtp+=./.nvim" +q 2>/dev/null
    echo "  ✓ Neovim starts successfully with GEEST config"
else
    echo "  ❌ Neovim failed to start with configuration"
end

echo ""
echo "🎯 Manual Test Commands:"
echo ""
echo "  1. Start with dashboard:"
echo "     nvim --cmd 'set rtp+=./.nvim'"
echo ""
echo "  2. Test with a Python file:"
echo "     nvim --cmd 'set rtp+=./.nvim' geest/__init__.py"
echo ""
echo "  3. Check plugins are loading:"
echo "     nvim --cmd 'set rtp+=./.nvim' -c ':Lazy' -c 'q'"
echo ""
echo "  4. Test telescope:"
echo "     nvim --cmd 'set rtp+=./.nvim' -c ':Telescope find_files' -c 'q'"
echo ""

# Test 5: Create a fish function for convenience
echo "🐟 Fish Function Setup:"
echo "Add this to your ~/.config/fish/config.fish:"
echo ""
echo "function nvim-geest"
echo "    nvim --cmd \"set rtp+=./.nvim\" \$argv"
echo "end"
echo ""
echo "Then you can use: nvim-geest [filename]"
