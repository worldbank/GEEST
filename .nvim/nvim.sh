#!/usr/bin/env bash
# Neovim wrapper script

# Get the directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$SCRIPT_DIR"

# Change to the project root (parent of .nvim)
PROJECT_ROOT="$(dirname "$CONFIG_DIR")"
cd "$PROJECT_ROOT" || exit 1

# Start Neovim with the custom config
exec nvim \
    --cmd "lua package.path = '$CONFIG_DIR/lua/?.lua;$CONFIG_DIR/lua/?/init.lua;' .. package.path" \
    --cmd "lua vim.opt.rtp:prepend('$CONFIG_DIR')" \
    --cmd "lua dofile('$CONFIG_DIR/init.lua')" \
    "$@"
