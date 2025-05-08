return {
  "folke/which-key.nvim",
  event = "VeryLazy",
  init = function()
    vim.o.timeout = true
    vim.o.timeoutlen = 500
  end,
  opts = {
    defaults = {
      ["<leader>s"] = { name = "+session" },
    },
  },
  config = function()
    local status_ok, which_key = pcall(require, "which-key")
    if not status_ok then
      return
    end

    -- Configuration settings from the online example
    local setup = {
      plugins = {
        marks = true,
        registers = true,
        spelling = {
          enabled = true,
          suggestions = 20,
        },
        presets = {
          operators = false,
          motions = true,
          text_objects = true,
          windows = true,
          nav = true,
          z = true,
          g = true,
        },
      },
      icons = {
        breadcrumb = "»",
        separator = "➜",
        group = "+",
      },
      win = {
        no_overlap = true,
        -- width = 1,
        height = { min = 4, max = 25 },
        col = 0,
        row = math.huge,
        -- border = "rounded",
        -- padding = { 1, 2 },
        title = true,
        title_pos = "center",
        -- zindex = 1000,
        -- winblend = 90,
      },
      layout = {
        height = { min = 4, max = 25 },
        width = { min = 20, max = 50 },
        spacing = 3,
        align = "left",
      },
      show_help = true,
    }

    -- Apply the setup and mappings
    which_key.setup(setup)
  end,
}
