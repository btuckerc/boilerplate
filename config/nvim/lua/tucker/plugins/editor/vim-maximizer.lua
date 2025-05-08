return {
  "szw/vim-maximizer",
  keys = {
    { "<leader>sm", "<cmd>MaximizerToggle<CR>", desc = "Maximize/minimize a split" },
  },
  config = function()
    vim.g.maximizer_set_default_mapping = 0
  end,
}
