return {
  {
    "stevearc/oil.nvim",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    config = function()
      require("oil").setup({
        default_file_explorer = true,
        columns = { "icon", "permissions" },
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

      -- Open parent directory in current window
      set("n", "<leader>e", "<CMD>Oil<CR>", { desc = "Open parent directory" })

      -- Open parent directory in floating window
      set("n", "<leader>ef", require("oil").toggle_float, { desc = "Open parent directory in floating window" })

      -- Open parent directory in vertical split
      set("n", "<leader>ev", "<CMD>vsplit | Oil<CR>", { desc = "Open parent directory in vertical split" })
    end,
  },
}
