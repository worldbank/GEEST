-- Telescope fuzzy finder
return {
  "nvim-telescope/telescope.nvim",
  tag = "0.1.5",
  dependencies = {
    "nvim-lua/plenary.nvim",
    {
      "nvim-telescope/telescope-fzf-native.nvim",
      build = "make",
      cond = function()
        return vim.fn.executable("make") == 1
      end,
    },
  },
  config = function()
    local telescope = require("telescope")
    local actions = require("telescope.actions")

    telescope.setup({
      defaults = {
        mappings = {
          i = {
            ["<C-k>"] = actions.move_selection_previous,
            ["<C-j>"] = actions.move_selection_next,
            ["<C-q>"] = actions.send_selected_to_qflist + actions.open_qflist,
          },
        },
        file_ignore_patterns = {
          "%.git/",
          "__pycache__/",
          "%.pyc$",
          "node_modules/",
          "%.egg%-info/",
          "build/",
          "dist/",
        },
        -- Open files in current buffer instead of new window
        layout_strategy = "horizontal",
        layout_config = {
          prompt_position = "top",
        },
        sorting_strategy = "ascending",
      },
      pickers = {
        find_files = {
          -- Open in current buffer
          attach_mappings = function(_, map)
            map("i", "<CR>", actions.select_default)
            map("n", "<CR>", actions.select_default)
            return true
          end,
        },
        live_grep = {
          attach_mappings = function(_, map)
            map("i", "<CR>", actions.select_default)
            map("n", "<CR>", actions.select_default)
            return true
          end,
        },
        buffers = {
          attach_mappings = function(_, map)
            map("i", "<CR>", actions.select_default)
            map("n", "<CR>", actions.select_default)
            return true
          end,
        },
      },
    })

    -- Enable telescope fzf native, if installed
    pcall(require("telescope").load_extension, "fzf")

    -- Set keymaps
    local builtin = require("telescope.builtin")
    vim.keymap.set("n", "<leader>ff", builtin.find_files, { desc = "Find files" })
    vim.keymap.set("n", "<leader>fg", builtin.live_grep, { desc = "Live grep" })
    vim.keymap.set("n", "<leader>fb", builtin.buffers, { desc = "Find buffers" })
    vim.keymap.set("n", "<leader>fh", builtin.help_tags, { desc = "Help tags" })
    vim.keymap.set("n", "<leader>fr", builtin.oldfiles, { desc = "Recent files" })
    vim.keymap.set("n", "<leader>fc", builtin.commands, { desc = "Commands" })
    vim.keymap.set("n", "<leader>fk", builtin.keymaps, { desc = "Find keymaps" })
    vim.keymap.set("n", "<leader>fs", builtin.grep_string, { desc = "Grep string" })

    -- LSP and symbols
    vim.keymap.set("n", "<leader>fo", builtin.lsp_document_symbols, { desc = "Document symbols" })
    vim.keymap.set("n", "<leader>fO", builtin.lsp_workspace_symbols, { desc = "Workspace symbols" })
    vim.keymap.set("n", "<leader>fS", builtin.lsp_dynamic_workspace_symbols, { desc = "Dynamic workspace symbols" })

    -- Python-specific file finder
    vim.keymap.set("n", "<leader>fy", function()
      builtin.find_files({
        find_command = { "fd", "--type", "f", "--extension", "py" }
      })
    end, { desc = "Find Python files" })

    -- Alternative Python finder using glob pattern (if fd is not available)
    vim.keymap.set("n", "<leader>fY", function()
      builtin.find_files({
        prompt_title = "Find Python Files",
        cwd = vim.fn.getcwd(),
        search_dirs = { vim.fn.getcwd() },
        file_ignore_patterns = { "node_modules", ".git", "__pycache__", "%.pyc" },
        additional_args = function()
          return { "--glob", "*.py" }
        end
      })
    end, { desc = "Find Python files (glob)" })
  end,
}
