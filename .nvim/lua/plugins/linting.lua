-- Linting Configuration with nvim-lint and null-ls
return {
    {
        "mfussenegger/nvim-lint",
        event = { "BufReadPre", "BufNewFile" },
        config = function()
            local lint = require("lint")

            -- Helper function to check if executable exists
            local function executable_exists(name)
                return vim.fn.executable(name) == 1
            end

            -- Configure linters by filetype (only if available)
            lint.linters_by_ft = {}

            -- Python linting (only if tools are available)
            if executable_exists("flake8") then
                lint.linters_by_ft.python = lint.linters_by_ft.python or {}
                table.insert(lint.linters_by_ft.python, "flake8")

                -- Custom flake8 configuration
                lint.linters.flake8.args = {
                    "--format=%(path)s:%(row)d:%(col)d:%(code)s:%(text)s",
                    "--no-show-source",
                    "--max-line-length=88",
                    "--extend-ignore=E203,W503",
                }
            end

            if executable_exists("mypy") then
                lint.linters_by_ft.python = lint.linters_by_ft.python or {}
                table.insert(lint.linters_by_ft.python, "mypy")
            end

            -- Lua linting (only if luacheck is available)
            if executable_exists("luacheck") then
                lint.linters_by_ft.lua = { "luacheck" }
            end

            -- Shell linting (only if shellcheck is available)
            if executable_exists("shellcheck") then
                lint.linters_by_ft.bash = { "shellcheck" }
                lint.linters_by_ft.sh = { "shellcheck" }
            end

            -- Markdown linting (only if markdownlint is available)
            if executable_exists("markdownlint") then
                lint.linters_by_ft.markdown = { "markdownlint" }
            end

            -- YAML linting (only if yamllint is available)
            if executable_exists("yamllint") then
                lint.linters_by_ft.yaml = { "yamllint" }
            end

            -- Auto-lint on save and text change
            local lint_augroup = vim.api.nvim_create_augroup("lint", { clear = true })
            vim.api.nvim_create_autocmd({ "BufEnter", "BufWritePost", "InsertLeave" }, {
                group = lint_augroup,
                callback = function()
                    -- Only lint if there are linters configured for this filetype
                    local ft = vim.bo.filetype
                    if lint.linters_by_ft[ft] and #lint.linters_by_ft[ft] > 0 then
                        lint.try_lint()
                    end
                end,
            })

            -- Manual lint trigger
            vim.keymap.set("n", "<leader>l", function()
                lint.try_lint()
            end, { desc = "Trigger linting for current file" })
        end,
    },
    {
        "nvimtools/none-ls.nvim",
        dependencies = {
            "nvim-lua/plenary.nvim",
        },
        event = { "BufReadPre", "BufNewFile" },
        config = function()
            local null_ls = require("null-ls")
            local sources = {}

            -- Helper function to check if executable exists
            local function executable_exists(name)
                return vim.fn.executable(name) == 1
            end

            -- Python formatters and diagnostics
            if executable_exists("black") then
                table.insert(sources, null_ls.builtins.formatting.black.with({
                    args = { "--line-length", "88", "--quiet", "-" },
                }))
            end

            if executable_exists("isort") then
                table.insert(sources, null_ls.builtins.formatting.isort)
            end

            -- Only add flake8 if it exists
            if executable_exists("flake8") then
                table.insert(sources, null_ls.builtins.diagnostics.flake8.with({
                    args = { "--max-line-length=88", "--extend-ignore=E203,W503", "--stdin-display-name", "$FILENAME", "-" },
                }))
            end

            -- Lua formatters and diagnostics
            if executable_exists("stylua") then
                table.insert(sources, null_ls.builtins.formatting.stylua)
            end

            -- Only add luacheck if it exists
            if executable_exists("luacheck") then
                table.insert(sources, null_ls.builtins.diagnostics.luacheck.with({
                    extra_args = { "--globals", "vim" },
                }))
            end

            -- Shell formatters and diagnostics
            if executable_exists("shfmt") then
                table.insert(sources, null_ls.builtins.formatting.shfmt.with({
                    args = { "-i", "2", "-ci" },
                }))
            end

            if executable_exists("shellcheck") then
                table.insert(sources, null_ls.builtins.diagnostics.shellcheck)
            end

            -- Markdown/YAML/JSON formatting
            if executable_exists("prettier") then
                table.insert(sources, null_ls.builtins.formatting.prettier.with({
                    filetypes = { "markdown", "yaml", "json" },
                }))
            end

            -- Generic formatters (always available)
            table.insert(sources, null_ls.builtins.formatting.trim_whitespace)
            table.insert(sources, null_ls.builtins.formatting.trim_newlines)

            null_ls.setup({
                sources = sources,

                -- Format on save
                on_attach = function(client, bufnr)
                    if client.supports_method("textDocument/formatting") then
                        vim.api.nvim_create_autocmd("BufWritePre", {
                            group = vim.api.nvim_create_augroup("LspFormatting", {}),
                            buffer = bufnr,
                            callback = function()
                                vim.lsp.buf.format({ async = false })
                            end,
                        })
                    end
                end,
            })
        end,
    },
}
