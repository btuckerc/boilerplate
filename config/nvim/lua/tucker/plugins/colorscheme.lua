return {
    dir = "~/.config/nvim/lua/tucker/themes", -- Path to the directory where your theme resides
    priority = 1000, -- Ensure it's loaded early
    config = function()
        -- Load and apply the local theme
        local currenttheme = require("tucker.themes.current-theme")
        currenttheme.apply()
    end,
}
