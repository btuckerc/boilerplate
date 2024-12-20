return {
    'akinsho/bufferline.nvim',
    dependencies = {
        'moll/vim-bbye',
        'nvim-tree/nvim-web-devicons',
    },
    config = function()
        local bufferline = require('bufferline')
        bufferline.setup {
            options = {
                mode = 'buffers',
                themable = true,
                numbers = 'none', -- | "ordinal" | "buffer_id" | "both" | function({ ordinal, id, lower, raise }): string,
                close_command = 'Bdelete! %d',
                right_mouse_command = 'Bdelete! %d',
                left_mouse_command = 'buffer %d',
                middle_mouse_command = nil,
                -- buffer_close_icon = '󰅖',
                -- buffer_close_icon = '✗',
                buffer_close_icon = '✕',
                close_icon = '',
                path_components = 1, -- Show only the file name without the directory
                modified_icon = '●',
                left_trunc_marker = '',
                right_trunc_marker = '',
                max_name_length = 30,
                max_prefix_length = 30,
                tab_size = 21,
                diagnostics = false,
                diagnostics_update_in_insert = false,
                -- color_icons = true,
                show_buffer_icons = true,
                show_buffer_close_icons = true,
                show_close_icon = true,
                persist_buffer_sort = true,
                separator_style = { '│', '│' }, -- | "thick" | "thin" | { 'any', 'any' },
                enforce_regular_tabs = true,
                always_show_bufferline = true,
                show_tab_indicators = false,
                indicator = {
                    -- icon = '▎',
                    style = 'none',
                },
                icon_pinned = '󰐃',
                minimum_padding = 1,
                maximum_padding = 5,
                maximum_length = 15,
                sort_by = 'insert_at_end',
            },
            highlights = {
                buffer_selected = {
                    bold = true,
                    italic = false,
                },
            },
        }

        -- Keymaps
        vim.keymap.set("n", "<Tab>", "<Cmd>BufferLineCycleNext<CR>", {})
        vim.keymap.set("n", "<S-Tab>", "<Cmd>BufferLineCyclePrev<CR>", {})
    end,
}
