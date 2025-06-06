return {
  "folke/which-key.nvim",
  event = "VeryLazy",
  opts = {
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
      group = "", -- Use a nicer icon for groups
    },
    win = {
      no_overlap = true,
      height = { min = 4, max = 25 },
      title = true,
      title_pos = "center",
    },
    layout = {
      height = { min = 4, max = 25 },
      width = { min = 20, max = 50 },
      spacing = 3,
      align = "left",
    },
    triggers = { "<leader>" },
  },
  config = function(_, opts)
    local which_key = require("which-key")
    which_key.setup(opts)

    -- Define keymap groups
    which_key.add({
      { "<leader>b", group = "+buffer" },
      { "<leader>c", group = "+code" },
      { "<leader>d", group = "+diagnostics" },
      { "<leader>e", group = "+explorer" },
      { "<leader>f", group = "+find" },
      { "<leader>g", group = "+git" },
      { "<leader>h", group = "+harpoon" },
      { "<leader>l", group = "+lsp" },
      { "<leader>o", group = "+obsidian" },
      { "<leader>p", group = "+plugin" },
      { "<leader>s", group = "+session" },
      { "<leader>t", group = "+tab" },
      { "<leader>w", group = "+window" },
      { "<leader>x", group = "+execute" },
    })
  end,
}
