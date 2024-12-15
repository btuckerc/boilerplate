return {
    "yetone/avante.nvim",
    lazy = true,  -- Load lazily
    cmd = { "Avante" },  -- Trigger on command
    ft = { "lua", "python", "javascript" },  -- Trigger for these filetypes
    opts = {
        theme = "dark",  -- Set to 'light' if you prefer
        auto_apply = false,  -- Manually apply changes
        provider = "claude",
        claude = {
            endpoint = "https://api.anthropic.com",
            model = "claude-3-5-sonnet-20241022",
            temperature = 0,
            max_tokens = 4096,
        },
        behaviour = {
            auto_suggestions = true,
            minimize_diff = true,
        },
        mappings = {
            suggestion = {
                accept = "<C-l>",
                next = "<M-]>",
                prev = "<M-[>",
            },
        },
        windows = {
            position = "right",
            width = 30,
        },
        paths = {
            templates = vim.fn.stdpath("config") .. "/lua/tucker/plugins/avante/templates",
        },
    },
    dependencies = {
        "MunifTanjim/nui.nvim",
        "hrsh7th/nvim-cmp",  -- Autocompletion
        "nvim-lua/plenary.nvim",  -- Dependency for Telescope and more
        "nvim-tree/nvim-web-devicons",  -- Icons
    },
}

