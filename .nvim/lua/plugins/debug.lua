-- Debug Adapter Protocol (DAP) Configuration
--
-- Remote Debugging Setup:
-- 1. Install debugpy in your remote environment: pip install debugpy
-- 2. In your Python code, add: import debugpy; debugpy.listen(5678); debugpy.wait_for_client()
-- 3. Run your Python script
-- 4. In Neovim, use <leader>da to attach to the remote debugger
--
-- Key bindings:
-- <leader>da - Attach to remote debugger (prompts for host/port)
-- <leader>db - Toggle breakpoint at current line
-- <leader>dx - Remove ALL breakpoints
-- <leader>dX - Remove breakpoint on current line
-- <leader>du - Toggle DAP UI
-- <leader>de - Evaluate expression under cursor or selection
return {
    {
        "mfussenegger/nvim-dap",
        dependencies = {
            "rcarriga/nvim-dap-ui",
            "theHamsta/nvim-dap-virtual-text",
            "nvim-neotest/nvim-nio",
            "williamboman/mason.nvim",
            "mfussenegger/nvim-dap-python",
        },
        keys = {
            -- Breakpoint management
            { "<leader>db", function() require("dap").toggle_breakpoint() end, desc = "Toggle breakpoint" },
            { "<leader>dB", function() require("dap").set_breakpoint(vim.fn.input('Breakpoint condition: ')) end, desc = "Conditional breakpoint" },
            { "<leader>dx", function() require("dap").clear_breakpoints() end, desc = "Remove all breakpoints" },
            { "<leader>dX", function()
                local line = vim.fn.line('.')
                require("dap").clear_breakpoints()
                vim.notify("Cleared breakpoint on line " .. line)
            end, desc = "Remove breakpoint on current line" },

            -- Session control
            { "<leader>dc", function() require("dap").continue() end, desc = "Continue" },
            { "<leader>dC", function() require("dap").run_to_cursor() end, desc = "Run to cursor" },
            { "<leader>da", function()
                local host = vim.fn.input("Host (default localhost): ")
                if host == "" then host = "localhost" end
                local port = vim.fn.input("Port (default 5678): ")
                if port == "" then port = "5678" end
                require("dap").run({
                    type = "python",
                    request = "attach",
                    name = "Remote Attach",
                    connect = {
                        host = host,
                        port = tonumber(port)
                    },
                })
            end, desc = "Attach to remote debugger" },

            -- Navigation and execution
            { "<leader>dg", function() require("dap").goto_() end, desc = "Go to line (no execute)" },
            { "<leader>di", function() require("dap").step_into() end, desc = "Step into" },
            { "<leader>do", function() require("dap").step_over() end, desc = "Step over" },
            { "<leader>dO", function() require("dap").step_out() end, desc = "Step out" },
            { "<leader>dj", function() require("dap").down() end, desc = "Down" },
            { "<leader>dk", function() require("dap").up() end, desc = "Up" },

            -- Session management
            { "<leader>dl", function() require("dap").run_last() end, desc = "Run last" },
            { "<leader>dp", function() require("dap").pause() end, desc = "Pause" },
            { "<leader>dr", function() require("dap").repl.toggle() end, desc = "Toggle REPL" },
            { "<leader>ds", function() require("dap").session() end, desc = "Session" },
            { "<leader>dt", function() require("dap").terminate() end, desc = "Terminate" },
            { "<leader>dw", function() require("dap.ui.widgets").hover() end, desc = "Widgets" },
        },
        config = function()
            local dap = require("dap")

            -- Set up signs
            vim.fn.sign_define('DapBreakpoint', {text='🔴', texthl='', linehl='', numhl=''})
            vim.fn.sign_define('DapBreakpointCondition', {text='🟡', texthl='', linehl='', numhl=''})
            vim.fn.sign_define('DapLogPoint', {text='🟢', texthl='', linehl='', numhl=''})
            vim.fn.sign_define('DapStopped', {text='👉', texthl='', linehl='debugPC', numhl=''})
            vim.fn.sign_define('DapBreakpointRejected', {text='🚫', texthl='', linehl='', numhl=''})

            -- Python debugging configuration
            require("dap-python").setup("python")

            -- Custom Python configuration
            table.insert(dap.configurations.python, {
                type = "python",
                request = "launch",
                name = "Launch file with arguments",
                program = "${file}",
                args = function()
                    local args_string = vim.fn.input('Arguments: ')
                    return vim.split(args_string, " +")
                end,
                console = "integratedTerminal",
                pythonPath = function()
                    local cwd = vim.fn.getcwd()
                    if vim.fn.executable(cwd .. '/.venv/bin/python') == 1 then
                        return cwd .. '/.venv/bin/python'
                    elseif vim.fn.executable(cwd .. '/venv/bin/python') == 1 then
                        return cwd .. '/venv/bin/python'
                    else
                        return '/usr/bin/python'
                    end
                end,
            })

            -- Django configuration
            table.insert(dap.configurations.python, {
                type = "python",
                request = "launch",
                name = "Django",
                program = "${workspaceFolder}/manage.py",
                args = {"runserver", "--noreload"},
                console = "integratedTerminal",
                django = true,
                pythonPath = function()
                    local cwd = vim.fn.getcwd()
                    if vim.fn.executable(cwd .. '/.venv/bin/python') == 1 then
                        return cwd .. '/.venv/bin/python'
                    elseif vim.fn.executable(cwd .. '/venv/bin/python') == 1 then
                        return cwd .. '/venv/bin/python'
                    else
                        return '/usr/bin/python'
                    end
                end,
            })

            -- Remote debugging configuration
            table.insert(dap.configurations.python, {
                type = "python",
                request = "attach",
                name = "Remote Attach (localhost:5678)",
                connect = {
                    host = "localhost",
                    port = 5678,
                },
                pathMappings = {
                    {
                        localRoot = "${workspaceFolder}",
                        remoteRoot = ".",
                    },
                },
            })
        end,
    },
    {
        "rcarriga/nvim-dap-ui",
        dependencies = { "mfussenegger/nvim-dap", "nvim-neotest/nvim-nio" },
        keys = {
            { "<leader>du", function() require("dapui").toggle() end, desc = "Toggle DAP UI" },
            { "<leader>de", function() require("dapui").eval() end, desc = "Eval", mode = {"n", "v"} },
        },
        config = function()
            local dap = require("dap")
            local dapui = require("dapui")

            dapui.setup({
                icons = { expanded = "▾", collapsed = "▸", current_frame = "▸" },
                mappings = {
                    expand = { "<CR>", "<2-LeftMouse>" },
                    open = "o",
                    remove = "d",
                    edit = "e",
                    repl = "r",
                    toggle = "t",
                },
                element_mappings = {},
                expand_lines = vim.fn.has("nvim-0.7") == 1,
                layouts = {
                    {
                        elements = {
                            { id = "scopes", size = 0.25 },
                            "breakpoints",
                            "stacks",
                            "watches",
                        },
                        size = 40,
                        position = "left",
                    },
                    {
                        elements = {
                            "repl",
                            "console",
                        },
                        size = 0.25,
                        position = "bottom",
                    },
                },
                controls = {
                    enabled = true,
                    element = "repl",
                    icons = {
                        pause = "",
                        play = "",
                        step_into = "",
                        step_over = "",
                        step_out = "",
                        step_back = "",
                        run_last = "↻",
                        terminate = "□",
                    },
                },
                floating = {
                    max_height = nil,
                    max_width = nil,
                    border = "single",
                    mappings = {
                        close = { "q", "<Esc>" },
                    },
                },
                windows = { indent = 1 },
                render = {
                    max_type_length = nil,
                    max_value_lines = 100,
                },
            })

            -- Automatically open/close DAP UI
            dap.listeners.after.event_initialized["dapui_config"] = function()
                dapui.open()
            end
            dap.listeners.before.event_terminated["dapui_config"] = function()
                dapui.close()
            end
            dap.listeners.before.event_exited["dapui_config"] = function()
                dapui.close()
            end
        end,
    },
    {
        "theHamsta/nvim-dap-virtual-text",
        dependencies = { "mfussenegger/nvim-dap", "nvim-treesitter/nvim-treesitter" },
        config = function()
            require("nvim-dap-virtual-text").setup({
                enabled = true,
                enabled_commands = true,
                highlight_changed_variables = true,
                highlight_new_as_changed = false,
                show_stop_reason = true,
                commented = false,
                only_first_definition = true,
                all_references = false,
                clear_on_continue = false,
                display_callback = function(variable, buf, stackframe, node, options)
                    if options.virt_text_pos == 'inline' then
                        return ' = ' .. variable.value
                    else
                        return variable.name .. ' = ' .. variable.value
                    end
                end,
                virt_text_pos = vim.fn.has 'nvim-0.10' == 1 and 'inline' or 'eol',
                all_frames = false,
                virt_lines = false,
                virt_text_win_col = nil,
            })
        end,
    },
    {
        "mfussenegger/nvim-dap-python",
        dependencies = { "mfussenegger/nvim-dap" },
        ft = "python",
        config = function()
            -- This will be configured in the main dap config above
        end,
    },
}
