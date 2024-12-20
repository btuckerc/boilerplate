return {
    "williamboman/mason.nvim",
    dependencies = {
        "williamboman/mason-lspconfig.nvim",
    },
    config = function()
        local mason = require("mason")
        local mason_lspconfig = require("mason-lspconfig")

        -- Enable mason and configure icons
        mason.setup({
            ui = {
                icons = {
                    package_installed = "✓",
                    package_pending = "➜",
                    package_uninstalled = "✗",
                },
            },
        })

        -- Configure LSP servers to install
        mason_lspconfig.setup({
            ensure_installed = {
                "lua_ls",
                "rust_analyzer",
                "gopls",
                "zls",
                "ts_ls",
                "html",
                "cssls",
                "tailwindcss",
                "svelte",
                "graphql",
                "emmet_ls",
                "prismals",
                "pyright",
            },
            automatic_installation = true,
            handlers = {
                ["lua_ls"] = function()
                    require("lspconfig").lua_ls.setup({
                        settings = {
                            Lua = {
                                runtime = { version = "LuaJIT" },
                                diagnostics = {
                                    globals = { "vim" },
                                },
                                workspace = {
                                    library = vim.api.nvim_get_runtime_file("", true),
                                    checkThirdParty = false,
                                },
                                telemetry = { enable = false },
                            },
                        },
                    })
                end,
            },
        })

        -- Install other tools (linters, formatters, debuggers)
        local other_tools = {
            "pylint",    -- python linter
            "eslint_d", -- javascript linter
        }

        for _, tool in ipairs(other_tools) do
            local package = require("mason-registry").get_package(tool)
            if not package:is_installed() then
                package:install()
            end
        end
    end,
}
