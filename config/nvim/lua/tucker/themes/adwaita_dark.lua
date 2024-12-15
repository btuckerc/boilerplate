-- Adwaita Dark Theme for Neovim
-- License: MIT
-- Author: Emil Löfquist (https://github.com/ewal)
-- Inspired by: https://github.com/Mofiqul/adwaita.nvim

local M = {}

M.colors = {
    background = "#1d1d1d",
    foreground = "#deddda",
    selection_background = "#303030",
    selection_foreground = "#c0bfbc",
    url_color = "#1a5fb4",
    cursor = "#deddda",
    cursor_text_color = "#1d1d1d",

    -- Tab bar improvements
    tab_bar_background = "#202020",        -- Slightly lighter dark background for the tab bar
    active_tab_background = "#30353b",     -- Distinct active tab with a soft dark gray
    active_tab_foreground = "#e6e6e6",     -- Brighter text for the active tab
    inactive_tab_background = "#282828",   -- Darker background for inactive tabs
    inactive_tab_foreground = "#7e7e7e",   -- Muted gray text for inactive tabs
    tab_border_color = "#404040",          -- Subtle border between tabs

    active_border_color = "#4f4f4f",
    inactive_border_color = "#282828",
    bell_border_color = "#ed333b",
    visual_bell_color = "none",
    tab_bar_margin_color = "none",

    -- Colors
    color0 = "#1d1d1d",
    color1 = "#ed333b",
    color2 = "#57e389",
    color3 = "#ff7800",
    color4 = "#62a0ea",
    color5 = "#9141ac",
    color6 = "#5bc8af",
    color7 = "#deddda",
    color8 = "#9a9996",
    color9 = "#f66151",
    color10 = "#8ff0a4",
    color11 = "#ffa348",
    color12 = "#99c1f1",
    color13 = "#dc8add",
    color14 = "#93ddc2",
    color15 = "#f6f5f4",
}

-- Function to apply the theme
function M.apply()
    local colors = M.colors
    vim.cmd("highlight Normal guifg=" .. colors.foreground .. " guibg=" .. colors.background)
    vim.cmd("highlight Visual guifg=" .. colors.selection_foreground .. " guibg=" .. colors.selection_background)
    vim.cmd("highlight Cursor guifg=" .. colors.cursor_text_color .. " guibg=" .. colors.cursor)
    -- Add more highlight groups as needed
end

return M

