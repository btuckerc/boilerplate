return {
  "neovim/nvim-lspconfig",
  event = { "BufReadPre", "BufNewFile" },
  dependencies = {
    "hrsh7th/nvim-cmp",
    "williamboman/mason.nvim",
    "williamboman/mason-lspconfig.nvim",
    "WhoIsSethDaniel/mason-tool-installer.nvim",
    {
      "folke/lazydev.nvim",
      ft = "lua",
      opts = {},
    },
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
    { "https://git.sr.ht/~whynothugo/lsp_lines.nvim" },
    "stevearc/conform.nvim",
    "b0o/SchemaStore.nvim",
  },

  config = function()
    -- Local requires for better organization
    local conform = require("conform")
    local fidget = require("fidget")
    local lspconfig = require("lspconfig")
    local telescope_builtin = require('telescope.builtin')

    local extend = function(name, key, values)
      local mod = require(string.format("lspconfig.configs.%s", name))
      local default = mod.default_config
      local keys = vim.split(key, ".", { plain = true })
      while #keys > 0 do
        local item = table.remove(keys, 1)
        default = default[item]
      end

      if vim.islist(default) then
        for _, value in ipairs(default) do
          table.insert(values, value)
        end
      else
        for item, value in pairs(default) do
          if not vim.tbl_contains(values, item) then
            values[item] = value
          end
        end
      end
      return values
    end

    -- Setup formatters
    conform.setup({
      formatters_by_ft = {
        lua = { "stylua" },
        go = { "gofmt", "goimports" },
        python = { "isort", "black" },
        rust = { "rustfmt" },
        javascript = { "prettier" },
        typescript = { "prettier" },
        json = { "prettier" },
        yaml = { "prettier" },
        markdown = { "prettier" },
      }
    })

    -- Get LSP capabilities from nvim-cmp
    local capabilities = require('cmp_nvim_lsp').default_capabilities()

    -- Setup Fidget for LSP progress
    fidget.setup({})

    -- Unified LSP keymap setup
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

      -- Additional mappings
      map("<space>cr", vim.lsp.buf.rename, "Code Rename")
      map("<space>ca", vim.lsp.buf.code_action, "Code Action")
      map("<space>wd", telescope_builtin.lsp_document_symbols, "Workspace Document Symbols")
      map("gT", vim.lsp.buf.type_definition, "Goto Type Definition")
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

    -- Server-specific settings for disabling features
    local disable_semantic_tokens = {
      lua = true,
    }

    -- Server-specific configurations
    local servers = {
      bashls = {},
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
      rust_analyzer = {
        settings = {
          ['rust-analyzer'] = {
            checkOnSave = {
              command = "clippy",
            },
          },
        },
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
        on_attach = function(client, bufnr)
          vim.g.zig_fmt_parse_errors = 0
          vim.g.zig_fmt_autosave = 0
        end,
      },
      ts_ls = {},
      tailwindcss = {
        init_options = {
          userLanguages = {
            templ = "html",
          }
        }
      },
      gopls = {
        settings = {
          gopls = {
            hints = {
              assignVariableTypes = true,
              compositeLiteralFields = true,
              compositeLiteralTypes = true,
              constantValues = true,
              functionTypeParameters = true,
              parameterNames = true,
              rangeVariableTypes = true,
            },
          },
        },
      },
      pyright = {},
      jsonls = {
        settings = {
          json = {
            schemas = require("schemastore").json.schemas(),
            validate = { enable = true },
          },
        },
      },
      yamlls = {
        settings = {
          yaml = {
            schemaStore = {
              enable = true,
              url = "https://www.schemastore.org/api/json/catalog.json",
            },
            schemas = require("schemastore").yaml.schemas(),
          },
        },
      },
      clangd = {},
    }

    -- LSP attach configuration
    vim.api.nvim_create_autocmd('LspAttach', {
      group = vim.api.nvim_create_augroup('user-lsp-attach', { clear = true }),
      callback = function(event)
        local bufnr = event.buf
        local client = vim.lsp.get_client_by_id(event.data.client_id)
        assert(client, "must have valid client")

        -- Setup keymaps and features
        setup_lsp_keymaps(event)
        setup_document_highlight(client, bufnr)

        -- Set local omnifunc
        vim.bo[bufnr].omnifunc = 'v:lua.vim.lsp.omnifunc'

        -- Disable semantic tokens for specific filetypes
        local filetype = vim.bo[bufnr].filetype
        if disable_semantic_tokens[filetype] then
          client.server_capabilities.semanticTokensProvider = nil
        end

        -- Override server capabilities if needed
        local server_settings = servers[client.name]
        if type(server_settings) == "table" and server_settings.server_capabilities then
          for k, v in pairs(server_settings.server_capabilities) do
            if v == vim.NIL then v = nil end
            client.server_capabilities[k] = v
          end
        end
      end,
    })

    -- Configure diagnostics
    vim.diagnostic.config({
      virtual_text = false,
      signs = true,
      underline = true,
      update_in_insert = false,
      severity_sort = true,
      float = {
        focusable = false,
        style = "minimal",
        border = "rounded",
        source = "always",
        header = "",
        prefix = "",
      },
    })

    -- Let lsp_lines handle diagnostic signs
    require("lsp_lines").setup()
    vim.diagnostic.config { virtual_text = true, virtual_lines = false }

    vim.keymap.set("", "<leader>l", function()
      local config = vim.diagnostic.config() or {}
      if config.virtual_text then
        vim.diagnostic.config { virtual_text = false, virtual_lines = true }
      else
        vim.diagnostic.config { virtual_text = true, virtual_lines = false }
      end
    end, { desc = "Toggle lsp_lines" })

    -- Setup servers with mason-lspconfig
    local mason_lspconfig = require("mason-lspconfig")

    mason_lspconfig.setup({
      ensure_installed = vim.tbl_keys(servers)
    })

    for server_name, server_config in pairs(servers) do
      server_config.capabilities = capabilities
      lspconfig[server_name].setup(server_config)
    end
  end
}
