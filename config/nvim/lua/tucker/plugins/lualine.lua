return {
    "nvim-lualine/lualine.nvim",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    config = function()
        local lualine = require("lualine")
        local lazy_status = require("lazy.status")

        local mode = {
            'mode',
            fmt = function(str)
                return ' ' .. str
            end,
        }

        -- Minimal lualine setup for Lazy updates only
        lualine.setup({
            sections = {
                lualine_a = {}, -- Disable this section
                -- lualine_a = { mode },
                lualine_b = {}, -- Disable this section
                -- lualine_b = { 'branch' },
                lualine_c = {}, -- Disable this section
                lualine_x = {}, -- Disable this section
                lualine_y = {}, -- Disable this section
                lualine_z = {
                    {
                        lazy_status.updates,
                        cond = lazy_status.has_updates, -- Only show when updates are pending
                        -- color = { fg = "#ff9e64" }, -- Optional color for visibility
                    },
                },
            },
            options = {
                icons_enabled = true,
                theme = "auto",
                component_separators = { left = '', right = '' },
                section_separators = { left = '', right = '' },
                disabled_filetypes = { 'alpha', 'neo-tree', 'Avante' },
                -- always_divide_middle = true,
                always_divide_middle = false,
            },
            extensions = {}, -- Ensure no filetype-specific extensions load
        })
    end,
}

