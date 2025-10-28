-- AI assistance and productivity tools

return {
  -- AI assistance (Copilot)
  {
    "zbirenbaum/copilot.lua",
    cmd = "Copilot",
    event = "InsertEnter",
    config = function()
      require("copilot").setup({
        suggestion = {
          enabled = true,
          auto_trigger = true,
          keymap = {
            accept = "<C-y>",
            accept_word = "<C-Right>",
            accept_line = "<C-y>",
            next = "<M-]>",
            prev = "<M-p>",
            dismiss = "<C-]>",
          },
        },
        panel = { enabled = false },
      })
    end,
  },
}
