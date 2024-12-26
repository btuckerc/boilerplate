return {
  dir = "~/.config/nvim/lua/tucker/themes", -- Path to the directory where your theme resides
  priority = 1000, -- Ensure it's loaded early
  config = function()
    -- Load the current theme
    local currenttheme = require("tucker.themes.current-theme")

    -- Add transparency logic
    local transparent = true -- Set to true to enable transparency

    -- Define colors based on transparency settings
    local colors = {
      bg = transparent and "NONE" or "#011628",
      bg_dark = transparent and "NONE" or "#011423",
    }

    -- Set up global variables or overrides for the theme
    vim.g.currenttheme_transparent = transparent
    vim.g.currenttheme_colors = colors

    -- Apply the theme using its existing API
    currenttheme.apply({
      transparent = transparent,
      colors = colors,
    })
  end,
}
