#!/usr/bin/env bash

# Script to list all shortcuts configured in GEEST Neovim configs
# Usage: ./scripts/show-nvim-shortcuts.sh

nvim_dir="/home/timlinux/dev/python/GEEST/.nvim"

{
    echo "# 🚀 GEEST Neovim Shortcuts"
    echo ""
    echo "**Leader key:** \`<Space>\`"
    echo ""

    # Function to extract all shortcuts from a file
    extract_shortcuts() {
        local file="$1"
        local category="$2"

        # Find all keymap.set or vim.keymap.set lines
        local shortcuts
        shortcuts=$(grep -n "keymap\.set" "$file" 2>/dev/null | head -50)

        if [[ -n "$shortcuts" ]]; then
            echo "## 📁 $category"
            echo ""
            echo "| Key | Mode | Description |"
            echo "|-----|------|-------------|"

            while IFS= read -r line; do
                local content
                content=$(echo "$line" | cut -d: -f2-)

                # Extract mode (first parameter after keymap.set)
                local mode_match
                mode_match=$(echo "$content" | grep -o '"[nvixstc]*"' | head -1 | tr -d '"')
                if [[ -z "$mode_match" ]]; then
                    mode_match=$(echo "$content" | grep -o "{ *\"[nvixstc]*\"" | head -1 | tr -d '{ "')
                fi
                [[ -z "$mode_match" ]] && mode_match="n"

                # Extract key combination (second parameter)
                local key_match
                key_match=$(echo "$content" | sed -n 's/.*keymap\.set([^"]*"\([^"]*\)".*/\1/p')
                if [[ -z "$key_match" ]]; then
                    key_match=$(echo "$content" | sed -n 's/.*keymap\.set([^"]*\([^"]*\)[",].*/\1/p')
                fi

                if [[ -n "$key_match" ]]; then
                    # Clean up the key
                    local key
                    key=${key_match//<leader>/<Space>}
                    local description=""

                    # Try to extract description from desc field or comments
                    if [[ "$content" =~ desc.*[\"\']([^\"\']*) ]]; then
                        description="${BASH_REMATCH[1]}"
                    elif [[ "$content" =~ --[[:space:]]*(.+)$ ]]; then
                        description="${BASH_REMATCH[1]}"
                    else
                        # Extract function names and commands
                        if [[ "$content" =~ vim\.lsp\.buf\.([a-zA-Z_]+) ]]; then
                            description="LSP: ${BASH_REMATCH[1]//_/ }"
                        elif [[ "$content" =~ builtin\.([a-zA-Z_]+) ]]; then
                            description="Telescope: ${BASH_REMATCH[1]//_/ }"
                        elif [[ "$content" =~ require.*telescope.*builtin.*\.([a-zA-Z_]+) ]]; then
                            description="Telescope: ${BASH_REMATCH[1]//_/ }"
                        elif [[ "$content" =~ :([a-zA-Z!]+) ]]; then
                            description="Command: ${BASH_REMATCH[1]}"
                        elif [[ "$content" =~ \"([^\"]*function[^\"]*) ]]; then
                            description="Function call"
                        else
                            description="Custom action"
                        fi
                    fi

                    # Format mode for display
                    local mode_display=""
                    case "$mode_match" in
                        n) mode_display="Normal" ;;
                        i) mode_display="Insert" ;;
                        v) mode_display="Visual" ;;
                        x) mode_display="Visual Block" ;;
                        s) mode_display="Select" ;;
                        t) mode_display="Terminal" ;;
                        c) mode_display="Command" ;;
                        *) mode_display="Multiple" ;;
                    esac

                    printf "| \`%s\` | %s | %s |\n" "$key" "$mode_display" "$description"
                fi
            done <<<"$shortcuts"
            echo ""
        fi
    }

    # Check for core keymaps file
    if [[ -f "$nvim_dir/lua/config/keymaps.lua" ]]; then
        extract_shortcuts "$nvim_dir/lua/config/keymaps.lua" "Core Keymaps"
    fi

    # LSP shortcuts (from lsp.lua)
    if [[ -f "$nvim_dir/lua/plugins/lsp.lua" ]]; then
        echo "## 📁 LSP Shortcuts (Active when LSP is attached)"
        echo ""
        echo "| Key | Mode | Description |"
        echo "|-----|------|-------------|"
        echo "| \`gD\` | Normal | Go to declaration |"
        echo "| \`<Alt-Space>\` | Normal | **Go to definition** |"
        echo "| \`K\` | Normal | Show hover information |"
        echo "| \`gi\` | Normal | Go to implementation |"
        echo "| \`<Ctrl-k>\` | Normal | Show signature help |"
        echo "| \`<Space>rn\` | Normal | Rename symbol |"
        echo "| \`<Space>ca\` | Normal/Visual | Code actions |"
        echo "| \`gr\` | Normal | Show references |"
        echo "| \`<Space>f\` | Normal | Format code |"
        echo ""
    fi

    # Plugin-specific shortcuts
    if [[ -d "$nvim_dir/lua/plugins" ]]; then
        while IFS= read -r -d '' file; do
            plugin_name=$(basename "$file" .lua)
            display_name=$(echo "$plugin_name" | sed 's/[_-]/ /g' | sed 's/\b\w/\U&/g')

            # Check if file has shortcuts (skip lsp.lua since we handled it specially)
            if [[ "$plugin_name" != "lsp" ]] && grep -q "keymap\.set" "$file" 2>/dev/null; then
                extract_shortcuts "$file" "Plugin: $display_name"
            fi
        done < <(find "$nvim_dir/lua/plugins" -name "*.lua" -type f -print0 | sort -z)
    fi

    echo "## � Tips"
    echo ""
    echo "- Use \`<Space>fk\` to search all keymaps with Telescope"
    echo "- Leader key is set to \`<Space>\` in init.lua"
    echo "- **\`<Alt-Space>\`** is your custom go-to-definition shortcut"
    echo "- Standard Vim shortcuts (like \`j\`, \`k\`, \`w\`, \`b\`) are not listed here"
    echo ""
    echo "## 🔧 Configuration Files"
    echo ""
    echo "To modify shortcuts, edit files in:"
    echo "- \`~/.nvim/lua/config/keymaps.lua\` (core shortcuts)"
    echo "- \`~/.nvim/lua/plugins/*.lua\` (plugin-specific shortcuts)"

} | glow
