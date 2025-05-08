return {
  {
    "stevearc/oil.nvim",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    config = function()
      require("oil").setup({
        columns = { "icon" },
        keymaps = {
          ["<C-h>"] = false,
          ["<M-h>"] = "actions.select_split",
        },
        view_options = {
          show_hidden = true,
        },
      })

      -- Key mappings
      local set = vim.keymap.set
      local opts = { noremap = true, silent = true }

      -- Open parent directory in current window
      set("n", "<leader>e", "<CMD>Oil<CR>", { desc = "Open parent directory" })

      -- Open parent directory in floating window
      set("n", "<leader>ef", require("oil").toggle_float, { desc = "Open parent directory in floating window" })
    end,
  },
}
