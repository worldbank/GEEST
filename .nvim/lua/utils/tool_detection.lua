-- Tool Detection Utilities
local M = {}

-- Function to find a tool in various ways
function M.find_tool(tool_name)
    -- Method 1: Direct executable check
    if vim.fn.executable(tool_name) == 1 then
        return tool_name
    end

    -- Method 2: Try with python -m for Python tools
    if tool_name == "flake8" or tool_name == "mypy" or tool_name == "black" then
        local python_executables = {"python", "python3"}
        for _, python in ipairs(python_executables) do
            if vim.fn.executable(python) == 1 then
                -- Test if the module exists
                local test_cmd = python .. " -c \"import " .. tool_name .. "; print('OK')\""
                local result = vim.fn.system(test_cmd)
                if vim.v.shell_error == 0 and result:match("OK") then
                    return {python, "-m", tool_name}
                end
            end
        end
    end

    -- Method 3: Check common Nix store paths
    local nix_paths = vim.split(vim.env.PATH or "", ":")
    for _, path in ipairs(nix_paths) do
        local full_path = path .. "/" .. tool_name
        if vim.fn.executable(full_path) == 1 then
            return full_path
        end
    end

    return nil
end

-- Function to setup a linter with automatic tool detection
function M.setup_linter(lint, tool_name, custom_config)
    local tool = M.find_tool(tool_name)
    if not tool then
        return nil
    end

    if type(tool) == "table" then
        -- This is a python -m command
        lint.linters[tool_name] = lint.linters[tool_name] or {}
        lint.linters[tool_name].cmd = tool[1]  -- python
        local base_args = lint.linters[tool_name].args or {}
        lint.linters[tool_name].args = vim.list_extend({tool[2], tool[3]}, base_args) -- -m toolname
    elseif custom_config then
        -- Apply custom configuration
        for key, value in pairs(custom_config) do
            lint.linters[tool_name] = lint.linters[tool_name] or {}
            lint.linters[tool_name][key] = value
        end
    end

    return tool_name
end

return M
