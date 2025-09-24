-- Status line
return {
  "nvim-lualine/lualine.nvim",
  dependencies = { "nvim-tree/nvim-web-devicons" },
  config = function()
    local lualine = require("lualine")
    local lazy_status = require("lazy.status") -- to configure lazy pending plugin count

    local colors = {
      blue = "#65D1FF",
      green = "#3EFFDC",
      violet = "#FF61EF",
      yellow = "#FFDA7B",
      red = "#FF4A4A",
      fg = "#c3ccdc",
      bg = "#112638",
      inactive_bg = "#2c3043",
    }

    local my_lualine_theme = {
      normal = {
        a = { bg = colors.blue, fg = colors.bg, gui = "bold" },
        b = { bg = colors.bg, fg = colors.fg },
        c = { bg = colors.bg, fg = colors.fg },
      },
      insert = {
        a = { bg = colors.green, fg = colors.bg, gui = "bold" },
        b = { bg = colors.bg, fg = colors.fg },
        c = { bg = colors.bg, fg = colors.fg },
      },
      visual = {
        a = { bg = colors.violet, fg = colors.bg, gui = "bold" },
        b = { bg = colors.bg, fg = colors.fg },
        c = { bg = colors.bg, fg = colors.fg },
      },
      command = {
        a = { bg = colors.yellow, fg = colors.bg, gui = "bold" },
        b = { bg = colors.bg, fg = colors.fg },
        c = { bg = colors.bg, fg = colors.fg },
      },
      replace = {
        a = { bg = colors.red, fg = colors.bg, gui = "bold" },
        b = { bg = colors.bg, fg = colors.fg },
        c = { bg = colors.bg, fg = colors.fg },
      },
      inactive = {
        a = { bg = colors.inactive_bg, fg = colors.semilightgray, gui = "bold" },
        b = { bg = colors.inactive_bg, fg = colors.semilightgray },
        c = { bg = colors.inactive_bg, fg = colors.semilightgray },
      },
    }

    -- configure lualine with modified theme
    lualine.setup({
      options = {
        theme = my_lualine_theme,
      },
      sections = {
        lualine_a = { "mode" },
        lualine_b = { "branch", "diff", "diagnostics" },
        lualine_c = {
          "filename",
          -- Show current line diagnostic message
          {
            function()
              local line = vim.fn.line(".") - 1
              local col = vim.fn.col(".") - 1
              local diagnostics = vim.diagnostic.get(0, { lnum = line })

              if #diagnostics == 0 then
                return ""
              end

              -- Get the most severe diagnostic for current line
              local diagnostic = diagnostics[1]
              for _, d in ipairs(diagnostics) do
                if d.severity < diagnostic.severity then
                  diagnostic = d
                end
              end

              local icons = {
                [vim.diagnostic.severity.ERROR] = " ",
                [vim.diagnostic.severity.WARN] = " ",
                [vim.diagnostic.severity.INFO] = " ",
                [vim.diagnostic.severity.HINT] = " ",
              }

              local icon = icons[diagnostic.severity] or " "
              local message = diagnostic.message:gsub("\n", " "):gsub("\r", "")

              -- Truncate long messages
              if #message > 80 then
                message = message:sub(1, 77) .. "..."
              end

              return icon .. message
            end,
            color = function()
              local line = vim.fn.line(".") - 1
              local diagnostics = vim.diagnostic.get(0, { lnum = line })

              if #diagnostics == 0 then
                return { fg = colors.fg }
              end

              local diagnostic = diagnostics[1]
              for _, d in ipairs(diagnostics) do
                if d.severity < diagnostic.severity then
                  diagnostic = d
                end
              end

              local severity_colors = {
                [vim.diagnostic.severity.ERROR] = { fg = colors.red },
                [vim.diagnostic.severity.WARN] = { fg = colors.yellow },
                [vim.diagnostic.severity.INFO] = { fg = colors.blue },
                [vim.diagnostic.severity.HINT] = { fg = colors.green },
              }

              return severity_colors[diagnostic.severity] or { fg = colors.fg }
            end,
          },
        },
        lualine_x = {
          {
            lazy_status.updates,
            cond = lazy_status.has_updates,
            color = { fg = "#ff9e64" },
          },
          { "encoding" },
          { "fileformat" },
          { "filetype" },
        },
      },
    })
  end,
}
