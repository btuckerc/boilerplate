return {
  "nvim-telescope/telescope.nvim",
  cmd = "Telescope",
  branch = "0.1.x",
  dependencies = {
    "nvim-lua/plenary.nvim",
    { "nvim-telescope/telescope-fzf-native.nvim", build = "make" },
    "nvim-telescope/telescope-ui-select.nvim",
    "nvim-tree/nvim-web-devicons",
  },
  config = function()
    local telescope = require("telescope")
    local actions = require("telescope.actions")
    local keymap = vim.keymap -- for conciseness
    local builtin = require("telescope.builtin")

    telescope.setup({
      defaults = {
        mappings = {
          i = {
            ["<C-k>"] = actions.move_selection_previous,
            ["<C-j>"] = actions.move_selection_next,
            ["<C-q>"] = actions.send_selected_to_qflist + actions.open_qflist,
            ["<C-x>"] = actions.delete_buffer,
          },
          n = {
            ["<C-k>"] = actions.move_selection_previous,
            ["<C-j>"] = actions.move_selection_next,
            ["<C-q>"] = actions.send_selected_to_qflist + actions.open_qflist,
            ["<C-x>"] = actions.delete_buffer,
          },
        },
        layout_strategy = "flex",
        layout_config = {
          flex = {
            flip_columns = 120,
          },
        },
        scroll_strategy = "cycle",
        sorting_strategy = "ascending",
        prompt_prefix = "🔍 ",
        selection_caret = "➤ ",
        entry_prefix = "  ",
        initial_mode = "insert",
        path_display = { "truncate" },
        winblend = 0,
        border = true,
        borderchars = { "─", "│", "─", "│", "╭", "╮", "╯", "╰" },
        color_devicons = true,
        set_env = { ["COLORTERM"] = "truecolor" },
      },
      pickers = {
        find_files = {
          hidden = true,
          no_ignore = false,
          follow = true,
        },
        live_grep = {
          additional_args = function()
            return { "--hidden" }
          end,
        },
      },
      extensions = {
        fzf = {
          fuzzy = true,
          override_generic_sorter = true,
          override_file_sorter = true,
          case_mode = "smart_case",
        },
        ["ui-select"] = {
          require("telescope.themes").get_dropdown(),
        },
      },
    })

    -- Load extensions
    pcall(require("telescope").load_extension, "fzf")
    pcall(require("telescope").load_extension, "ui-select")

    -- Key mappings
    local set = vim.keymap.set
    local opts = { noremap = true, silent = true }

    -- Find existing buffers
    set("n", "<leader><leader>", builtin.buffers, { desc = "Find existing buffers" })

    -- Find files
    set("n", "<leader>ff", builtin.find_files, { desc = "Find files" })
    set("n", "<leader>fg", builtin.git_files, { desc = "Find files in Git" })
    set("n", "<leader>fw", builtin.live_grep, { desc = "Live grep" })
    set("n", "<leader>fc", builtin.grep_string, { desc = "Find current word" })
    set("n", "<leader>fr", builtin.oldfiles, { desc = "Find recent files" })
    set("n", "<leader>/", builtin.current_buffer_fuzzy_find, { desc = "Fuzzy find in current buffer" })

    -- Find help tags
    set("n", "<leader>fh", builtin.help_tags, { desc = "Find help tags" })

    -- Find Neovim config files
    set("n", "<leader>fn", function()
      builtin.find_files({ cwd = vim.fn.stdpath("config") })
    end, { desc = "Find Neovim config files" })

    -- Find config files
    set("n", "<leader>f.", function()
      builtin.find_files({ cwd = vim.fn.expand("~/.config") })
    end, { desc = "Find config files" })
  end,
}
