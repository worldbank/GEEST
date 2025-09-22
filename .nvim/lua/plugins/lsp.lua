-- LSP Configuration with Mason
return {
    {
        "williamboman/mason.nvim",
        config = function()
            require("mason").setup({
                ui = {
                    icons = {
                        package_installed = "✓",
                        package_pending = "➜",
                        package_uninstalled = "✗"
                    }
                }
            })
        end,
    },
    {
        "WhoIsSethDaniel/mason-tool-installer.nvim",
        dependencies = { "williamboman/mason.nvim" },
        config = function()
            require("mason-tool-installer").setup({
                ensure_installed = {
                    -- LSP servers
                    "pylsp",
                    "lua-language-server",
                    "bash-language-server",

                    -- Linters and formatters
                    "flake8",
                    "mypy",
                    "black",
                    "isort",
                    "shellcheck",
                    "shfmt",
                    "luacheck",
                },
                auto_update = false,
                run_on_start = false, -- Don't install automatically since you have system tools
            })
        end,
    },
    {
        "williamboman/mason-lspconfig.nvim",
        dependencies = { "mason.nvim", "nvim-lspconfig" },
        config = function()
            require("mason-lspconfig").setup({
                ensure_installed = { "pylsp", "lua_ls", "bashls" },
                automatic_installation = true,
            })
        end,
    },
    {
        "neovim/nvim-lspconfig",
        dependencies = {
            "hrsh7th/cmp-nvim-lsp",
            "mason.nvim",
            "mason-lspconfig.nvim",
        },
        config = function()
            local capabilities = require("cmp_nvim_lsp").default_capabilities()

            -- Use modern vim.lsp.config API (Neovim 0.11+)
            local function setup_lsp_server(name, config)
                config = config or {}
                config.capabilities = capabilities

                local success, _ = pcall(function()
                    vim.lsp.config(name, config)
                end)
                if not success then
                    vim.notify("LSP server " .. name .. " not available", vim.log.levels.INFO)
                end
            end

            -- Setup LSP servers with modern API
            setup_lsp_server("pylsp", {
                settings = {
                    pylsp = {
                        plugins = {
                            black = { enabled = true },
                            flake8 = { enabled = true, maxLineLength = 88 },
                            mypy = { enabled = true },
                        },
                    },
                },
            })

            setup_lsp_server("lua_ls", {
                settings = {
                    Lua = {
                        runtime = { version = 'LuaJIT' },
                        diagnostics = { globals = {'vim'} },
                        workspace = {
                            library = vim.api.nvim_get_runtime_file("", true),
                            checkThirdParty = false,
                        },
                        telemetry = { enable = false },
                    },
                },
            })

            setup_lsp_server("bashls", {})

            -- Key mappings for LSP
            vim.api.nvim_create_autocmd("LspAttach", {
                group = vim.api.nvim_create_augroup("UserLspConfig", {}),
                callback = function(ev)
                    vim.bo[ev.buf].omnifunc = "v:lua.vim.lsp.omnifunc"

                    local opts = { buffer = ev.buf }
                    vim.keymap.set("n", "gD", vim.lsp.buf.declaration, opts)
                    vim.keymap.set("n", "<M-Space>", vim.lsp.buf.definition, opts)
                    vim.keymap.set("n", "K", vim.lsp.buf.hover, opts)
                    vim.keymap.set("n", "gi", vim.lsp.buf.implementation, opts)
                    vim.keymap.set("n", "<C-k>", vim.lsp.buf.signature_help, opts)
                    vim.keymap.set("n", "<leader>rn", vim.lsp.buf.rename, opts)
                    vim.keymap.set({ "n", "v" }, "<leader>ca", vim.lsp.buf.code_action, opts)
                    vim.keymap.set("n", "gr", vim.lsp.buf.references, opts)
                    vim.keymap.set("n", "<leader>f", function()
                        vim.lsp.buf.format({ async = true })
                    end, opts)
                end,
            })
        end,
    }
}
