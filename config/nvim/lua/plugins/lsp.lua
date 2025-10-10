-- LSP configuration, formatting, and language servers
-- Uses native vim.lsp.config (Neovim 0.11+) for cleaner setup

return {
    -- Mason for LSP server management
    {
        "williamboman/mason.nvim",
        cmd = "Mason",
        build = ":MasonUpdate",
        config = function()
            require("mason").setup({
                ui = {
                    border = "rounded",
                },
            })
        end,
    },

    -- Mason LSP integration
    {
        "williamboman/mason-lspconfig.nvim",
        event = { "BufReadPre", "BufNewFile" },
        dependencies = { "williamboman/mason.nvim" },
        config = function()
            require("mason-lspconfig").setup({
                ensure_installed = {
                    "lua_ls",
                    "ts_ls",
                    "pyright",
                    "gopls",
                    "rust_analyzer",
                    "terraformls",
                    "yamlls",
                    "jsonls",
                    "bashls",
                    "dockerls",
                },
            })

            -- Native LSP configuration
            local capabilities = vim.lsp.protocol.make_client_capabilities()

            -- Enable native completion
            vim.lsp.completion.enable()

            -- Performance optimization: Set large file threshold for LSP
            vim.lsp.buf.large_file_threshold = 1024 * 1024  -- 1MB threshold

            -- Global LSP performance settings
            vim.diagnostic.config({
                update_in_insert = false,    -- Don't show diagnostics while typing
                severity_sort = true,
                float = {
                    focusable = false,
                    style = "minimal",
                    border = "rounded",
                    source = "always",
                    header = "",
                    prefix = "",
                },
                signs = {
                    priority = 8,  -- Lower priority for less frequent updates
                },
            })

            -- LSP keymaps
            vim.api.nvim_create_autocmd("LspAttach", {
                callback = function(event)
                    local map = function(keys, func, desc)
                        vim.keymap.set("n", keys, func, { buffer = event.buf, desc = "LSP: " .. desc })
                    end

                    map("gd", vim.lsp.buf.definition, "Go to definition")
                    map("gr", vim.lsp.buf.references, "Go to references")
                    map("gI", vim.lsp.buf.implementation, "Go to implementation")
                    map("gD", vim.lsp.buf.type_definition, "Type definition")
                    map("<leader>rn", vim.lsp.buf.rename, "Rename")
                    map("<leader>ca", vim.lsp.buf.code_action, "Code action")
                    map("K", vim.lsp.buf.hover, "Hover documentation")

                    -- Diagnostics
                    map("[d", vim.diagnostic.goto_prev, "Previous diagnostic")
                    map("]d", vim.diagnostic.goto_next, "Next diagnostic")
                    map("<leader>df", vim.diagnostic.open_float, "Show diagnostic")
                end,
            })

            -- Configure individual LSP servers using native vim.lsp.config
            vim.lsp.config("lua_ls", {
                settings = {
                    Lua = {
                        runtime = { version = "LuaJIT" },
                        workspace = {
                            checkThirdParty = false,
                            library = {
                                "${3rd}/luv/library",
                                unpack(vim.api.nvim_get_runtime_file("", true)),
                            },
                        },
                        telemetry = { enable = false },
                        diagnostics = { disable = { "missing-fields" } },
                    },
                },
            })

            vim.lsp.config("ts_ls", {
                settings = {
                    typescript = {
                        inlayHints = {
                            includeInlayParameterNameHints = "all",
                            includeInlayParameterNameHintsWhenArgumentMatchesName = false,
                            includeInlayFunctionParameterTypeHints = true,
                            includeInlayVariableTypeHints = true,
                            includeInlayPropertyDeclarationTypeHints = true,
                            includeInlayFunctionLikeReturnTypeHints = true,
                            includeInlayEnumMemberValueHints = true,
                        },
                    },
                },
            })

            vim.lsp.config("pyright", {
                settings = {
                    python = {
                        analysis = {
                            autoSearchPaths = true,
                            diagnosticMode = "workspace",
                            useLibraryCodeForTypes = true,
                        },
                    },
                },
            })

            vim.lsp.config("gopls", {
                settings = {
                    gopls = {
                        analyses = {
                            unusedparams = true,
                        },
                        staticcheck = true,
                        gofumpt = true,
                    },
                },
            })

            vim.lsp.config("rust_analyzer", {
                settings = {
                    ["rust-analyzer"] = {
                        cargo = {
                            allFeatures = true,
                        },
                        checkOnSave = {
                            command = "clippy",
                        },
                    },
                },
            })

            vim.lsp.config("yamlls", {
                settings = {
                    yaml = {
                        schemas = {
                            ["https://json.schemastore.org/github-workflow.json"] = "/.github/workflows/*",
                            ["https://json.schemastore.org/kustomization.json"] = "kustomization.yaml",
                            ["https://raw.githubusercontent.com/compose-spec/compose-spec/master/schema/compose-spec.json"] = "docker-compose*.yml",
                        },
                    },
                },
            })

            vim.lsp.config("jsonls", {
                settings = {
                    json = {
                        schemas = require("schemastore").json.schemas(),
                        validate = { enable = true },
                    },
                },
            })

            -- Basic configs for other servers
            local basic_servers = { "terraformls", "bashls", "dockerls" }
            for _, server in ipairs(basic_servers) do
                vim.lsp.config(server, {})
            end
        end,
    },

    -- JSON schemas
    {
        "b0o/SchemaStore.nvim",
        ft = { "json", "jsonc" },
    },

    -- Formatting
    {
        "stevearc/conform.nvim",
        event = { "BufWritePre" },
        cmd = { "ConformInfo" },
        keys = {
            {
                "<leader>f",
                function()
                    require("conform").format({ async = true, lsp_fallback = true })
                end,
                mode = "",
                desc = "Format buffer",
            },
        },
        config = function()
            require("conform").setup({
                formatters_by_ft = {
                    lua = { "stylua" },
                    python = { "black" },
                    javascript = { "prettier" },
                    typescript = { "prettier" },
                    json = { "prettier" },
                    yaml = { "prettier" },
                    markdown = { "prettier" },
                    go = { "gofumpt", "goimports" },
                    rust = { "rustfmt" },
                    terraform = { "terraform_fmt" },
                    sh = { "shfmt" },
                },
                format_on_save = {
                    timeout_ms = 500,
                    lsp_fallback = true,
                },
            })
        end,
    },
}