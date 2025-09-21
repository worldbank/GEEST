-- Testing Framework Configuration
return {
    {
        "vim-test/vim-test",
        keys = {
            { "<leader>tr", ":TestNearest<CR>", desc = "Test nearest" },
            { "<leader>tf", ":TestFile<CR>", desc = "Test file" },
            { "<leader>ta", ":TestSuite<CR>", desc = "Test suite" },
            { "<leader>tl", ":TestLast<CR>", desc = "Test last" },
            { "<leader>tv", ":TestVisit<CR>", desc = "Test visit" },
        },
        config = function()
            -- Configure test strategies
            vim.g["test#strategy"] = "neovim"
            vim.g["test#neovim#term_position"] = "horizontal"
            vim.g["test#neovim#preserve_screen"] = 1

            -- Python test configuration
            vim.g["test#python#runner"] = "pytest"
            vim.g["test#python#pytest#options"] = "-v"

            -- Custom test mappings
            vim.keymap.set('n', '<leader>tr', ':TestNearest<CR>', { desc = 'Test nearest' })
            vim.keymap.set('n', '<leader>tt', ':TestFile<CR>', { desc = 'Test current file' })
            vim.keymap.set('n', '<leader>ts', ':TestSuite<CR>', { desc = 'Test suite' })
            vim.keymap.set('n', '<leader>tg', ':TestVisit<CR>', { desc = 'Go to test file' })
        end,
    },
    {
        "nvim-neotest/neotest",
        dependencies = {
            "nvim-neotest/nvim-nio",
            "nvim-lua/plenary.nvim",
            "antoinemadec/FixCursorHold.nvim",
            "nvim-treesitter/nvim-treesitter",
            "nvim-neotest/neotest-python",
            "nvim-neotest/neotest-plenary",
        },
        keys = {
            { "<leader>nr", function() require("neotest").run.run() end, desc = "Run nearest test" },
            { "<leader>nf", function() require("neotest").run.run(vim.fn.expand("%")) end, desc = "Run current file" },
            { "<leader>nd", function() require("neotest").run.run({strategy = "dap"}) end, desc = "Debug nearest test" },
            { "<leader>ns", function() require("neotest").run.stop() end, desc = "Stop test" },
            { "<leader>no", function() require("neotest").output.open({ enter = true, auto_close = true }) end, desc = "Show test output" },
            { "<leader>nO", function() require("neotest").output_panel.toggle() end, desc = "Toggle output panel" },
            { "<leader>nS", function() require("neotest").summary.toggle() end, desc = "Toggle summary" },
        },
        config = function()
            require("neotest").setup({
                adapters = {
                    require("neotest-python")({
                        dap = { justMyCode = false },
                        args = {"--log-level", "DEBUG"},
                        runner = "pytest",
                    }),
                    require("neotest-plenary"),
                },
                discovery = {
                    enabled = true,
                    concurrent = 1,
                },
                running = {
                    concurrent = true,
                },
                summary = {
                    enabled = true,
                    animated = true,
                    follow = true,
                    expand_errors = true,
                },
                output = {
                    enabled = true,
                    open_on_run = "short",
                },
                output_panel = {
                    enabled = true,
                    open = "botright split | resize 15",
                },
                quickfix = {
                    enabled = false,
                },
                status = {
                    enabled = true,
                    signs = true,
                    virtual_text = true,
                },
                icons = {
                    child_indent = "│",
                    child_prefix = "├",
                    collapsed = "─",
                    expanded = "╮",
                    failed = "✖",
                    final_child_indent = " ",
                    final_child_prefix = "╰",
                    non_collapsible = "─",
                    passed = "✔",
                    running = "🗘",
                    running_animated = { "/", "|", "\\", "-", "/", "|", "\\", "-" },
                    skipped = "○",
                    unknown = "?",
                },
            })
        end,
    },
}
