return {
  "nvim-telescope/telescope.nvim",
  branch = "0.1.x",
  dependencies = {
    "nvim-lua/plenary.nvim",
    { "nvim-telescope/telescope-fzf-native.nvim", build = "make" },
    "nvim-telescope/telescope-smart-history.nvim",
    "nvim-telescope/telescope-ui-select.nvim",
    "nvim-tree/nvim-web-devicons",
  },
  config = function()
    local telescope = require("telescope")
    local actions = require("telescope.actions")
    local keymap = vim.keymap -- for conciseness

    telescope.setup({
      defaults = {
        pickers = {
          find_files = {
            theme = "ivy"
          }
        },
        extensions = {
          wrap_results = true,
          fzf = {},
          ["ui-select"] = {
            require("telescope.themes").get_dropdown {},
          },
        },
        path_display = { "smart" },
        mappings = {
          i = {
            ["<C-k>"] = actions.move_selection_previous,
            ["<C-j>"] = actions.move_selection_next,
            ["<C-q>"] = actions.send_selected_to_qflist + actions.open_qflist,
          },
        },
      },
    })

    -- Load extensions
    pcall(require("telescope").load_extension, "fzf")
    pcall(require("telescope").load_extension, "smart_history")
    pcall(require("telescope").load_extension, "ui-select")

    local builtin = require("telescope.builtin")

    -- File and text finding
    keymap.set("n", "<leader><leader>", builtin.buffers, { desc = "[ ] Find existing buffers" })
    keymap.set("n", "<space>ff", builtin.find_files, { desc = "[F]ind [F]ile" })
    keymap.set("n", "<space>ft", builtin.git_files, { desc = "[F]ind in [T]ree" })
    keymap.set("n", "<space>fh", builtin.help_tags, { desc = "[F]ind in [H]elp tags" })
    keymap.set("n", "<space>fd", builtin.live_grep, { desc = "[F]ind in cw[D]" })
    keymap.set("n", "<space>fs", builtin.grep_string, { desc = "[F]ind by [S]earch word under cursor" })
    keymap.set("n", "<space>fr", builtin.oldfiles, { desc = "[F]ind [R]ecent files" })
    keymap.set("n", "<space>/", builtin.current_buffer_fuzzy_find)

    keymap.set("n", "<leader>fn", function()
      builtin.find_files { cwd = vim.fn.stdpath("config") }
    end, { desc = "[F]ind [N]eovim file" })
  end,
}
