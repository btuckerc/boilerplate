return {
    dir = "~/.config/nvim/lua/tucker/themes", -- Path to the directory where your theme resides
    priority = 1000, -- Ensure it's loaded early
    config = function()
        -- Load and apply the local theme
        local adwaita_dark = require("tucker.themes.current-theme")
        adwaita_dark.apply()
    end,
}
