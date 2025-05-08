return {
    "MeanderingProgrammer/render-markdown.nvim",
    enabled = true,
    dependencies = {
        "nvim-treesitter/nvim-treesitter",
        "nvim-tree/nvim-web-devicons"
    },
    ft = { "markdown", "norg", "rmd", "org" },
    init = function()
        -- Define colors - using a calm, modern color palette
        local color1_bg = "#ff757f" -- Soft red for H1
        local color2_bg = "#4fd6be" -- Teal for H2
        local color3_bg = "#7dcfff" -- Light blue for H3
        local color4_bg = "#ff9e64" -- Orange for H4
        local color5_bg = "#7aa2f7" -- Blue for H5
        local color6_bg = "#c0caf5" -- Lavender for H6
        local color_fg = "#1F2335" -- Dark background color for text

        -- Heading background highlights
        vim.cmd(string.format([[highlight Headline1Bg guifg=%s guibg=%s gui=bold]], color_fg, color1_bg))
        vim.cmd(string.format([[highlight Headline2Bg guifg=%s guibg=%s gui=bold]], color_fg, color2_bg))
        vim.cmd(string.format([[highlight Headline3Bg guifg=%s guibg=%s gui=bold]], color_fg, color3_bg))
        vim.cmd(string.format([[highlight Headline4Bg guifg=%s guibg=%s gui=bold]], color_fg, color4_bg))
        vim.cmd(string.format([[highlight Headline5Bg guifg=%s guibg=%s gui=bold]], color_fg, color5_bg))
        vim.cmd(string.format([[highlight Headline6Bg guifg=%s guibg=%s gui=bold]], color_fg, color6_bg))
    end,
    opts = {
        heading = {
            sign = false,
            icons = { "󰎤 ", "󰎧 ", "󰎪 ", "󰎭 ", "󰎱 ", "󰎳 " },
            backgrounds = {
                "Headline1Bg",
                "Headline2Bg",
                "Headline3Bg",
                "Headline4Bg",
                "Headline5Bg",
                "Headline6Bg",
            },
            foregrounds = {
                "Headline1Fg",
                "Headline2Fg",
                "Headline3Fg",
                "Headline4Fg",
                "Headline5Fg",
                "Headline6Fg",
            },
        },
        code = {
            sign = false,
            width = "block",
            right_pad = 1,
        },
        bullet = {
            -- Turn on list bullet rendering
            enabled = true,
        },
        checkbox = {
            -- Turn on checkbox state rendering
            enabled = true,
            position = "inline",
            unchecked = {
                icon = "   󰄱 ",
                highlight = "RenderMarkdownUnchecked",
            },
            checked = {
                icon = "   󰱒 ",
                highlight = "RenderMarkdownChecked",
            },
        },
    },
}
