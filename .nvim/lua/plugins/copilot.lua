-- GitHub Copilot Integration
return {
    {
        "zbirenbaum/copilot.lua",
        cmd = "Copilot",
        event = "InsertEnter",
        config = function()
            require("copilot").setup({
                panel = {
                    enabled = true,
                    auto_refresh = true,
                    keymap = {
                        jump_prev = "[[",
                        jump_next = "]]",
                        accept = "<CR>",
                        refresh = "gr",
                        open = "<M-CR>",
                    },
                    layout = {
                        position = "bottom", -- | top | left | right
                        ratio = 0.4,
                    },
                },
                suggestion = {
                    enabled = true,
                    auto_trigger = true,
                    debounce = 75,
                    keymap = {
                        accept = "<C-l>",
                        accept_word = false,
                        accept_line = false,
                        next = "<M-]>",
                        prev = "<M-[>",
                        dismiss = "<C-]>",
                    },
                },
                filetypes = {
                    yaml = false,
                    markdown = false,
                    help = false,
                    gitcommit = false,
                    gitrebase = false,
                    hgcommit = false,
                    svn = false,
                    cvs = false,
                    ["."] = false,
                },
                copilot_node_command = "node", -- Node.js version must be > 16.x
                server_opts_overrides = {},
            })
        end,
    },
    {
        "CopilotC-Nvim/CopilotChat.nvim",
        branch = "canary",
        dependencies = {
            { "zbirenbaum/copilot.lua" }, -- or github/copilot.vim
            { "nvim-lua/plenary.nvim" }, -- for curl, log wrapper
        },
        event = "VeryLazy",
        config = function()
            local chat = require("CopilotChat")

            chat.setup({
                debug = false,
                show_help = "yes", -- Show help text for CopilotChatInPlace
                prompts = {
                    Explain = "Please explain how the following code works.",
                    Review = "Please review the following code and provide suggestions for improvement.",
                    Tests = "Please explain how the selected code works, then generate unit tests for it.",
                    Refactor = "Please refactor the following code to improve its clarity and readability.",
                    FixCode = "Please fix the following code to make it work as intended.",
                    FixError = "Please explain the error in the following text and provide a solution.",
                    BetterNamings = "Please provide better names for the following variables and functions.",
                    Documentation = "Please provide documentation for the following code.",
                    SwaggerApiDocs = "Please provide documentation for the following API using Swagger.",
                    SwaggerJSDoc = "Please write JSDoc for the following API using Swagger.",
                },
                window = {
                    layout = 'vertical', -- 'vertical', 'horizontal', 'float'
                    width = 0.5, -- fractional width of parent, or absolute width in columns when > 1
                    height = 0.5, -- fractional height of parent, or absolute height in rows when > 1
                    -- Options below only apply to floating windows
                    relative = 'editor', -- 'editor', 'win', 'cursor', 'mouse'
                    border = 'single', -- 'none', single', 'double', 'rounded', 'solid', 'shadow'
                    title = 'Copilot Chat', -- title of chat window
                    zindex = 1, -- determines if window is on top or below other floating windows
                },
            })

            -- Key mappings for Copilot Chat
            vim.keymap.set('n', '<leader>cc', ':CopilotChatToggle<CR>', { desc = 'Toggle Copilot Chat' })
            vim.keymap.set('v', '<leader>ce', ':CopilotChatExplain<CR>', { desc = 'Explain selection' })
            vim.keymap.set('v', '<leader>cr', ':CopilotChatReview<CR>', { desc = 'Review selection' })
            vim.keymap.set('v', '<leader>cf', ':CopilotChatFix<CR>', { desc = 'Fix selection' })
            vim.keymap.set('v', '<leader>co', ':CopilotChatOptimize<CR>', { desc = 'Optimize selection' })
            vim.keymap.set('v', '<leader>cd', ':CopilotChatDocs<CR>', { desc = 'Document selection' })
            vim.keymap.set('v', '<leader>ct', ':CopilotChatTests<CR>', { desc = 'Generate tests' })

            -- Inline Copilot requests (like VS Code inline editing)
            vim.keymap.set('n', '<leader>ci', function()
                local input = vim.fn.input('Copilot request: ')
                if input ~= '' then
                    vim.cmd('CopilotChat ' .. input)
                end
            end, { desc = 'Inline Copilot request' })

            vim.keymap.set('v', '<leader>ci', function()
                local input = vim.fn.input('Copilot request for selection: ')
                if input ~= '' then
                    vim.cmd("'<,'>CopilotChat " .. input)
                end
            end, { desc = 'Inline Copilot request for selection' })
        end,
    },
}
