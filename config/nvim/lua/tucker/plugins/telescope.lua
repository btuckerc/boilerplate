return {
    "nvim-telescope/telescope.nvim",
    branch = "0.1.x",
    dependencies = {
        "nvim-lua/plenary.nvim",
        { "nvim-telescope/telescope-fzf-native.nvim", build = "make" },
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
                    fzf = {}
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
        telescope.load_extension("fzf")

        -- File and text finding
        keymap.set("n", "<leader>ff", "<cmd>Telescope find_files<cr>", { desc = "Find files" })
        keymap.set("n", "<leader>fg", "<cmd>Telescope git_files<cr>", { desc = "Find git files" })
        keymap.set("n", "<leader>fr", "<cmd>Telescope oldfiles<cr>", { desc = "Find recent files" })
        keymap.set("n", "<leader>fs", "<cmd>Telescope live_grep<cr>", { desc = "Search string in cwd" })
        keymap.set("n", "<leader>fw", "<cmd>Telescope grep_string<cr>", { desc = "Search word under cursor" })
        keymap.set("n", "<leader>fh", "<cmd>Telescope help_tags<cr>", { desc = "Search help tags" })
    end,
}
