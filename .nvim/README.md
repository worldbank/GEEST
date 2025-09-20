# GEEST Project Local Neovim Configuration

This directory contains a minimal but functional Neovim configuration specifically tailored for the GEEST project development.

## Quick Start

To use this configuration with your GEEST project:

1. Make sure you have Neovim 0.8+ installed
2. From the project root directory, run:

   ```bash
   ./.nvim/nvim-geest
   ```

Or update your Fish function in `~/.config/fish/functions/nvim-geest.fish`:

```fish
function nvim-geest
    /home/timlinux/dev/python/GEEST/.nvim/nvim-geest $argv
end
```

Then you can simply run `nvim-geest` from anywhere.

## Features

### Core Features

- **Leader Key**: Space (`<leader>` = ` `)
- **Plugin Manager**: lazy.nvim (auto-installed)
- **Colorscheme**: Tokyo Night
- **Line Numbers**: Relative and absolute
- **Python-optimized**: 4-space indentation, 88-character line length

### Key Plugins

- **LSP Support**: Python LSP with Mason for automatic installation
- **Fuzzy Finding**: Telescope for file/text search
- **Syntax Highlighting**: Treesitter with Python, Lua, and more
- **File Explorer**: nvim-tree
- **Auto-completion**: nvim-cmp with LSP integration
- **Git Integration**: Gitsigns for diff visualization
- **Status Line**: Lualine with custom theme

### Key Mappings

#### General

- `<leader>w` - Save file
- `<leader>q` - Quit
- `<leader>h` - Clear search highlighting
- `<C-h/j/k/l>` - Navigate splits
- `<S-h/l>` - Previous/Next buffer

#### File Operations

- `<leader>ff` - Find files
- `<leader>fg` - Live grep
- `<leader>fb` - Browse buffers
- `<leader>fr` - Recent files

#### File Explorer

- `<leader>ee` - Toggle file explorer
- `<leader>ef` - Find current file in explorer

#### LSP

- `gd` - Go to definition
- `gr` - Show references
- `K` - Hover documentation
- `<leader>ca` - Code actions
- `<leader>rn` - Rename symbol
- `[d` / `]d` - Navigate diagnostics

#### Git

- `]h` / `[h` - Navigate git hunks
- `<leader>hs` - Stage hunk
- `<leader>hr` - Reset hunk
- `<leader>hp` - Preview hunk

## Configuration Structure

```
.nvim/
├── init.lua              # Main entry point
└── lua/
    ├── config/
    │   ├── options.lua   # Neovim options
    │   ├── keymaps.lua   # Key mappings
    │   └── autocmds.lua  # Auto commands
    └── plugins/
        ├── colorscheme.lua
        ├── telescope.lua
        ├── treesitter.lua
        ├── lsp.lua
        ├── completion.lua
        ├── nvim-tree.lua
        ├── lualine.lua
        ├── autopairs.lua
        ├── gitsigns.lua
        └── utils.lua
```

## Python Development

This configuration is optimized for Python development with:

- Python LSP server (pylsp) with black and isort integration
- 88-character line length (Black formatter standard)
- 4-space indentation
- Auto-pairs for brackets and quotes
- Treesitter syntax highlighting for Python

## Customization

To customize the configuration:

1. Edit files in `.nvim/lua/config/` for general settings
2. Edit files in `.nvim/lua/plugins/` for plugin-specific settings
3. The configuration automatically loads on startup

## Requirements

- Neovim 0.8+
- Git (for plugin management)
- A terminal with true color support
- Optional: ripgrep for better search performance
- Optional: fd for faster file finding
