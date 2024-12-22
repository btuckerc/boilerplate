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
                lualine_a = { mode },
                lualine_b = { 'branch' },
                lualine_c = {
                    {
                        'filename',
                        path = 1,  -- Show relative path
                        symbols = {
                            modified = '●',
                            readonly = '🔒',
                            unnamed = '[No Name]',
                        }
                    }
                },
                lualine_x = {
                    {
                        'diagnostics',
                        sources = { 'nvim_diagnostic' },
                        sections = { 'error', 'warn' },
                        symbols = { error = ' ', warn = ' ' },
                    },
                    'filetype'
                },
                lualine_y = { 'progress' },
                lualine_z = {
                    {
                        lazy_status.updates,
                        cond = lazy_status.has_updates,
                    },
                    'location'
                },
            },
            options = {
                icons_enabled = true,
                theme = "auto",
                component_separators = { left = '', right = '' },
                section_separators = { left = '', right = '' },
                disabled_filetypes = { 'alpha', 'neo-tree', 'Avante' },
                always_divide_middle = false,
                globalstatus = true,
            },
            extensions = {}, -- Ensure no filetype-specific extensions load
        })
    end,
}
