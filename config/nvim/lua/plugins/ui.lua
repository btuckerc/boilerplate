-- UI and visual enhancements

return {
    -- Statusline with custom misery scheduler integration
    {
        "nvim-lualine/lualine.nvim",
        dependencies = { "nvim-tree/nvim-web-devicons" },
        config = function()
            local function misery_task_count()
                -- This function is to integrate your custom 'misery.scheduler'
                local misery_ok, misery = pcall(require, "misery.scheduler")
                if not misery_ok then return "" end

                local task_count = #misery.tasks
                if task_count > 0 then
                    return string.format("Tasks: %d", task_count)
                end
                return ""
            end

            require("lualine").setup({
                options = {
                    icons_enabled = false,
                    theme = "auto",
                    component_separators = { left = ' ', right = ' '},
                    section_separators = { left = ' ', right = ' '},
                    disabled_filetypes = {
                        statusline = {},
                        winbar = {},
                    },
                    always_divide_middle = true,
                },
                sections = {
                    lualine_a = { "mode" },
                    lualine_b = { "branch", "diff", misery_task_count },
                    lualine_c = {},
                    lualine_x = { "filename" },
                    lualine_y = { "filetype" },
                    lualine_z = { "location" },
                },
            })
        end,
    },

    -- Mini.nvim utilities
    {
        "echasnovski/mini.nvim",
        config = function()
            -- Better Around/Inside textobjects
            require("mini.ai").setup({ n_lines = 500 })

            -- Add/delete/replace surroundings
            require("mini.surround").setup()
        end,
    },

    -- Ghostty terminal integration
    {
        "ghostty",
        dir = "/Applications/Ghostty.app/Contents/Resources/vim/vimfiles/",
        lazy = false,
    },

    -- Colorizer for CSS colors
    {
        "norcalli/nvim-colorizer.lua",
        ft = { "css", "scss", "html", "javascript", "typescript" },
        config = function()
            require("colorizer").setup()
        end,
    },
}