{
  config,
  pkgs,
  lib,
  ...
}:

let
  # Python runtime with debugpy for nvim-dap
  py = pkgs.python3.withPackages (ps: [
    ps.debugpy
    ps.pip
  ]);

  # Colour palette (Kartoza base + a few sat/desat variants)
  kartoza = {
    base0 = "#FDFFFC"; # paper
    base1 = "#898B89"; # graphite
    base2 = "#54A1C9"; # sky
    accent = "#E29F34"; # saffron
    # simple variants
    base1_desat = "#7e807e";
    base1_over = "#9fa19f";
    sky_desat = "#4c91b3";
    sky_over = "#63b7e3";
    saff_desat = "#cc8f2f";
    saff_over = "#ffb247";
    black = "#0b0d0c";
  };
in
{
  home.packages = with pkgs; [
    py # debugpy for Python DAP
    black # Python fmt
    nixfmt-rfc-style # Nix fmt (or nixfmt-classic if you prefer)
    shfmt # Shell fmt
    ripgrep
    fd # Telescope speed
    sqlite # neoclip persistence
    gh # GitHub CLI
    gitAndTools.gitFull # git, diffs, mergetool, etc.
    imagemagick
    libvips # image.nvim backends
    nodejs_20 # Copilot + TS servers runtime
    (python3.withPackages (ps: [
      ps.pyqt5
      ps.pyqt6
    ])) # QT for completions
  ];

  programs.neovim = {
    enable = true;
    defaultEditor = true;

    # Install plugins from nixpkgs where possible (no runtime curl/npm nonsense).
    plugins = with pkgs.vimPlugins; [
      # Core UX
      plenary-nvim
      nvim-web-devicons
      nui-nvim
      telescope-nvim
      telescope-fzf-native-nvim
      # File tree + images
      neo-tree-nvim
      nvim-window-picker
      image-nvim
      # Treesitter
      (nvim-treesitter.withPlugins (
        p: with p; [
          bash
          python
          lua
          nix
          json
          yaml
          toml
          html
          css
          markdown
          vim
          regex
          query
        ]
      ))
      # LSP + Completion
      nvim-lspconfig
      nvim-cmp
      cmp-nvim-lsp
      cmp-buffer
      cmp-path
      cmp_luasnip
      luasnip
      friendly-snippets
      # Formatting
      conform-nvim
      # Statusline (powerline glyphs)
      lualine-nvim
      # Spell helpers
      dressing-nvim
      # Git
      gitsigns-nvim
      vim-fugitive
      diffview-nvim
      octo-nvim # PRs/issues from inside nvim
      telescope-github-nvim # gh telescope extension
      # Copilot + Chat
      copilot-lua
      CopilotChat-nvim
      # DAP (debugging)
      nvim-dap
      nvim-dap-ui
      nvim-dap-python
      # Clipboard history
      nvim-neoclip-lua
      # Image render helper for kitty
      # (image.nvim uses kitty protocol automatically in Kitty)
      # Fun
      nvimesweeper
      cellular-automaton-nvim
    ];

    # System LSP servers from Nix (no mason)
    extraPackages = with pkgs; [
      pyright # Python (works well for Django too)
      bash-language-server
      nixd # modern Nix LSP (or nil if you prefer)
      vscode-langservers-extracted # jsonls, html, cssls
      yaml-language-server
    ];

    extraLuaConfig =
      let
        c = kartoza; # alias
      in
      ''
        -- ──────────────────────────────────────────────────────────────────────
        -- Options
        -- ──────────────────────────────────────────────────────────────────────
        vim.opt.termguicolors = true
        vim.opt.number = true
        vim.opt.relativenumber = true
        vim.opt.signcolumn = "yes"
        vim.opt.expandtab = true        -- spaces, not tabs
        vim.opt.shiftwidth = 2
        vim.opt.tabstop = 2
        vim.opt.smartindent = true
        vim.opt.clipboard = "unnamedplus"
        vim.opt.updatetime = 400
        vim.opt.timeoutlen = 500
        vim.opt.spell = true
        vim.opt.spelllang = { "en_gb" }

        -- Persistent clipboard history
        require("neoclip").setup({
          history = 1000,
          enable_persistent_history = true,
          continuous_sync = true,
          default_register = { '"', "+", "*" },
          db_path = vim.fn.stdpath("data") .. "/neoclip.sqlite3",
        })

        -- ──────────────────────────────────────────────────────────────────────
        -- Kartoza Colourscheme (minimal, pragmatic)
        -- ──────────────────────────────────────────────────────────────────────
        local palette = {
          base0 = "${c.base0}",
          base1 = "${c.base1}",
          base2 = "${c.base2}",
          accent= "${c.accent}",
          black = "${c.black}",
          sky_d = "${c.sky_desat}",
          sky_o = "${c.sky_over}",
          saff_d= "${c.saff_desat}",
          saff_o= "${c.saff_over}",
        }
        vim.cmd("highlight clear")
        vim.g.colors_name = "kartoza"
        local function hi(grp, opts)
          local cmd = "hi " .. grp
          if opts.fg then cmd = cmd .. " guifg=" .. opts.fg end
          if opts.bg then cmd = cmd .. " guibg=" .. opts.bg end
          if opts.gui then cmd = cmd .. " gui=" .. opts.gui end
          vim.cmd(cmd)
        end
        -- UI bases
        hi("Normal",       { fg = palette.black,  bg = palette.base0 })
        hi("NormalFloat",  { fg = palette.black,  bg = palette.base0 })
        hi("LineNr",       { fg = palette.base1 })
        hi("CursorLine",   { bg = palette.base0 })
        hi("CursorLineNr", { fg = palette.accent, gui = "bold" })
        hi("VertSplit",    { fg = palette.base1 })
        hi("Visual",       { bg = palette.sky_d })
        hi("Search",       { bg = palette.saff_o, fg = palette.black })
        hi("IncSearch",    { bg = palette.sky_o,  fg = palette.black })
        hi("StatusLine",   { bg = palette.base1,  fg = palette.base0 })
        hi("Pmenu",        { bg = palette.base1,  fg = palette.base0 })
        hi("PmenuSel",     { bg = palette.accent, fg = palette.black })
        hi("GitSignsAdd",    { fg = "#2aa198" })
        hi("GitSignsChange", { fg = palette.base2 })
        hi("GitSignsDelete", { fg = "#dc322f" })
        -- Syntax accents
        hi("Identifier",   { fg = palette.base2 })
        hi("Statement",    { fg = palette.accent, gui = "bold" })
        hi("Type",         { fg = palette.sky_d })
        hi("String",       { fg = palette.saff_d })
        hi("Comment",      { fg = palette.base1, gui = "italic" })

        -- lualine with Nerd Font separators
        require("lualine").setup({
          options = {
            theme = {
              normal   = { c = { fg = palette.black, bg = palette.base0 } },
              insert   = { c = { fg = palette.black, bg = palette.sky_o } },
              visual   = { c = { fg = palette.black, bg = palette.saff_o } },
              replace  = { c = { fg = palette.black, bg = palette.sky_d } },
              inactive = { c = { fg = palette.base1, bg = palette.base0 } },
            },
            section_separators = { left = "", right = "" },
            component_separators = { left = "", right = "" },
            icons_enabled = true,
            globalstatus = true,
          },
        })

        -- ──────────────────────────────────────────────────────────────────────
        -- Telescope (files, grep, GH, clipboard history)
        -- ──────────────────────────────────────────────────────────────────────
        local telescope = require("telescope")
        telescope.setup({})
        telescope.load_extension("fzf")
        telescope.load_extension("gh")
        telescope.load_extension("neoclip")

        -- ──────────────────────────────────────────────────────────────────────
        -- File manager: Neo-tree (+ image.nvim + Kitty inline images)
        -- ──────────────────────────────────────────────────────────────────────
        require("neo-tree").setup({
          close_if_last_window = true,
          window = { position = "left", width = 32 },
          filesystem = {
            follow_current_file = true,
            filtered_items = { hide_dotfiles = false, hide_gitignored = true },
            components = {
              -- image preview on hover (open in a floating buffer via image.nvim)
            },
          },
        })
        vim.keymap.set("n", "<leader>e", "<cmd>Neotree toggle<cr>", { desc = "File tree" })

        -- Inline images in Kitty
        require("image").setup({
          backend = "kitty",
          integrations = { markdown = { enabled = true }, neorg = { enabled = true } },
          editor_only_render_when_focused = true,
        })

        -- ──────────────────────────────────────────────────────────────────────
        -- Completion (nvim-cmp) + LSP
        -- ──────────────────────────────────────────────────────────────────────
        local cmp = require("cmp")
        local luasnip = require("luasnip")
        require("luasnip.loaders.from_vscode").lazy_load()
        cmp.setup({
          snippet = { expand = function(args) luasnip.lsp_expand(args.body) end },
          mapping = cmp.mapping.preset.insert({
            ["<C-Space>"] = cmp.mapping.complete(),
            ["<CR>"] = cmp.mapping.confirm({ select = true }),
            ["<Tab>"] = cmp.mapping.select_next_item(),
            ["<S-Tab>"] = cmp.mapping.select_prev_item(),
          }),
          sources = {
            { name = "nvim_lsp" },
            { name = "buffer" },
            { name = "path" },
            { name = "luasnip" },
          },
        })

        local lsp = require("lspconfig")
        local caps = require("cmp_nvim_lsp").default_capabilities()

        -- Python (PyQt5/PyQt6/PyQGIS/Django friendly)
        lsp.pyright.setup({
          capabilities = caps,
          settings = {
            python = {
              analysis = {
                typeCheckingMode = "basic",
                autoImportCompletions = true,
                extraPaths = { "src", "python" },
              },
            },
          },
        })

        -- Bash
        lsp.bashls.setup({ capabilities = caps })

        -- Nix
        lsp.nixd.setup({
          capabilities = caps,
          settings = { nixd = { formatting = { command = { "nixfmt" } } } },
        })

        -- Web bits (json, yaml, html, css)
        lsp.jsonls.setup({ capabilities = caps })
        lsp.yamlls.setup({ capabilities = caps })
        lsp.html.setup({ capabilities = caps })
        lsp.cssls.setup({ capabilities = caps })

        -- ──────────────────────────────────────────────────────────────────────
        -- Formatting (Conform): Black, nixfmt, shfmt
        -- ──────────────────────────────────────────────────────────────────────
        require("conform").setup({
          formatters_by_ft = {
            python = { "black" },
            nix = { "nixfmt" },
            sh = { "shfmt" },
            bash = { "shfmt" },
          },
          format_on_save = function(bufnr)
            local ft = vim.bo[bufnr].filetype
            if ft == "python" or ft == "nix" or ft == "sh" or ft == "bash" then
              return { timeout_ms = 3000, lsp_fallback = true }
            end
          end,
        })

        -- ──────────────────────────────────────────────────────────────────────
        -- Git UX: signs, PRs, diff/merge
        -- ──────────────────────────────────────────────────────────────────────
        require("gitsigns").setup()
        require("diffview").setup({})
        require("octo").setup()
        vim.keymap.set("n", "<leader>gg", "<cmd>Git<cr>", { desc = "Fugitive (Git)" })
        vim.keymap.set("n", "<leader>gd", "<cmd>DiffviewOpen<cr>", { desc = "Diffview" })
        vim.keymap.set("n", "<leader>gD", "<cmd>DiffviewClose<cr>", { desc = "Diffview close" })
        vim.keymap.set("n", "<leader>gpr", "<cmd>Octo pr list<cr>", { desc = "List PRs" })
        vim.keymap.set("n", "<leader>gpc", "<cmd>Octo pr create<cr>", { desc = "Create PR" })

        -- Telescope helpers
        vim.keymap.set("n", "<leader>ff", "<cmd>Telescope find_files<cr>", { desc="Find files" })
        vim.keymap.set("n", "<leader>fg", "<cmd>Telescope live_grep<cr>", { desc="Grep" })
        vim.keymap.set("n", "<leader>fb", "<cmd>Telescope buffers<cr>", { desc="Buffers" })
        vim.keymap.set("n", "<leader>fy", "<cmd>Telescope neoclip<cr>", { desc="Clipboard history" })
        vim.keymap.set("n", "<leader>gh", "<cmd>Telescope gh issues<cr>", { desc="GH issues" })

        -- ──────────────────────────────────────────────────────────────────────
        -- GitHub Copilot + Copilot Chat with presets
        -- ──────────────────────────────────────────────────────────────────────
        require("copilot").setup({ suggestion = { enabled = true }, panel = { enabled = false } })
        local chat = require("CopilotChat")
        chat.setup({
          prompts = {
            review = { prompt = "Review the selected code and point out issues, style, and bugs." },
            feature = { prompt = "Implement the requested feature in the selected code, with tests if reasonable." },
            refactor = { prompt = "Refactor the selected code: improve readability and reduce complexity without changing behavior." },
          },
        })
        vim.keymap.set("v", "<leader>cr", function() chat.ask("review") end,   { desc="CopilotChat: Review" })
        vim.keymap.set("v", "<leader>cf", function() chat.ask("feature") end,  { desc="CopilotChat: Feature" })
        vim.keymap.set("v", "<leader>cx", function() chat.ask("refactor") end, { desc="CopilotChat: Refactor" })
        vim.keymap.set("n", "<leader>cc", function() chat.toggle() end,        { desc="CopilotChat toggle" })

        -- ──────────────────────────────────────────────────────────────────────
        -- Debugging (nvim-dap) — Python (debugpy uses pydevd under the hood)
        -- ──────────────────────────────────────────────────────────────────────
        local dap = require("dap")
        local dapui = require("dapui")
        dapui.setup()
        require("dap-python").setup("${py}/bin/python")
        vim.keymap.set("n", "<F5>", dap.continue, { desc = "DAP Continue" })
        vim.keymap.set("n", "<F10>", dap.step_over, { desc = "DAP Step Over" })
        vim.keymap.set("n", "<F11>", dap.step_into, { desc = "DAP Step Into" })
        vim.keymap.set("n", "<F12>", dap.step_out, { desc = "DAP Step Out" })
        vim.keymap.set("n", "<leader>db", dap.toggle_breakpoint, { desc = "DAP Breakpoint" })
        vim.keymap.set("n", "<leader>du", dapui.toggle, { desc = "DAP UI" })

        -- ──────────────────────────────────────────────────────────────────────
        -- Fun: Minesweeper + Cellular Automata
        -- ──────────────────────────────────────────────────────────────────────
        vim.keymap.set("n", "<leader>ms", "<cmd>Nvimesweeper<cr>", { desc = "Minesweeper" })
        vim.keymap.set("n", "<leader>zz", function()
          require("cellular-automaton").start_animation("make_it_rain")
        end, { desc = "Make it rain" })

        -- Leader
        vim.g.mapleader = " "
      '';
  };

  # A neat README dropped into your config dir
  home.file.".config/nvim/README.md".text = ''
    # Tim’s Neovim
    A practical, declarative Nix setup with:
    - LSP + completion for **Python (PyQt5/6, Django), Nix (nixd), Bash**.
    - On-save formatting: **Black**, **nixfmt**, **shfmt**.
    - **UK English** spell-check.
    - **GitHub Copilot** + **Copilot Chat** (presets: review / feature / refactor).
    - **Kartoza** colourscheme.
    - Powerline statusline with Nerd Font glyphs (use a Nerd Font in Kitty).
    - **DAP** debugging for Python (debugpy).
    - **Persistent clipboard** history across sessions (Telescope → `<leader>fy`).
    - Toggleable file manager: **Neo-tree** (`<leader>e`).
    - **Inline images** in Kitty via `image.nvim`.
    - **Great Git**: Fugitive, Gitsigns, Diffview, **Octo** (PRs/issues).
    - **Fun**: Minesweeper (`<leader>ms`), Cellular Automata rain (`<leader>zz`).

    ## Key shortcuts
    - Leader is **Space**.
    - File tree: `<leader>e`
    - Files/Grep/Buffers: `<leader>ff`, `<leader>fg`, `<leader>fb`
    - Clipboard history: `<leader>fy`
    - Git: Fugitive `<leader>gg`, Diffview `<leader>gd` / close `<leader>gD`
    - PRs/Issues (Octo): `<leader>gpr` (list), `<leader>gpc` (create)
    - Copilot Chat (visual select code first):
      - Review: `<leader>cr`
      - Implement feature: `<leader>cf`
      - Refactor: `<leader>cx`
      - Toggle chat: `<leader>cc`
    - Debug (Python): `F5/F10/F11/F12`, toggle UI: `<leader>du`, set BP: `<leader>db`
    - Minesweeper: `<leader>ms`, Rain: `<leader>zz`

    ## Notes
    - Ensure your terminal uses a **Nerd Font** for glyphs.
    - Kitty ≥ 0.28 recommended for inline images.
    - `gh auth login` once to enable Octo/Telescope-gh.
    - For PyQGIS projects, point **Pyright** to your env/site-packages if needed via
      `python.analysis.extraPaths` in a local `pyrightconfig.json`.
  '';
}
