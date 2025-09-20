-- Additional utilities
return {
  -- Comment toggle
  {
    "numToStr/Comment.nvim",
    event = { "BufReadPre", "BufNewFile" },
    config = function()
      require("Comment").setup()
    end,
  },

  -- Which key - shows keybindings
  {
    "folke/which-key.nvim",
    event = "VeryLazy",
    init = function()
      vim.o.timeout = true
      vim.o.timeoutlen = 500
    end,
    config = function()
      local wk = require("which-key")
      wk.setup({
        window = {
          border = "rounded",
          position = "bottom",
          margin = { 1, 0, 1, 0 },
          padding = { 2, 2, 2, 2 },
        },
      })

      -- Define key group descriptions
      wk.register({
        ["<leader>f"] = { name = "Find" },
        ["<leader>e"] = { name = "Explorer" },
        ["<leader>h"] = { name = "Git Hunks" },
        ["<leader>c"] = { name = "Code" },
        ["<leader>r"] = { name = "Rename/Replace" },
        ["<leader>s"] = { name = "Split" },
        ["<leader>l"] = { name = "Location List" },
        ["<leader>b"] = { name = "Buffer" },
      })
    end,
  },

  -- Indent guides
  {
    "lukas-reineke/indent-blankline.nvim",
    event = { "BufReadPre", "BufNewFile" },
    main = "ibl",
    config = function()
      require("ibl").setup({
        indent = { char = "┊" },
        scope = { enabled = false },
      })
    end,
  },

  -- Better notifications
  {
    "rcarriga/nvim-notify",
    config = function()
      require("notify").setup({
        background_colour = "#000000",
        render = "minimal",
      })
      vim.notify = require("notify")
    end,
  },
}
