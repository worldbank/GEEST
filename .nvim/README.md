# GEEST Project Local Neovim Configuration

This directory contains a comprehensive Neovim configuration specifically tailored for the GEEST project development, featuring **40+ plugins** for a complete modern development environment.

## Quick Start

To use this configuration with your GEEST project:

1. Make sure you have Neovim 0.10+ installed
2. From the project root directory, run:

   ```bash
   ./.nvim/nvim-geest
   ```

Or create a Fish function in `~/.config/fish/functions/nvim-geest.fish`:

```fish
function nvim-geest
    /home/timlinux/dev/python/GEEST/.nvim/nvim-geest $argv
end
```

Then you can simply run `nvim-geest` from anywhere.

## 🚀 Complete Feature Set

### Core Development Tools

- **LSP Integration**: Mason.nvim manages language servers automatically
  - Python (pylsp), Lua (lua_ls), Bash (bashls)
- **AI Assistance**: GitHub Copilot with interactive chat interface
- **Comprehensive Formatting**: Auto-format on save for Python, Lua, Nix, Shell
- **Advanced Linting**: Real-time linting with nvim-lint and null-ls
- **Testing Framework**: Both vim-test and neotest for comprehensive testing
- **Debugging**: Full DAP support with Python debugging capabilities
- **Git Workflow**: Triple Git integration (gitsigns + fugitive + neogit)

### Plugin Categories

#### LSP & Completion (8 plugins)

- nvim-lspconfig, mason.nvim, mason-lspconfig.nvim
- nvim-cmp, cmp-nvim-lsp, cmp-buffer, cmp-path, lspkind.nvim

#### Formatting & Linting (4 plugins)

- formatter.nvim, black.nvim, nvim-lint, none-ls.nvim

#### AI Integration (2 plugins)

- copilot.lua, copilot-chat.nvim

#### Testing (3 plugins)

- vim-test, neotest, neotest-python

#### Git Workflow (4 plugins)

- gitsigns.nvim, vim-fugitive, neogit, diffview.nvim

#### Debugging (4 plugins)

- nvim-dap, nvim-dap-ui, nvim-dap-virtual-text, nvim-dap-python

#### Project Management (2 plugins)

- project.nvim, which-key.nvim

Plus existing plugins: telescope.nvim, nvim-treesitter, lualine.nvim, tokyo-night.nvim, etc.

## 🔍 Plugin Verification

### Count All Plugins

```bash
./.nvim/nvim-geest --headless +"lua local lazy = require('lazy'); print('Total plugins loaded:', vim.tbl_count(lazy.plugins()))" +q
```

### List All Plugin Names

```bash
./.nvim/nvim-geest --headless +"lua local lazy = require('lazy'); for name, plugin in pairs(lazy.plugins()) do if plugin.name then print(plugin.name) end end" +q
```

### Check Specific Plugin

```bash
./.nvim/nvim-geest --headless +"lua local lazy = require('lazy'); for name, plugin in pairs(lazy.plugins()) do if plugin.name and plugin.name:match('copilot') then print('Found:', plugin.name) end end" +q
```

### Verify LSP Servers

```bash
./.nvim/nvim-geest --headless +"lua print('LSP servers:', vim.tbl_keys(require('lspconfig.configs')))" +q
```

### Check Configuration Loading

```bash
./.nvim/nvim-geest --headless +"lua require('lazy').setup({ import = 'plugins' }); print('Configuration loaded successfully')" +q
```

### 🔧 Initial Setup

After first launch, install LSP servers and tools via Mason:

```vim
:Mason
```

Then install commonly used tools:

- **LSP Servers**: `python-lsp-server`, `lua-language-server`, `bash-language-server`
- **Formatters**: `black`, `nixfmt`, `shfmt`, `prettier`
- **Linters**: `flake8`, `luacheck`, `shellcheck`

Or install via command line:

```vim
:MasonInstall python-lsp-server lua-language-server bash-language-server black flake8 luacheck
```

## 📋 Key Mappings

### Leader Key: Space (`<leader>` = ` `)

#### File Operations

- `<leader>ff` - Find files (Telescope)
- `<leader>fg` - Live grep search
- `<leader>fb` - Browse buffers
- `<leader>fr` - Recent files
- `<leader>fp` - Find projects

#### Code Development

- `<leader>ca` - Code actions (LSP)
- `<leader>rn` - Rename symbol (LSP)
- `<leader>bf` - Format file/selection
- `<leader>l` - Trigger linting

#### AI Assistance (Copilot)

- `<leader>cc` - Toggle Copilot Chat
- `<leader>ce` - Explain selection
- `<leader>cr` - Review code selection
- `<leader>cf` - Fix code selection
- `<leader>cd` - Document selection
- `<leader>ct` - Generate tests

#### Testing

- `<leader>tn` - Test nearest
- `<leader>tf` - Test file
- `<leader>ta` - Test suite
- `<leader>nr` - Run nearest (neotest)
- `<leader>ns` - Test summary (neotest)

#### Git Operations

- `<leader>gg` - Git status (fugitive)
- `<leader>gn` - Open Neogit interface
- `<leader>gc` - Git commit
- `<leader>gP` - Git push
- `<leader>gs` - Stage hunk
- `<leader>gr` - Reset hunk
- `<leader>gp` - Preview hunk
- `<leader>gb` - Git blame

#### Debugging

- `<leader>db` - Toggle breakpoint
- `<leader>dc` - Debug continue
- `<leader>di` - Debug step into
- `<leader>do` - Debug step over
- `<leader>du` - Toggle debug UI
- `<leader>dt` - Terminate debug session

#### Navigation

- `gd` - Go to definition
- `gr` - Show references
- `K` - Hover documentation
- `]c` / `[c` - Navigate git hunks
- `]d` / `[d` - Navigate diagnostics

## 🐍 Python Development Optimized

This configuration provides enterprise-grade Python development with:

- **Language Server**: Automatic pylsp installation via Mason
- **Formatting**: Black formatter (88-character line length) with auto-format on save
- **Linting**: Flake8, mypy integration with real-time feedback
- **Testing**: Pytest integration with both vim-test and neotest
- **Debugging**: Full Python debugging with breakpoints and variable inspection
- **Import Management**: Automatic import sorting with isort
- **Code Intelligence**: GitHub Copilot for AI-assisted development

## 🏗️ Configuration Structure

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
## 🏗️ Configuration Structure

```text
.nvim/
├── init.lua                     # Main entry point
├── nvim-geest                   # Wrapper script for easy launch
└── lua/
    ├── config/
    │   ├── options.lua         # Neovim options
    │   ├── keymaps.lua         # Key mappings
    │   └── autocmds.lua        # Auto commands
    └── plugins/
        ├── colorscheme.lua     # Tokyo Night theme
        ├── telescope.lua       # Fuzzy finder
        ├── treesitter.lua      # Syntax highlighting
        ├── lsp.lua            # Language servers + Mason
        ├── completion.lua      # Auto-completion + lspkind
        ├── formatter.lua       # Multi-language formatting
        ├── linting.lua        # Linting configuration
        ├── copilot.lua        # AI assistance
        ├── testing.lua        # Test runners
        ├── project.lua        # Project + which-key
        ├── debug.lua          # DAP debugging
        ├── gitsigns.lua       # Comprehensive Git
        ├── nvim-tree.lua      # File explorer
        ├── lualine.lua        # Status line
        ├── autopairs.lua      # Auto-pairing
        ├── dashboard.lua      # Alpha dashboard
        └── utils.lua          # Utilities
```

## 🛠️ Installation & Setup

### Prerequisites

- **Neovim 0.10+** (required for latest plugin features)
- **Git** (for plugin management)
- **Python 3.8+** with pip
- **Node.js** (for Copilot functionality)
- **Ripgrep** (optional, for faster search)
- **fd** (optional, for faster file finding)

### First Launch

1. All plugins install automatically on first launch
2. LSP servers install automatically via Mason
3. Configuration loads without any manual setup
4. GitHub Copilot requires `:Copilot auth` on first use

### Language Server Installation

Mason automatically installs these LSP servers:

- **pylsp** (Python Language Server)
- **lua_ls** (Lua Language Server)
- **bashls** (Bash Language Server)

Manual installation via Mason UI:

```bash
./.nvim/nvim-geest
# Then in Neovim: :Mason
```

## 🧪 Testing the Configuration

### Basic Functionality Test

```bash
# Test configuration loading
./.nvim/nvim-geest --version

# Test plugin loading (should show 40+ plugins)
./.nvim/nvim-geest --headless +"lua local lazy = require('lazy'); print('Total plugins loaded:', vim.tbl_count(lazy.plugins()))" +q
```

### Python Development Test

```bash
# Test Python LSP and formatting
./.nvim/nvim-geest test_format.py
# In Neovim: Try <leader>bf to format, gd to go to definition
```

### Git Integration Test

```bash
# Test Git integration
./.nvim/nvim-geest
# In Neovim: Try <leader>gg for Git status, <leader>gn for Neogit
```

## 📚 Learning Resources

### Key Concepts

- **LSP**: Language Server Protocol provides code intelligence
- **DAP**: Debug Adapter Protocol enables debugging capabilities
- **Treesitter**: Provides advanced syntax highlighting
- **Lazy Loading**: Plugins load only when needed for faster startup

### Getting Help

- `:help <plugin-name>` - Plugin documentation
- `<leader>` then wait - Which-key shows available bindings
- `:Mason` - Manage language servers and tools
- `:Lazy` - Plugin management interface
- `:checkhealth` - Diagnose configuration issues

## 🐛 Troubleshooting

### Common Issues

**Plugins not loading:**

```bash
# Check plugin count
./.nvim/nvim-geest --headless +"lua print('Plugins:', vim.tbl_count(require('lazy').plugins()))" +q
```

**LSP not working:**

```bash
# Check LSP servers
./.nvim/nvim-geest --headless +"lua print('LSP servers available')" +q
# In Neovim: :LspInfo
```

**Copilot not working:**

```bash
# In Neovim: :Copilot auth
```

**Formatting not working:**

```bash
# Check formatters
# In Neovim: :Mason (look for black, nixfmt, shfmt)
```

### Debug Mode

```bash
# Start with verbose logging
./.nvim/nvim-geest --cmd 'set verbose=9'
```

## 🎯 Usage Examples

### Python Development Workflow

1. Open project: `./.nvim/nvim-geest`
2. Find files: `<leader>ff`
3. Code with LSP: Auto-completion, go to definition (`gd`)
4. Format code: `<leader>bf` (auto-formats with black)
5. Run tests: `<leader>tn` (test nearest function)
6. Debug code: `<leader>db` (toggle breakpoint), `<leader>dc` (debug)
7. Git workflow: `<leader>gg` (status), `<leader>gn` (Neogit UI)
8. AI assistance: `<leader>cc` (Copilot chat)

### Multi-Language Support

- **Python**: Full LSP + formatting + testing + debugging
- **Lua**: LSP + formatting for Neovim configuration
- **Shell**: LSP + formatting + linting for scripts
- **Nix**: Formatting for Nix expressions
- **Markdown**: Formatting + linting for documentation

## 🔗 Related Files

- `PLUGIN-SUMMARY.md` - Complete plugin listing with descriptions
- Individual plugin configs in `lua/plugins/` directory
- Keybinding reference via which-key (`<leader>` then wait)

---

This configuration represents a complete, modern development environment comparable to VS Code or JetBrains IDEs, but with the efficiency and customizability of Neovim.
