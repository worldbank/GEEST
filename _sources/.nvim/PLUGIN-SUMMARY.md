# GEEST Neovim Configuration - Complete Plugin List

This comprehensive Neovim configuration includes all requested plugins and more for a complete development environment.

## Core LSP & Completion

### Language Server Protocol (LSP)

- **nvim-lspconfig** - LSP configuration for Neovim
- **mason.nvim** - Manage external editor tooling (LSP servers, DAP adapters, linters, formatters)
- **mason-lspconfig.nvim** - Integration between mason.nvim and nvim-lspconfig

### Autocompletion

- **nvim-cmp** - Completion engine
- **cmp-nvim-lsp** - LSP source for nvim-cmp
- **cmp-buffer** - Buffer words source
- **cmp-path** - File paths source
- **LuaSnip** - Snippet engine
- **lspkind.nvim** - VS Code-like pictograms for completion

## Formatting & Linting

### Formatters

- **formatter.nvim** - Multi-language formatter with support for:
  - **black** (Python)
  - **nixfmt** (Nix)
  - **shfmt** (Shell scripts)
  - **stylua** (Lua)
- **black.nvim** - Backup Python formatter

### Linting

- **nvim-lint** - Asynchronous linting engine
- **none-ls.nvim** (formerly null-ls) - Language server for various tools

## AI & Copilot Integration

- **copilot.lua** - GitHub Copilot integration
- **copilot-chat.nvim** - Interactive chat with Copilot

## Testing Framework

- **vim-test** - Test runner integration
- **neotest** - Modern test runner with:
  - **neotest-python** - Python test adapter
  - **neotest-plenary** - Plenary test adapter

## Navigation & Search

- **telescope.nvim** - Fuzzy finder and picker
- **project.nvim** - Project management
- **nvim-tree.lua** - File explorer (existing)

## Git Integration

- **gitsigns.nvim** - Git signs in the gutter
- **vim-fugitive** - Comprehensive Git integration
- **neogit** - Magit-like Git interface
- **diffview.nvim** - Advanced diff viewing

## Debugging

- **nvim-dap** - Debug Adapter Protocol client
- **nvim-dap-ui** - UI for nvim-dap
- **nvim-dap-virtual-text** - Virtual text support for debugging
- **nvim-dap-python** - Python debugging support

## UI & UX Enhancements

- **which-key.nvim** - Key binding helper
- **lualine.nvim** - Status line (existing)
- **alpha-nvim** - Dashboard (existing)
- **tokyo-night.nvim** - Colorscheme (existing)

## Syntax & Highlighting

- **nvim-treesitter** - Syntax highlighting (existing)

## Additional Utilities

- **plenary.nvim** - Lua utility functions (dependency)
- **nvim-nio** - Async I/O library (dependency)
- **nvim-autopairs** - Auto-pairing brackets (existing)
- **Comment.nvim** - Commenting (existing)

## Total Count

This configuration includes **40+ plugins** providing a comprehensive development environment with:

### Key Bindings Summary

- `<leader>` = Space
- `<leader>ff` - Find files
- `<leader>fg` - Live grep
- `<leader>fb` - Find buffers
- `<leader>fp` - Find projects
- `<leader>cc` - Toggle Copilot Chat
- `<leader>gg` - Git status
- `<leader>gn` - Open Neogit
- `<leader>db` - Toggle breakpoint
- `<leader>dc` - Debug continue
- `<leader>tn` - Test nearest
- `<leader>tf` - Test file
- `<leader>bf` - Format file
- `<leader>l` - Trigger linting

### Language Support

- **Python**: Full LSP, formatting (black), linting (flake8, mypy), testing (pytest), debugging
- **Lua**: LSP, formatting (stylua), linting (luacheck)
- **Bash/Shell**: LSP, formatting (shfmt), linting (shellcheck)
- **Nix**: Formatting (nixfmt)
- **Markdown**: Formatting (prettier), linting (markdownlint)
- **YAML/JSON**: Formatting and linting support

## Usage

Start Neovim with the GEEST configuration:

```bash
cd /path/to/GEEST
./.nvim/nvim-geest
```

All plugins will be automatically installed on first launch. The configuration provides a complete, modern development environment suitable for Python development and general programming tasks.
