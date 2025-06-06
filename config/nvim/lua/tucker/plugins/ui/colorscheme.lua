return {
  dir = "~/.config/nvim/lua/tucker/themes", -- Path to the directory where your theme resides
  priority = 1000, -- Ensure it's loaded early
  config = function()
    -- Load the current theme
    local currenttheme = require("tucker.themes.current-theme")

    -- Apply the theme with transparency enabled
    currenttheme.apply(true)
  end,
}
