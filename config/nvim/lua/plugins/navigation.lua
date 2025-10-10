-- Navigation and file management

return {
    -- Fuzzy finder
    {
        "nvim-telescope/telescope.nvim",
        branch = "0.1.x",
        event = "VimEnter",
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
            require("telescope").setup({
                defaults = {
                    mappings = {
                        i = {
                            ["<C-k>"] = require("telescope.actions").move_selection_previous,
                            ["<C-j>"] = require("telescope.actions").move_selection_next,
                        },
                    },
                },
            })

            pcall(require("telescope").load_extension, "fzf")

            local builtin = require("telescope.builtin")
            vim.keymap.set("n", "<leader>ff", builtin.find_files, { desc = "Find files" })
            vim.keymap.set("n", "<leader>fg", builtin.live_grep, { desc = "Live grep" })
            vim.keymap.set("n", "<leader>fb", builtin.buffers, { desc = "Find buffers" })
            vim.keymap.set("n", "<leader>fh", builtin.help_tags, { desc = "Help tags" })
            vim.keymap.set("n", "<leader>fr", builtin.oldfiles, { desc = "Recent files" })
        end,
    },

    -- File explorer
    {
        "stevearc/oil.nvim",
        lazy = false, -- Load immediately to handle directory opening
        dependencies = {
            { "nvim-tree/nvim-web-devicons", lazy = false }
        },
        config = function()
            require("oil").setup({
                default_file_explorer = true,
                columns = { "icon", "permissions" },
                keymaps = {
                    ["<C-h>"] = false,
                    ["<M-h>"] = "actions.select_split",
                },
                view_options = {
                    show_hidden = true,
                },
                cleanup_delay_ms = false,
            })

            local set = vim.keymap.set

            -- Open parent directory in current window
            set("n", "<leader>e", "<CMD>Oil<CR>", { desc = "Open parent directory" })
            set("n", "-", "<CMD>Oil<CR>", { desc = "Open parent directory" })

            -- Open parent directory in floating window
            set("n", "<leader>ef", require("oil").toggle_float, { desc = "Open parent directory in floating window" })

            -- Open parent directory in vertical split
            set("n", "<leader>ev", "<CMD>vsplit | Oil<CR>", { desc = "Open parent directory in vertical split" })

            -- Custom quit that returns to Oil directory view
            set("n", "<leader>q", function()
                local bufnr = vim.api.nvim_get_current_buf()
                local bufname = vim.api.nvim_buf_get_name(bufnr)
                local buftype = vim.bo[bufnr].buftype
                local filetype = vim.bo[bufnr].filetype

                -- Check if this is a normal file buffer
                if buftype == "" and filetype ~= "oil" and bufname ~= "" and vim.fn.filereadable(bufname) == 1 then
                    local dir = vim.fn.fnamemodify(bufname, ":p:h")

                    -- Check if buffer is modified
                    if vim.bo[bufnr].modified then
                        vim.api.nvim_err_writeln("No write since last change")
                        return
                    end

                    -- Count remaining normal file buffers (excluding current)
                    local normal_bufs = vim.tbl_filter(function(buf)
                        return buf ~= bufnr
                            and vim.api.nvim_buf_is_valid(buf)
                            and vim.bo[buf].buftype == ""
                            and vim.bo[buf].filetype ~= "oil"
                            and vim.api.nvim_buf_get_name(buf) ~= ""
                            and vim.fn.filereadable(vim.api.nvim_buf_get_name(buf)) == 1
                    end, vim.api.nvim_list_bufs())

                    if #normal_bufs == 0 then
                        -- This is the last normal file buffer, replace with Oil
                        require("oil").open(dir)
                        vim.api.nvim_buf_delete(bufnr, {})
                    else
                        -- Other file buffers exist, just quit the window
                        vim.cmd("quit")
                    end
                else
                    -- Not a normal file buffer, quit normally
                    vim.cmd("quit")
                end
            end, { desc = "Quit and return to Oil directory" })

        end,
    },
}