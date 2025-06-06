-- Converted Neovim Theme
-- Generated from Kitty theme: /Users/tucker/Documents/GitHub/boilerplate/config/kitty/current-theme.conf
-- Generated on: Thu Dec 26 17:45:36 EST 2024

local M = {}

M.colors = {
    background = "#1d1d1d",
    foreground = "#deddda",

    -- Tab bar improvements
    tab_bar_background = "#1d1d1d",
    active_tab_background = "#272727",
    active_tab_foreground = "#deddda",
    inactive_tab_background = "#131313",
    inactive_tab_foreground = "#7e7e7e",
    tab_border_color = "#404040",

    -- Colors
    color0 = "#151515",
    color1 = "#ff8eaf",
    color2 = "#a6e25f",
    color3 = "#87a8af",
    color4 = "#00c9f8",
    color5 = "#e85b92",
    color6 = "#5f868f",
    color7 = "#d5f1f2",
    color8 = "#696969",
    color9 = "#ed4c7a",
    color10 = "#a6e179",
    color11 = "#ffdf6b",
    color12 = "#79d2ff",
    color13 = "#bb5d79",
    color14 = "#f8e578",
    color15 = "#e2f1f6",
}

-- Function to apply the theme
function M.apply(transparent)
    local colors = M.colors
    local bg = transparent and "NONE" or colors.background

    -- Basic highlights
    vim.cmd("highlight Normal guifg=" .. colors.foreground .. " guibg=" .. bg)

    -- Tabline highlights
    vim.cmd("highlight TabLine guibg=" .. colors.inactive_tab_background .. " guifg=" .. colors.inactive_tab_foreground)
    vim.cmd("highlight TabLineSel guibg=" .. colors.active_tab_background .. " guifg=" .. colors.active_tab_foreground)
    vim.cmd("highlight TabLineFill guibg=" .. colors.tab_bar_background)

    -- Tab borders
    vim.cmd("highlight TabBorder guibg=" .. colors.tab_bar_background .. " guifg=" .. colors.tab_border_color)
end

return M
