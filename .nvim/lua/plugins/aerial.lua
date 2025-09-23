-- Code outline sidebar
return {
  "stevearc/aerial.nvim",
  dependencies = {
    "nvim-treesitter/nvim-treesitter",
    "nvim-tree/nvim-web-devicons"
  },
  config = function()
    require("aerial").setup({
      -- optionally use on_attach to set keymaps when aerial is attached to a buffer
      on_attach = function(bufnr)
        -- Jump to the next/previous symbol
        vim.keymap.set("n", "{", "<cmd>AerialPrev<CR>", {buffer = bufnr})
        vim.keymap.set("n", "}", "<cmd>AerialNext<CR>", {buffer = bufnr})
      end,

      -- Set up automatic aerial for certain filetypes
      auto_jump = false,

      -- Configure the layout
      layout = {
        max_width = { 40, 0.2 },
        width = nil,
        min_width = 20,
        default_direction = "prefer_right",
        placement = "window",
      },

      -- Show line numbers in aerial window
      show_guides = true,

      -- Filter symbols by kind
      filter_kind = {
        "Class",
        "Constructor",
        "Enum",
        "Function",
        "Interface",
        "Module",
        "Method",
        "Struct",
      },

      -- Automatically open aerial for these filetypes
      open_automatic = function(bufnr)
        local filename = vim.api.nvim_buf_get_name(bufnr)
        local is_large_file = vim.api.nvim_buf_line_count(bufnr) > 1000

        -- Only auto-open for Python files that aren't too large
        return filename:match("%.py$") and not is_large_file
      end,
    })

    -- Keymaps
    vim.keymap.set("n", "<leader>a", "<cmd>AerialToggle!<CR>", { desc = "Toggle symbols outline" })
    vim.keymap.set("n", "<leader>A", "<cmd>AerialNavToggle<CR>", { desc = "Toggle symbols navigation" })
  end
}
