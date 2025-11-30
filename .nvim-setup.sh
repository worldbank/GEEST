#!/bin/bash
# Setup script for nvim with QGIS libraries in nix environment
# Run this after 'nix develop' to ensure proper Python paths

set -e

echo "Setting up nvim environment for GEEST project..."

# Ensure we're in a nix develop shell
if [ -z "$NIX_SHELL" ] && [ -z "$IN_NIX_SHELL" ]; then
    echo "Warning: Not in a nix develop shell. Run 'nix develop' first."
    echo "Continuing anyway..."
fi

# Find QGIS Python modules from nix store
QGIS_PYTHON_PATH=""
if [ -n "$NIX_STORE" ]; then
    # Try to find QGIS Python path in the current environment
    QGIS_PATHS=$(find /nix/store -maxdepth 2 -name "qgis-*" -type d 2>/dev/null | head -5)
    for path in $QGIS_PATHS; do
        if [ -d "$path/share/qgis/python" ]; then
            QGIS_PYTHON_PATH="$path/share/qgis/python"
            break
        fi
    done
fi

# Also check if PYTHONPATH is already set by the nix flake
if [ -n "$PYTHONPATH" ]; then
    echo "Found existing PYTHONPATH: $PYTHONPATH"
    # Extract QGIS path from PYTHONPATH if present
    IFS=':' read -ra PATHS <<< "$PYTHONPATH"
    for path in "${PATHS[@]}"; do
        if [[ $path == *"qgis/python"* ]]; then
            QGIS_PYTHON_PATH="$path"
            break
        fi
    done
fi

if [ -n "$QGIS_PYTHON_PATH" ]; then
    echo "Found QGIS Python path: $QGIS_PYTHON_PATH"
    export QGIS_PYTHON_PATH
else
    echo "Warning: Could not find QGIS Python path. LSP may not have QGIS completions."
fi

# Export Python path for nvim LSP
export NVIM_PYTHON_PATH="$PYTHONPATH"

# Check for Node.js (required for GitHub Copilot)
if ! command -v node &> /dev/null; then
    echo "Warning: Node.js not found. GitHub Copilot requires Node.js."
    echo "Install Node.js or ensure it's available in your PATH for Copilot to work."
fi

# Check for Anthropic API key (required for Claude chat)
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Info: Set ANTHROPIC_API_KEY environment variable for Claude chat integration."
    echo "Example: export ANTHROPIC_API_KEY=your_api_key_here"
fi

echo "Environment configured. You can now run 'nvim' or 'vim' (aliased to nvim)."
echo "QGIS libraries should be available for autocompletion and type checking."
echo "Additional features:"
echo "  - GitHub Copilot: Alt+L to accept suggestions, Alt+] for next, Alt+[ for previous"
echo "  - Claude Chat: <leader>cc to open chat, <leader>cr to reset, <leader>cx to close"

# Create a simple alias for vim -> nvim in the current shell
alias vim=nvim

# Function to start nvim with proper settings
nvim_geest() {
    echo "Starting nvim with GEEST configuration..."
    nvim "$@"
}

# Export the function so it's available in the shell
export -f nvim_geest

echo ""
echo "Quick start:"
echo "  nvim filename.py     # Start nvim with QGIS libraries configured"
echo "  vim filename.py      # Same as above (vim is aliased to nvim)"
echo "  nvim_geest           # Alternative command"
