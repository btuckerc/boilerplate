return {
    "WhoIsSethDaniel/mason-tool-installer.nvim",
    dependencies = { "williamboman/mason.nvim" },
    config = function()
        require("mason-tool-installer").setup({
            ensure_installed = {
                "pylint",
                "eslint_d",
                -- Add other tools you need here
            },
            -- Optional settings
            auto_update = false,
            run_on_start = true,
        })
    end,
}

