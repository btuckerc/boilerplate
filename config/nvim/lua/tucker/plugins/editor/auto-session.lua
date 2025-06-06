return {
    "rmagatti/auto-session",
    enabled = true,
    dependencies = {
        "folke/which-key.nvim",
    },
    config = function()
        local auto_session = require("auto-session")

        auto_session.setup({
            auto_restore_enabled = false, -- Don't automatically restore
            auto_save_enabled = true, -- But do automatically save sessions
            auto_session_suppress_dirs = {
                "~/",
                "~/Documents",
                "~/Downloads",
                "~/Desktop/",
                -- Add any other directories you don't want auto-session to save
            },
            log_level = "error",
            auto_session_use_git_branch = true, -- Use git branch names in session names
            pre_save_cmds = { "tabdo NvimTreeClose" }, -- Close file explorer before saving session
        })

        -- Key mappings for manual session management
        local keymap = vim.keymap
        keymap.set("n", "<leader>ss", "<cmd>SessionSave<CR>", { desc = "Save session" })
        keymap.set("n", "<leader>sr", "<cmd>SessionRestore<CR>", { desc = "Restore session" })
        keymap.set("n", "<leader>sd", "<cmd>SessionDelete<CR>", { desc = "Delete session" })
        keymap.set("n", "<leader>sf", "<cmd>Autosession search<CR>", { desc = "Find session" })
    end,
}
