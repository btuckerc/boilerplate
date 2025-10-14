-- LSP configuration, formatting, and language servers
-- Uses native vim.lsp.config (Neovim 0.11+) with mise-managed LSP servers
-- LSP servers are installed via mise instead of Mason for unified tool management

return {
    -- Native LSP configuration (Neovim 0.11+)
    {
        "neovim/nvim-lspconfig",
        event = { "BufReadPre", "BufNewFile" },
        config = function()
            -- All LSP servers are installed via mise and available in PATH
            -- See ~/.config/mise/config.toml for LSP installation
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
            -- All commands are installed via mise and available in PATH
            vim.lsp.config("lua_ls", {
                cmd = { "lua-language-server" },
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
                cmd = { "typescript-language-server", "--stdio" },
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
                cmd = { "pyright-langserver", "--stdio" },
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
                cmd = { "gopls" },
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
                cmd = { "rust-analyzer" },
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
                cmd = { "yaml-language-server", "--stdio" },
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
                cmd = { "vscode-json-language-server", "--stdio" },
                settings = {
                    json = {
                        schemas = require("schemastore").json.schemas(),
                        validate = { enable = true },
                    },
                },
            })

            -- Basic configs for other servers
            vim.lsp.config("terraformls", {
                cmd = { "terraform-ls", "serve" },
            })

            vim.lsp.config("bashls", {
                cmd = { "bash-language-server", "start" },
            })

            vim.lsp.config("dockerls", {
                cmd = { "docker-langserver", "--stdio" },
            })

            -- Enable all configured LSP servers
            -- Servers are automatically started when opening matching filetypes
            vim.lsp.enable({
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
            })
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