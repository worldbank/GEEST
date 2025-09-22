-- Project Management and Key Discovery
return {
    {
        -- Session Management
        "rmagatti/auto-session",
        config = function()
            require("auto-session").setup({
                log_level = "error",
                auto_session_suppress_dirs = { "~/", "~/Projects", "~/Downloads", "/"},
                auto_session_use_git_branch = false,

                -- Auto save session
                auto_save_enabled = true,
                auto_restore_enabled = true,

                -- Session lens for browsing sessions
                session_lens = {
                    buftypes_to_ignore = {}, -- list of buffer types what should not be deleted from current session
                    load_on_setup = true,
                    theme_conf = { border = true },
                    previewer = false,
                },
            })

            -- Key mappings for session management
            vim.keymap.set("n", "<leader>wr", "<cmd>SessionRestore<CR>", { desc = "Restore session for cwd" })
            vim.keymap.set("n", "<leader>ws", "<cmd>SessionSave<CR>", { desc = "Save session for auto session root dir" })
            vim.keymap.set("n", "<leader>wS", "<cmd>SessionSearch<CR>", { desc = "Search sessions" })
            vim.keymap.set("n", "<leader>wd", "<cmd>SessionDelete<CR>", { desc = "Delete session for cwd" })
        end,
    },
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
                        motions = false, -- Disable to reduce conflicts
                        text_objects = true,
                        windows = true,
                        nav = true,
                        z = true,
                        g = false, -- Disable g preset to avoid conflicts
                    },
                },
                show_help = true,
                show_keys = true,
                -- Use new win instead of window
                win = {
                    border = "rounded",
                    padding = { 2, 2, 2, 2 },
                },
                layout = {
                    height = { min = 4, max = 25 },
                    width = { min = 20, max = 50 },
                    spacing = 3,
                    align = "left",
                },
            })

            -- Register key groups using new spec format
            wk.add({
                { "<leader>c", group = "Code/Copilot" },
                { "<leader>f", group = "File/Find" },
                { "<leader>g", group = "Git" },
                { "<leader>l", group = "LSP/Location List" },
                { "<leader>n", group = "Neotest" },
                { "<leader>t", group = "Test" },
                { "<leader>w", group = "Workspace" },
                { "<leader>b", group = "Buffer/Format" },
                { "<leader>d", group = "Debug/Diagnostics" },
                { "<leader>da", desc = "Attach to remote debugger" },
                { "<leader>db", desc = "Toggle breakpoint" },
                { "<leader>dB", desc = "Conditional breakpoint" },
                { "<leader>dc", desc = "Continue" },
                { "<leader>dC", desc = "Run to cursor" },
                { "<leader>dx", desc = "Remove all breakpoints" },
                { "<leader>dX", desc = "Remove current breakpoint" },
                { "<leader>du", desc = "Toggle DAP UI" },
                { "<leader>de", desc = "Evaluate expression" },
                { "<leader>s", group = "Search/Split" },
                { "<leader>x", group = "Trouble" },
                { "<leader>e", group = "Explorer" },
                { "<leader>h", group = "Git Hunks" },
                { "<leader>r", group = "Rename/Replace" },
            })
        end,
    },
}
