return {
  {
  "kdheepak/lazygit.nvim",
  keys = {
    { "<leader>gg", "<cmd>LazyGit<CR>", desc = "Open LazyGit" },
    { "<leader>gl", "<cmd>LazyGitCurrentFile<CR>", desc = "Open LazyGit for current file" },
  },
  config = function()
    vim.g.lazygit_floating_window_winblend = 0
    vim.g.lazygit_floating_window_scaling_factor = 0.9
    vim.g.lazygit_use_custom_config_file_path = 0
    vim.g.lazygit_config_file_path = ""
  end,
  cmd = { "LazyGit", "LazyGitCurrentFile" },
  },
  {
    "lewis6991/gitsigns.nvim",
    keys = {

    },
    config = function()
      require("gitsigns").setup()
    end,
  }
}
