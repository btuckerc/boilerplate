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
    local tab_bg = transparent and "NONE" or colors.tab_bar_background

    -- Basic highlights
    vim.cmd("highlight Normal guifg=" .. colors.foreground .. " guibg=" .. bg)
    vim.cmd("highlight NormalNC guifg=" .. colors.foreground .. " guibg=" .. bg)

    -- Make more backgrounds transparent
    vim.cmd("highlight SignColumn guibg=" .. bg)
    vim.cmd("highlight LineNr guifg=" .. colors.color8 .. " guibg=" .. bg)
    vim.cmd("highlight CursorLineNr guifg=" .. colors.color11 .. " guibg=" .. bg)
    vim.cmd("highlight CursorLine guibg=" .. (transparent and "NONE" or colors.color0))
    vim.cmd("highlight StatusLine guifg=" .. colors.foreground .. " guibg=" .. (transparent and "NONE" or colors.active_tab_background))
    vim.cmd("highlight StatusLineNC guifg=" .. colors.inactive_tab_foreground .. " guibg=" .. (transparent and "NONE" or colors.inactive_tab_background))

    -- Floating windows
    vim.cmd("highlight NormalFloat guifg=" .. colors.foreground .. " guibg=" .. (transparent and "NONE" or colors.color0))
    vim.cmd("highlight FloatBorder guifg=" .. colors.tab_border_color .. " guibg=" .. (transparent and "NONE" or colors.color0))

    -- Pmenu (completion menu)
    vim.cmd("highlight Pmenu guifg=" .. colors.foreground .. " guibg=" .. (transparent and "NONE" or colors.color0))
    vim.cmd("highlight PmenuSel guifg=" .. colors.active_tab_foreground .. " guibg=" .. colors.active_tab_background)
    vim.cmd("highlight PmenuSbar guibg=" .. (transparent and "NONE" or colors.color8))
    vim.cmd("highlight PmenuThumb guibg=" .. colors.tab_border_color)

    -- Tabline highlights
    vim.cmd("highlight TabLine guibg=" .. (transparent and "NONE" or colors.inactive_tab_background) .. " guifg=" .. colors.inactive_tab_foreground)
    vim.cmd("highlight TabLineSel guibg=" .. (transparent and "NONE" or colors.active_tab_background) .. " guifg=" .. colors.active_tab_foreground)
    vim.cmd("highlight TabLineFill guibg=" .. tab_bg)

    -- Tab borders
    vim.cmd("highlight TabBorder guibg=" .. tab_bg .. " guifg=" .. colors.tab_border_color)

    -- Syntax highlighting using your color palette
    vim.cmd("highlight Comment guifg=" .. colors.color8)
    vim.cmd("highlight Constant guifg=" .. colors.color1)
    vim.cmd("highlight String guifg=" .. colors.color2)
    vim.cmd("highlight Identifier guifg=" .. colors.color4)
    vim.cmd("highlight Function guifg=" .. colors.color12)
    vim.cmd("highlight Statement guifg=" .. colors.color5)
    vim.cmd("highlight PreProc guifg=" .. colors.color6)
    vim.cmd("highlight Type guifg=" .. colors.color3)
    vim.cmd("highlight Special guifg=" .. colors.color11)
    vim.cmd("highlight Error guifg=" .. colors.color9)
    vim.cmd("highlight Todo guifg=" .. colors.color14 .. " gui=bold")

    -- Search highlighting
    vim.cmd("highlight Search guifg=" .. colors.color0 .. " guibg=" .. colors.color11)
    vim.cmd("highlight IncSearch guifg=" .. colors.color0 .. " guibg=" .. colors.color9)

    -- Visual mode
    vim.cmd("highlight Visual guibg=" .. colors.active_tab_background)

    -- Diagnostics
    vim.cmd("highlight DiagnosticError guifg=" .. colors.color9)
    vim.cmd("highlight DiagnosticWarn guifg=" .. colors.color11)
    vim.cmd("highlight DiagnosticInfo guifg=" .. colors.color4)
    vim.cmd("highlight DiagnosticHint guifg=" .. colors.color6)

    -- Telescope transparency
    vim.cmd("highlight TelescopeNormal guibg=" .. bg)
    vim.cmd("highlight TelescopeBorder guibg=" .. bg)
    vim.cmd("highlight TelescopePromptNormal guibg=" .. bg)
    vim.cmd("highlight TelescopePromptBorder guibg=" .. bg)
    vim.cmd("highlight TelescopeResultsNormal guibg=" .. bg)
    vim.cmd("highlight TelescopeResultsBorder guibg=" .. bg)
    vim.cmd("highlight TelescopePreviewNormal guibg=" .. bg)
    vim.cmd("highlight TelescopePreviewBorder guibg=" .. bg)

    -- Additional transparency for common highlight groups
    vim.cmd("highlight EndOfBuffer guibg=" .. bg)
    vim.cmd("highlight VertSplit guibg=" .. bg)
    vim.cmd("highlight WinSeparator guibg=" .. bg)
    vim.cmd("highlight FoldColumn guibg=" .. bg)
    vim.cmd("highlight Folded guibg=" .. bg)

    -- Make sure all backgrounds are transparent
    if transparent then
        vim.cmd("highlight NonText guibg=NONE")
        vim.cmd("highlight SpecialKey guibg=NONE")
        vim.cmd("highlight WinBar guibg=NONE")
        vim.cmd("highlight WinBarNC guibg=NONE")
    end
end

return M
