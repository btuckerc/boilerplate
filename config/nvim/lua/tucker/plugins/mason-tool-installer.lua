return {
    "WhoIsSethDaniel/mason-tool-installer.nvim",
    dependencies = {
        "williamboman/mason.nvim",
        "williamboman/mason-lspconfig.nvim",
    },
    config = function()
        require("mason").setup({
            ui = {
                icons = {
                    package_installed = "✓",
                    package_pending = "➜",
                    package_uninstalled = "✗",
                },
                border = "rounded",
                keymaps = {
                    toggle_server_expand = "<CR>",
                    install_server = "i",
                    update_server = "u",
                    uninstall_server = "x",
                },
            },
            max_concurrent_installers = 10,
        })

        require("mason-lspconfig").setup({
            ensure_installed = {},
            automatic_installation = true,
        })

        require("mason-tool-installer").setup({
            ensure_installed = {
                "pylint",
                "gopls",
                "rust_analyzer",
            },
            auto_update = false,
            run_on_start = true,
            start_delay = 3000, -- 3 second delay
        })
    end,
}
