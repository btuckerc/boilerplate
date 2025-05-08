return {
  "ThePrimeagen/git-worktree.nvim",
  keys = {
    { "<leader>gwt", "<cmd>lua require('telescope').extensions.git_worktree.git_worktrees()<CR>", desc = "List git worktrees" },
    { "<leader>gwc", "<cmd>lua require('telescope').extensions.git_worktree.create_git_worktree()<CR>", desc = "Create git worktree" },
  },
  config = function()
    require("git-worktree").setup({
      -- Default configuration
    })
  end,
}
