#!/usr/bin/env bash
# GEEST Neovim Setup and Test Script

echo "🎯 GEEST Neovim Configuration Setup"
echo "==================================="

# Set the project root
PROJECT_ROOT="/home/timlinux/dev/python/GEEST"
NVIM_CONFIG="$PROJECT_ROOT/.nvim"

echo "📁 Configuration location: $NVIM_CONFIG"

# Check if configuration exists
if [ ! -d "$NVIM_CONFIG" ]; then
    echo "❌ Configuration directory not found!"
    exit 1
fi

echo "✅ Configuration directory exists"

# Check if init.lua exists
if [ ! -f "$NVIM_CONFIG/init.lua" ]; then
    echo "❌ init.lua not found!"
    exit 1
fi

echo "✅ init.lua found"

# Test configuration load
echo ""
echo "🧪 Testing configuration load..."

cd "$PROJECT_ROOT"
nvim --cmd "set rtp+=./.nvim" --headless +"lua print('Config loaded')" +qall

if [ $? -eq 0 ]; then
    echo "✅ Configuration loads successfully"
else
    echo "❌ Configuration failed to load"
    exit 1
fi

# Create Fish function
echo ""
echo "🐟 Creating Fish function..."

FISH_FUNCTION_DIR="$HOME/.config/fish/functions"
mkdir -p "$FISH_FUNCTION_DIR"

cat >"$FISH_FUNCTION_DIR/nvim-geest.fish" <<'EOF'
function nvim-geest --description 'Start Neovim with GEEST configuration'
    set -l project_root /home/timlinux/dev/python/GEEST

    if test (pwd) = "$project_root"; or string match -q "$project_root/*" (pwd)
        nvim --cmd "set rtp+=./.nvim" $argv
    else
        echo "⚠️  You must be in the GEEST project directory"
        echo "📍 Expected: $project_root"
        echo "📍 Current:  "(pwd)
    end
end
EOF

echo "✅ Fish function created: ~/.config/fish/functions/nvim-geest.fish"

echo ""
echo "🎉 Setup Complete!"
echo ""
echo "💡 Usage:"
echo "   1. Navigate to your GEEST project: cd $PROJECT_ROOT"
echo "   2. Run: nvim-geest"
echo ""
echo "🔧 Manual command:"
echo "   nvim --cmd \"set rtp+=./.nvim\""
echo ""
echo "⚠️  Note: Plugins will install automatically on first run"
echo "   This may take a minute or two the first time."
