return {
  {
    'NvChad/nvim-colorizer.lua',
    config = function()
      require('colorizer').setup({
        filetypes = { 'css', 'javascript', 'typescript', 'html', 'lua', 'python' },
        user_default_options = {
          RGB = true,        -- Enable #RGB hex codes
          RRGGBB = true,     -- Enable #RRGGBB hex codes
          names = true,      -- Enable "Name" codes like Blue
          RRGGBBAA = false,  -- Disable #RRGGBBAA hex codes
          rgb_fn = false,    -- Disable CSS rgb() and rgba() functions
          hsl_fn = false,    -- Disable CSS hsl() and hsla() functions
          css = false,       -- Disable all CSS features: rgb_fn, hsl_fn, names, RGB, RRGGBB
          css_fn = false,    -- Disable all CSS *functions*: rgb_fn, hsl_fn
          mode = 'background', -- Set the display mode: 'background', 'foreground', or 'virtualtext'
        },
        buftypes = {},
      })
    end,
  },
}
