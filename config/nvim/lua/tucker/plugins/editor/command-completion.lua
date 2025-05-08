return {
  {
    "gelguy/wilder.nvim",
    build = ":UpdateRemotePlugins",
    dependencies = {
      "nvim-treesitter/nvim-treesitter",
      "romgrk/fzy-lua-native",
    },
    config = function()
      local wilder = require("wilder")
      wilder.setup({ modes = { ":", "/", "?" } })

      -- Enable fuzzy matching
      wilder.set_option("use_python_remote_plugin", 0)
      wilder.set_option("pipeline", {
        wilder.branch(
          wilder.cmdline_pipeline({
            fuzzy = 1,
            fuzzy_filter = wilder.lua_fzy_filter(),
          }),
          wilder.vim_search_pipeline()
        ),
      })

      -- Configure the popup menu
      wilder.set_option("renderer", wilder.popupmenu_renderer(
        wilder.popupmenu_border_theme({
          highlights = {
            border = "Normal",
          },
          border = "rounded",
          highlighter = wilder.lua_fzy_highlighter(),
          left = { " ", wilder.popupmenu_devicons() },
          right = { " ", wilder.popupmenu_scrollbar() },
        })
      ))
    end,
  },
}
