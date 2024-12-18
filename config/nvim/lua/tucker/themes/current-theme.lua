-- Converted Neovim Theme
-- Generated from Kitty theme: /Users/tucker/Documents/GitHub/boilerplate/config/kitty/current-theme.conf
-- Generated on: Tue Dec 17 19:39:33 EST 2024

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

    -- Basic highlights
    vim.cmd("highlight Normal guifg=" .. colors.foreground .. " guibg=" .. colors.background)

    -- Tabline highlights
    vim.cmd("highlight TabLine guibg=" .. colors.inactive_tab_background .. " guifg=" .. colors.inactive_tab_foreground)
    vim.cmd("highlight TabLineSel guibg=" .. colors.active_tab_background .. " guifg=" .. colors.active_tab_foreground)
    vim.cmd("highlight TabLineFill guibg=" .. colors.tab_bar_background)

    -- Tab borders
    vim.cmd("highlight TabBorder guibg=" .. colors.tab_bar_background .. " guifg=" .. colors.tab_border_color)
end

return M
