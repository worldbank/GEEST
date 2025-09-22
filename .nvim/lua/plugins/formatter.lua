-- Comprehensive Formatter Configuration
return {
    {
        -- Formatter plugin
        "mhartington/formatter.nvim",
        event = "VeryLazy", -- Load after startup instead of lazy-loading on command
        config = function()
            local formatter = require("formatter")

            formatter.setup({
                logging = true,
                log_level = vim.log.levels.WARN,
                filetype = {
                    python = {
                        require("formatter.filetypes.python").black,
                    },
                    lua = {
                        require("formatter.filetypes.lua").stylua,
                    },
                    nix = {
                        function()
                            return {
                                exe = "nixfmt",
                                args = {},
                                stdin = true,
                            }
                        end,
                    },
                    sh = {
                        function()
                            return {
                                exe = "shfmt",
                                args = { "-i", "2", "-ci" },
                                stdin = true,
                            }
                        end,
                    },
                    bash = {
                        function()
                            return {
                                exe = "shfmt",
                                args = { "-i", "2", "-ci" },
                                stdin = true,
                            }
                        end,
                    },
                    json = {
                        function()
                            return {
                                exe = "jq",
                                args = { "--indent", "2", "." },
                                stdin = true,
                            }
                        end,
                    },
                },
            })

                        -- Auto format on save
            local augroup = vim.api.nvim_create_augroup("FormatAutogroup", { clear = true })
            vim.api.nvim_create_autocmd("BufWritePre", {
                group = augroup,
                pattern = { "*.py", "*.lua", "*.nix", "*.sh", "*.json" },
                callback = function()
                    vim.cmd("Format")
                end,
            })

            -- Key mappings
            vim.keymap.set('n', '<leader>bf', ':Format<CR>', { desc = 'Format file' })
            vim.keymap.set('v', '<leader>bf', ':Format<CR>', { desc = 'Format selection' })
        end,
    },
    {
        -- Keep black.nvim as backup for advanced Python formatting
        "psf/black",
        ft = "python",
        cmd = { "Black", "BlackMacchiato" },
        config = function()
            vim.g.black_fast = 0
            vim.g.black_linelength = 88
            vim.g.black_skip_string_normalization = 0

            -- Key mappings for black-specific commands
            vim.keymap.set('n', '<leader>bb', ':Black<CR>', { desc = 'Format with Black' })
            vim.keymap.set('v', '<leader>bb', ':BlackMacchiato<CR>', { desc = 'Format selection with Black' })
        end,
    },
}
