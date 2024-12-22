return {
    "neovim/nvim-lspconfig",
    dependencies = {
        "saghen/blink.cmp",
        "stevearc/conform.nvim",
        "williamboman/mason.nvim",
        "williamboman/mason-lspconfig.nvim",
        "hrsh7th/cmp-nvim-lsp",
        "hrsh7th/cmp-buffer",
        "hrsh7th/cmp-path",
        "hrsh7th/cmp-cmdline",
        "hrsh7th/nvim-cmp",
        "L3MON4D3/LuaSnip",
        "saadparwaiz1/cmp_luasnip",
        {
            'j-hui/fidget.nvim',
            tag = 'v1.4.0',
            opts = {
                progress = {
                    display = {
                        done_icon = '✓',
                    },
                },
                notification = {
                    window = {
                        winblend = 0,
                    },
                },
            },
        },
    },

    config = function()
        -- Local requires for better organization
        local conform = require("conform")
        local cmp = require('cmp')
        local fidget = require("fidget")
        local lspconfig = require("lspconfig")
        local telescope_builtin = require('telescope.builtin')

        -- Setup formatters
        conform.setup({
            formatters_by_ft = {
            }
        })

        -- Get LSP capabilities from blink
        local capabilities = require('blink.cmp').get_lsp_capabilities()

        -- Setup Fidget for LSP progress
        fidget.setup({})

        -- LSP server configurations
        local function setup_lsp_keymaps(event)
            local map = function(keys, func, desc)
                vim.keymap.set('n', keys, func, { buffer = event.buf, desc = 'LSP: ' .. desc })
            end

            -- Telescope-based mappings
            map('gd', telescope_builtin.lsp_definitions, '[G]oto [D]efinition')
            map('gr', telescope_builtin.lsp_references, '[G]oto [R]eferences')
            map('gI', telescope_builtin.lsp_implementations, '[G]oto [I]mplementation')
            map('<leader>lt', telescope_builtin.lsp_type_definitions, '[L]SP [T]ype Definition')
            map('<leader>ls', telescope_builtin.lsp_document_symbols, '[L]SP Document [S]ymbols')
            map('<leader>lS', telescope_builtin.lsp_dynamic_workspace_symbols, '[L]SP Workspace [S]ymbols')

            -- LSP buffer mappings
            map('<leader>lr', vim.lsp.buf.rename, '[L]SP [R]ename')
            map('<leader>la', vim.lsp.buf.code_action, '[L]SP Code [A]ction')
            map('K', vim.lsp.buf.hover, 'Hover Documentation')
            map('gD', vim.lsp.buf.declaration, '[G]oto [D]eclaration')
            map('<leader>wa', vim.lsp.buf.add_workspace_folder, '[W]orkspace [A]dd Folder')
            map('<leader>wr', vim.lsp.buf.remove_workspace_folder, '[W]orkspace [R]emove Folder')
            map('<leader>wl', function()
                print(vim.inspect(vim.lsp.buf.list_workspace_folders()))
            end, '[W]orkspace [L]ist Folders')
        end

        -- Setup document highlight
        local function setup_document_highlight(client, bufnr)
            if client.server_capabilities.documentHighlightProvider then
                local group = vim.api.nvim_create_augroup("lsp_document_highlight", { clear = true })
                vim.api.nvim_create_autocmd({ "CursorHold", "CursorHoldI" }, {
                    group = group,
                    buffer = bufnr,
                    callback = vim.lsp.buf.document_highlight,
                })
                vim.api.nvim_create_autocmd({ "CursorMoved", "CursorMovedI" }, {
                    group = group,
                    buffer = bufnr,
                    callback = vim.lsp.buf.clear_references,
                })
            end
        end

        -- LSP attach configuration
        vim.api.nvim_create_autocmd('LspAttach', {
            group = vim.api.nvim_create_augroup('lsp-attach', { clear = true }),
            callback = function(event)
                setup_lsp_keymaps(event)
                local client = vim.lsp.get_client_by_id(event.data.client_id)
                if client then
                    setup_document_highlight(client, event.buf)
                end
            end,
        })

        -- Configure diagnostics
        vim.diagnostic.config({
            float = {
                focusable = false,
                style = "minimal",
                border = "rounded",
                source = "always",
                header = "",
                prefix = "",
            },
        })

        -- Server-specific configurations
        local servers = {
            lua_ls = {
                settings = {
                    Lua = {
                        runtime = { version = "Lua 5.1" },
                        diagnostics = {
                            globals = { "bit", "vim", "it", "describe", "before_each", "after_each" },
                        }
                    }
                }
            },
            zls = {
                root_dir = lspconfig.util.root_pattern(".git", "build.zig", "zls.json"),
                settings = {
                    zls = {
                        enable_inlay_hints = true,
                        enable_snippets = true,
                        warn_style = true,
                    },
                },
                on_attach = function()
                    vim.g.zig_fmt_parse_errors = 0
                    vim.g.zig_fmt_autosave = 0
                end,
            },
        }

        -- Setup each LSP server
        for server, config in pairs(servers) do
            config.capabilities = capabilities
            lspconfig[server].setup(config)
        end
    end
}
