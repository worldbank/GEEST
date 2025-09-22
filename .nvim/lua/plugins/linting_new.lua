-- Linting Configuration with nvim-lint
return {
    {
        "mfussenegger/nvim-lint",
        event = { "BufReadPre", "BufNewFile" },
        config = function()
            local lint = require("lint")

            -- Helper function to check if tool is available
            local function tool_available(tool)
                if vim.fn.executable(tool) == 1 then
                    return true
                end
                -- Check if it's a Python module
                if tool == "flake8" or tool == "mypy" then
                    for _, python in ipairs({"python", "python3"}) do
                        if vim.fn.executable(python) == 1 then
                            local result = vim.fn.system(python .. " -c \"import " .. tool .. "; print('OK')\"")
                            if vim.v.shell_error == 0 and result:match("OK") then
                                return true
                            end
                        end
                    end
                end
                return false
            end

            -- Configure linters by filetype
            local linters_by_ft = {}

            -- Python linting
            local python_linters = {}
            if tool_available("flake8") then
                table.insert(python_linters, "flake8")
            end
            if tool_available("mypy") then
                table.insert(python_linters, "mypy")
            end
            if #python_linters > 0 then
                linters_by_ft.python = python_linters
            end

            -- Shell linting
            if tool_available("shellcheck") then
                linters_by_ft.bash = { "shellcheck" }
                linters_by_ft.sh = { "shellcheck" }
            end

            -- Lua linting
            if tool_available("luacheck") then
                linters_by_ft.lua = { "luacheck" }
            end

            -- Markdown linting
            if tool_available("markdownlint") then
                linters_by_ft.markdown = { "markdownlint" }
            end

            -- YAML linting
            if tool_available("yamllint") then
                linters_by_ft.yaml = { "yamllint" }
            end

            -- Set the linters
            lint.linters_by_ft = linters_by_ft

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
}
