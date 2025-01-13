return {
  {
    "kdheepak/lazygit.nvim",
    keys = {
      { "<leader>gg", "<cmd>LazyGit<CR>", desc = "Open LazyGit" },
      { "<leader>gl", "<cmd>LazyGitCurrentFile<CR>", desc = "Open LazyGit for current file" },
    },
    config = function()
      vim.api.nvim_set_var('lazygit_floating_window_winblend', 0)
      vim.api.nvim_set_var('lazygit_floating_window_scaling_factor', 0.9)
      vim.api.nvim_set_var('lazygit_use_custom_config_file_path', 0)
      vim.api.nvim_set_var('lazygit_config_file_path', '')
    end,
    cmd = { "LazyGit", "LazyGitCurrentFile" },
  },
  {
    "lewis6991/gitsigns.nvim",
    keys = function()
      local gs = require("gitsigns")
      return {
        -- Navigation
        { "]h", function() gs.nav_hunk('next') end, desc = "Next Git hunk" },
        { "[h", function() gs.nav_hunk('prev') end, desc = "Previous Git hunk" },
        -- Actions
        { "<leader>gs", gs.stage_hunk, desc = "Stage hunk" },
        { "<leader>gr", gs.reset_hunk, desc = "Reset hunk" },
        { "<leader>gu", gs.undo_stage_hunk, desc = "Undo stage hunk" },
        { "<leader>gp", gs.preview_hunk, desc = "Preview hunk" },
        { "<leader>gb", gs.blame_line, desc = "Blame line" },
        -- Text object
        { "ih", gs.select_hunk, mode = { "o", "x" }, desc = "Select hunk" },
      }
    end,
    config = function()
      require("gitsigns").setup({
        signs = {
          add = { text = "│" },
          change = { text = "│" },
          delete = { text = "_" },
          topdelete = { text = "‾" },
          changedelete = { text = "~" },
          untracked = { text = "┆" },
        },
        signcolumn = true,
        current_line_blame = false, -- Toggle with `:Gitsigns toggle_current_line_blame`
        current_line_blame_opts = {
          virt_text = true,
          virt_text_pos = "eol", -- 'eol' | 'overlay' | 'right_align'
          delay = 1000,
          ignore_whitespace = false,
        },
      })
    end,
  }
}
