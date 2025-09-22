#!/usr/bin/env fish

# Script to list all leader shortcuts configured in GEEST Neovim configs
# Usage: ./scripts/list-nvim-leader-shortcuts.fish

set -l nvim_dir "/home/timlinux/dev/python/GEEST/.nvim"

echo "🚀 GEEST Neovim Leader Key Shortcuts"
echo "===================================="
echo ""
echo "Leader key: <Space>"
echo ""

# Function to extract leader shortcuts from a file
function extract_leader_shortcuts
    set -l file $argv[1]
    set -l category $argv[2]

    # Find all keymap.set or vim.keymap.set lines with <leader>
    set -l shortcuts (grep -n "keymap\.set.*<leader>" $file 2>/dev/null | head -20)

    if test (count $shortcuts) -gt 0
        echo "📁 $category"
        echo (string repeat -n (string length "$category") "-")

        for line in $shortcuts
            set -l line_num (string split ":" $line)[1]
            set -l content (string split ":" $line)[2..-1] | string join ":"

            # Extract the key combination
            set -l key_match (string match -r '<leader>[^"\'>,)]*' $content)

            if test -n "$key_match"
                set -l key (string replace "<leader>" "<Space>" $key_match)
                set -l description ""

                # Try to extract description from desc field
                set -l desc_match (string match -r 'desc.*?["\']([^"\']*)["\']' $content)
                if test (count $desc_match) -gt 1
                    set description $desc_match[2]
                else
                    # Try to extract command from quotes
                    set -l command_match (string match -r '["\'](:[^"\']+)["\']' $content)
                    if test (count $command_match) -gt 1
                        set description (string replace ":" "" $command_match[2])
                    else
                        # Extract telescope builtin functions
                        set -l func_match (string match -r 'builtin\.([a-zA-Z_]+)' $content)
                        if test (count $func_match) -gt 1
                            set description "Telescope: "(string replace "_" " " $func_match[2])
                        else
                            # Extract LSP functions
                            set -l lsp_match (string match -r 'vim\.lsp\.buf\.([a-zA-Z_]+)' $content)
                            if test (count $lsp_match) -gt 1
                                set description "LSP: "(string replace "_" " " $lsp_match[2])
                            else
                                # Extract command names from common patterns
                                switch $content
                                    case '*nohlsearch*'
                                        set description "Clear search highlighting"
                                    case '*bdelete*'
                                        set description "Delete buffer"
                                    case '*:w<*'
                                        set description "Save file"
                                    case '*:q<*'
                                        set description "Quit"
                                    case '*:qa!*'
                                        set description "Quit all without saving"
                                    case '*vsplit*'
                                        set description "Vertical split"
                                    case '*split*'
                                        set description "Horizontal split"
                                    case '*terminal*'
                                        set description "Open terminal"
                                    case '*copen*'
                                        set description "Open quickfix list"
                                    case '*cclose*'
                                        set description "Close quickfix list"
                                    case '*cnext*'
                                        set description "Next quickfix item"
                                    case '*cprevious*'
                                        set description "Previous quickfix item"
                                    case '*lopen*'
                                        set description "Open location list"
                                    case '*lclose*'
                                        set description "Close location list"
                                    case '*lnext*'
                                        set description "Next location item"
                                    case '*lprevious*'
                                        set description "Previous location item"
                                    case '*function*'
                                        set description "Custom function"
                                    case '*'
                                        set description "Custom action"
                                end
                            end
                        end
                    end
                end

                printf "  %-20s %s\n" $key $description
            end
        end
        echo ""
    end
end

# Core keymaps
extract_leader_shortcuts "$nvim_dir/lua/config/keymaps.lua" "Core Keymaps"

# Plugin-specific shortcuts
set -l plugin_files (find "$nvim_dir/lua/plugins" -name "*.lua" -type f | sort)

for file in $plugin_files
    set -l plugin_name (basename $file .lua)
    set -l display_name (string replace -r '^([a-z])' (string upper '$1') (string replace '_' ' ' (string replace '-' ' ' $plugin_name)))

    # Check if file has leader shortcuts
    if grep -q "keymap\.set.*<leader>" $file 2>/dev/null
        extract_leader_shortcuts $file "Plugin: $display_name"
    end
end

echo "💡 Tips:"
echo "--------"
echo "• Use <Space>fk to search all keymaps with Telescope"
echo "• Leader key is set to <Space> in init.lua"
echo "• Some plugins may have additional shortcuts not using leader key"
echo ""
echo "🔧 To modify shortcuts, edit files in:"
echo "   ~/.nvim/lua/config/keymaps.lua (core shortcuts)"
echo "   ~/.nvim/lua/plugins/*.lua (plugin-specific shortcuts)"
