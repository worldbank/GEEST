-- Project Management and Key Discovery
return {
    {
        "ahmedkhalf/project.nvim",
        config = function()
            require("project_nvim").setup({
                -- Manual mode doesn't automatically change your root directory, so you have
                -- the option to manually do so using `:ProjectRoot` command.
                manual_mode = false,

                -- Methods of detecting the root directory. **"lsp"** uses the native neovim
                -- lsp, while **"pattern"** uses vim-rooter like glob pattern matching. Here
                -- order matters: if one is not detected, the other is used as fallback. You
                -- can also delete or rearangge the detection methods.
                detection_methods = { "lsp", "pattern" },

                -- All the patterns used to detect root dir, when **"pattern"** is in
                -- detection_methods
                patterns = { ".git", "_darcs", ".hg", ".bzr", ".svn", "Makefile", "package.json", "pyproject.toml", "setup.py" },

                -- Table of lsp clients to ignore by name
                ignore_lsp = {},

                -- Don't calculate root dir on specific directories
                exclude_dirs = {},

                -- Show hidden files in telescope
                show_hidden = false,

                -- When set to false, you will get a message when project.nvim changes your
                -- directory.
                silent_chdir = true,

                -- What scope to change the directory, valid options are
                -- * global (default)
                -- * tab
                -- * win
                scope_chdir = 'global',

                -- Path where project.nvim will store the project history for use in
                -- telescope
                datapath = vim.fn.stdpath("data"),
            })

            -- Key mappings
            vim.keymap.set('n', '<leader>fp', ':Telescope projects<CR>', { desc = 'Find projects' })
        end,
    },
    {
        "folke/which-key.nvim",
        event = "VeryLazy",
        init = function()
            vim.o.timeout = true
            vim.o.timeoutlen = 300
        end,
        config = function()
            local wk = require("which-key")

            wk.setup({
                plugins = {
                    marks = true,
                    registers = true,
                    spelling = {
                        enabled = true,
                        suggestions = 20,
                    },
                    presets = {
                        operators = false,
                        motions = true,
                        text_objects = true,
                        windows = true,
                        nav = true,
                        z = true,
                        g = true,
                    },
                },
                operators = { gc = "Comments" },
                key_labels = {},
                icons = {
                    breadcrumb = "»",
                    separator = "➜",
                    group = "+",
                },
                popup_mappings = {
                    scroll_down = "<c-d>",
                    scroll_up = "<c-u>",
                },
                window = {
                    border = "rounded",
                    position = "bottom",
                    margin = { 1, 0, 1, 0 },
                    padding = { 2, 2, 2, 2 },
                    winblend = 0,
                },
                layout = {
                    height = { min = 4, max = 25 },
                    width = { min = 20, max = 50 },
                    spacing = 3,
                    align = "left",
                },
                ignore_missing = true,
                hidden = { "<silent>", "<cmd>", "<Cmd>", "<CR>", "call", "lua", "^:", "^ " },
                show_help = true,
                show_keys = true,
                triggers = "auto",
                triggers_blacklist = {
                    i = { "j", "k" },
                    v = { "j", "k" },
                },
            })

            -- Register key groups
            wk.register({
                ["<leader>c"] = { name = "+code/copilot" },
                ["<leader>f"] = { name = "+file/find" },
                ["<leader>g"] = { name = "+git" },
                ["<leader>l"] = { name = "+lsp" },
                ["<leader>n"] = { name = "+neotest" },
                ["<leader>t"] = { name = "+test" },
                ["<leader>w"] = { name = "+workspace" },
                ["<leader>b"] = { name = "+buffer/format" },
                ["<leader>d"] = { name = "+debug/diagnostics" },
                ["<leader>s"] = { name = "+search" },
                ["<leader>x"] = { name = "+trouble" },
            })
        end,
    },
}
