-- Comprehensive Git Integration
return {
    {
        -- Git signs in gutter
        "lewis6991/gitsigns.nvim",
        event = { "BufReadPre", "BufNewFile" },
        config = function()
            require("gitsigns").setup({
                signs = {
                    add = { text = "+" },
                    change = { text = "~" },
                    delete = { text = "_" },
                    topdelete = { text = "‾" },
                    changedelete = { text = "~" },
                },
                on_attach = function(bufnr)
                    local gs = package.loaded.gitsigns

                    local function map(mode, l, r, opts)
                        opts = opts or {}
                        opts.buffer = bufnr
                        vim.keymap.set(mode, l, r, opts)
                    end

                    -- Navigation
                    map('n', ']c', function()
                        if vim.wo.diff then return ']c' end
                        vim.schedule(function() gs.next_hunk() end)
                        return '<Ignore>'
                    end, {expr=true, desc = "Next git hunk"})

                    map('n', '[c', function()
                        if vim.wo.diff then return '[c' end
                        vim.schedule(function() gs.prev_hunk() end)
                        return '<Ignore>'
                    end, {expr=true, desc = "Previous git hunk"})

                    -- Actions
                    map('n', '<leader>gs', gs.stage_hunk, { desc = 'Stage hunk' })
                    map('n', '<leader>gr', gs.reset_hunk, { desc = 'Reset hunk' })
                    map('v', '<leader>gs', function() gs.stage_hunk {vim.fn.line('.'), vim.fn.line('v')} end, { desc = 'Stage hunk' })
                    map('v', '<leader>gr', function() gs.reset_hunk {vim.fn.line('.'), vim.fn.line('v')} end, { desc = 'Reset hunk' })
                    map('n', '<leader>gS', gs.stage_buffer, { desc = 'Stage buffer' })
                    map('n', '<leader>gu', gs.undo_stage_hunk, { desc = 'Undo stage hunk' })
                    map('n', '<leader>gR', gs.reset_buffer, { desc = 'Reset buffer' })
                    map('n', '<leader>gp', gs.preview_hunk, { desc = 'Preview hunk' })
                    map('n', '<leader>gb', function() gs.blame_line{full=true} end, { desc = 'Blame line' })
                    map('n', '<leader>gtb', gs.toggle_current_line_blame, { desc = 'Toggle line blame' })
                    map('n', '<leader>gd', gs.diffthis, { desc = 'Diff this' })
                    map('n', '<leader>gD', function() gs.diffthis('~') end, { desc = 'Diff this ~' })
                    map('n', '<leader>gtd', gs.toggle_deleted, { desc = 'Toggle deleted' })

                    -- Text object
                    map({'o', 'x'}, 'ih', ':<C-U>Gitsigns select_hunk<CR>', { desc = 'Select hunk' })
                end
            })
        end,
    },
    {
        -- Classic vim-fugitive for advanced Git operations
        "tpope/vim-fugitive",
        cmd = { "G", "Git", "Gdiffsplit", "Gread", "Gwrite", "Ggrep", "GMove", "GDelete", "GBrowse", "GRemove", "GRename", "Glgrep", "Gedit" },
        keys = {
            { "<leader>gg", ":Git<CR>", desc = "Git status" },
            { "<leader>gB", ":Git blame<CR>", desc = "Git blame" },
            { "<leader>gL", ":Git log<CR>", desc = "Git log" },
            { "<leader>gc", ":Git commit<CR>", desc = "Git commit" },
            { "<leader>gP", ":Git push<CR>", desc = "Git push" },
            { "<leader>gF", ":Git pull<CR>", desc = "Git pull" },
            { "<leader>gv", ":Gdiffsplit<CR>", desc = "Git diff split" },
            { "<leader>ge", ":Gedit<CR>", desc = "Git edit" },
            { "<leader>gw", ":Gwrite<CR>", desc = "Git write" },
        },
    },
    {
        -- Lazygit integration - terminal-based git UI
        "kdheepak/lazygit.nvim",
        cmd = "LazyGit",
        keys = {
            { "<leader>gg", ":LazyGit<CR>", desc = "Open LazyGit" },
            { "<leader>gl", ":LazyGit<CR>", desc = "Open LazyGit (full UI)" },
            { "<leader>gc", ":LazyGitFilterCurrentFile<CR>", desc = "LazyGit current file" },
        },
        config = function()
            -- LazyGit configuration is handled by the external lazygit tool
            -- No additional setup needed
        end,
    },
    {
        -- Enhanced diff viewing
        "sindrets/diffview.nvim",
        dependencies = "nvim-lua/plenary.nvim",
        cmd = { "DiffviewOpen", "DiffviewClose", "DiffviewToggleFiles", "DiffviewFocusFiles", "DiffviewRefresh" },
        keys = {
            { "<leader>gdo", ":DiffviewOpen<CR>", desc = "Open diffview" },
            { "<leader>gdc", ":DiffviewClose<CR>", desc = "Close diffview" },
            { "<leader>gdh", ":DiffviewFileHistory<CR>", desc = "File history" },
        },
        config = function()
            require("diffview").setup({
                diff_binaries = false,
                enhanced_diff_hl = false,
                git_cmd = { "git" },
                use_icons = true,
                show_help_hints = true,
                watch_index = true,
                icons = {
                    folder_closed = "",
                    folder_open = "",
                },
                signs = {
                    fold_closed = "",
                    fold_open = "",
                    done = "✓",
                },
                view = {
                    default = {
                        layout = "diff2_horizontal",
                        winbar_info = false,
                    },
                    merge_tool = {
                        layout = "diff3_horizontal",
                        disable_diagnostics = true,
                        winbar_info = true,
                    },
                    file_history = {
                        layout = "diff2_horizontal",
                        winbar_info = false,
                    },
                },
                file_panel = {
                    listing_style = "tree",
                    tree_options = {
                        flatten_dirs = true,
                        folder_statuses = "only_folded",
                    },
                    win_config = {
                        position = "left",
                        width = 35,
                        win_opts = {}
                    },
                },
                file_history_panel = {
                    log_options = {
                        git = {
                            single_file = {
                                diff_merges = "combined",
                            },
                            multi_file = {
                                diff_merges = "first-parent",
                            },
                        },
                    },
                    win_config = {
                        position = "bottom",
                        height = 16,
                        win_opts = {}
                    },
                },
                commit_log_panel = {
                    win_config = {
                        win_opts = {},
                    }
                },
                default_args = {
                    DiffviewOpen = {},
                    DiffviewFileHistory = {},
                },
                hooks = {},
                keymaps = {
                    disable_defaults = false,
                    view = {
                        { "n", "<tab>", false, { desc = "Listing style" } },
                        { "n", "q", "<cmd>DiffviewClose<cr>", { desc = "Close diffview" } },
                    },
                    file_panel = {
                        { "n", "q", "<cmd>DiffviewClose<cr>", { desc = "Close diffview" } },
                    },
                    file_history_panel = {
                        { "n", "q", "<cmd>DiffviewClose<cr>", { desc = "Close diffview" } },
                    },
                },
            })
        end,
    },
}
