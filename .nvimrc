" Local nvim configuration for GEEST project
" This file is automatically sourced when opening nvim in this directory

" Alias vim to nvim for this session
command! -nargs=* -complete=file Vim :edit <args>

" LSP Configuration for Python with pyright
lua << EOF
-- Only configure if LSP hasn't been configured yet
if not vim.g.geest_lsp_configured then
  vim.g.geest_lsp_configured = true

  -- Get QGIS Python path from environment (set by nix flake)
  local qgis_python_path = os.getenv("PYTHONPATH") or ""

  -- Configure pyright LSP
  require('lspconfig').pyright.setup({
    settings = {
      python = {
        pythonPath = vim.fn.exepath('python'),
        analysis = {
          extraPaths = vim.split(qgis_python_path, ':'),
          autoSearchPaths = true,
          useLibraryCodeForTypes = true,
          typeCheckingMode = "basic"
        }
      }
    },
    on_attach = function(client, bufnr)
      -- Key mappings for LSP
      local opts = { noremap=true, silent=true, buffer=bufnr }
      vim.keymap.set('n', 'gd', vim.lsp.buf.definition, opts)
      vim.keymap.set('n', 'K', vim.lsp.buf.hover, opts)
      vim.keymap.set('n', 'gi', vim.lsp.buf.implementation, opts)
      vim.keymap.set('n', '<C-k>', vim.lsp.buf.signature_help, opts)
      vim.keymap.set('n', '<space>rn', vim.lsp.buf.rename, opts)
      vim.keymap.set('n', '<space>ca', vim.lsp.buf.code_action, opts)
      vim.keymap.set('n', 'gr', vim.lsp.buf.references, opts)
      vim.keymap.set('n', '<space>f', function() vim.lsp.buf.format { async = true } end, opts)
    end,
  })

  -- Enable completion
  local capabilities = vim.lsp.protocol.make_client_capabilities()
  if pcall(require, 'cmp_nvim_lsp') then
    capabilities = require('cmp_nvim_lsp').default_capabilities(capabilities)
  end

  print("GEEST LSP configured with QGIS libraries")

  -- GitHub Copilot Configuration
  if pcall(require, 'copilot') then
    require('copilot').setup({
      suggestion = {
        enabled = true,
        auto_trigger = true,
        debounce = 75,
        keymap = {
          accept = "<M-l>",
          accept_word = false,
          accept_line = false,
          next = "<M-]>",
          prev = "<M-[>",
          dismiss = "<C-]>",
        },
      },
      filetypes = {
        python = true,
        yaml = true,
        markdown = true,
        help = false,
        gitcommit = false,
        gitrebase = false,
        hgcommit = false,
        svn = false,
        cvs = false,
        ["."] = false,
      },
      copilot_node_command = 'node',
      server_opts_overrides = {},
    })
  end

  -- Claude.nvim Configuration
  if pcall(require, 'claude') then
    require('claude').setup({
      -- API configuration
      api_key_cmd = 'echo $ANTHROPIC_API_KEY',
      model = 'claude-3-5-sonnet-20241022',
      max_tokens = 4096,

      -- UI configuration
      default_keymaps = true,
      chat = {
        split_direction = 'vertical',
        split_size = 0.4,
        show_settings_header = true,
      },

      -- Keymaps
      keymaps = {
        chat = '<leader>cc',
        reset = '<leader>cr',
        close = '<leader>cx',
      }
    })
  end
end
EOF

" Set local options for Python development
setlocal expandtab
setlocal tabstop=4
setlocal shiftwidth=4
setlocal softtabstop=4
setlocal autoindent
setlocal smartindent

" Enable syntax highlighting for Python
syntax on

" Show line numbers
set number
set relativenumber

" Highlight current line
set cursorline

" Enable mouse support
set mouse=a

" Better search
set ignorecase
set smartcase
set hlsearch
set incsearch

" Show matching brackets
set showmatch

" Status line
set laststatus=2
set statusline=%f\ %h%w%m%r\ %=%(%l,%c%V\ %=\ %P%)

echo "GEEST project nvim configuration loaded. QGIS libraries available for LSP."
