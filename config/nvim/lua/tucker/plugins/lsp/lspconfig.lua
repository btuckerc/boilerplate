return {
  "neovim/nvim-lspconfig",
  event = { "BufReadPre", "BufNewFile" },
  dependencies = {
    "saghen/blink.cmp",
    "stevearc/conform.nvim",
    "williamboman/mason.nvim",
    "williamboman/mason-lspconfig.nvim",
    "WhoIsSethDaniel/mason-tool-installer.nvim",
    "hrsh7th/cmp-nvim-lsp",
    "hrsh7th/cmp-buffer",
    "hrsh7th/cmp-path",
    "hrsh7th/cmp-cmdline",
    "hrsh7th/nvim-cmp",
    "L3MON4D3/LuaSnip",
    {
      -- `lazydev` configures Lua LSP for your Neovim config, runtime and plugins
      -- used for completion, annotations and signatures of Neovim apis
      "folke/lazydev.nvim",
      ft = "lua",
      opts = {},
    },
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
    { "https://git.sr.ht/~whynothugo/lsp_lines.nvim" },

    -- Autoformatting
    "stevearc/conform.nvim",

    -- Schema information
    "b0o/SchemaStore.nvim",
  },

  config = function()
    -- Local requires for better organization
    local conform = require("conform")
    local cmp = require('cmp')
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
      virtual_text = true,
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

    -- Define diagnostic signs
    local signs = { Error = " ", Warn = " ", Hint = " ", Info = " " }
    for type, icon in pairs(signs) do
      local hl = "DiagnosticSign" .. type
      vim.fn.sign_define(hl, { text = icon, texthl = hl, numhl = hl })
    end

    -- Server-specific configurations
    local servers = {
      bashls = true,
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
        cmd = { "rustup", "run", "stable", "rust-analyzer" },
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
        on_attach = function()
          vim.g.zig_fmt_parse_errors = 0
          vim.g.zig_fmt_autosave = 0
        end,
      },
      ts_ls = {},
      tailwindcss = {},
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
      pyright = true,
      jsonls = {
        server_capabilities = {
          documentFormattingProvider = false,
        },
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
              enable = false,
              url = "",
            },
            -- schemas = require("schemastore").yaml.schemas(),
          },
        },
      },
      clangd = {
        -- cmd = { "clangd", unpack(require("custom.clangd").flags) },
        -- TODO: Could include cmd, but not sure those were all relevant flags.
        --    looks like something i would have added while i was floundering
        init_options = { clangdFileStatus = true },

        filetypes = { "c" },
      },

      tailwindcss = {
        init_options = {
          userLanguages = {
            elixir = "phoenix-heex",
            eruby = "erb",
            heex = "phoenix-heex",
          },
        },
        filetypes = extend("tailwindcss", "filetypes", { "ocaml.mlx" }),
        settings = {
          tailwindCSS = {
            experimental = {
              classRegex = {
                [[class: "([^"]*)]],
                [[className="([^"]*)]],
              },
            },
            includeLanguages = extend("tailwindcss", "settings.tailwindCSS.includeLanguages", {
              ["ocaml.mlx"] = "html",
            }),
          },
        },
      },
    }

    local servers_to_install = vim.tbl_filter(function(key)
      local t = servers[key]
      if type(t) == "table" then
        return not t.manual_install
      else
        return t
      end
    end, vim.tbl_keys(servers))

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
    local ensure_installed = {
      "stylua",
      "lua_ls",
      "pylint",
      -- "tailwind-language-server",
    }

    vim.list_extend(ensure_installed, servers_to_install)
    require("mason-tool-installer").setup { ensure_installed = ensure_installed }

    for name, config in pairs(servers) do
      if config == true then
        config = {}
      end
      config = vim.tbl_deep_extend("force", {}, {
        capabilities = capabilities,
      }, config)

      lspconfig[name].setup(config)
    end

    local disable_semantic_tokens = {
      lua = true,
    }

    vim.api.nvim_create_autocmd("LspAttach", {
      callback = function(args)
        local bufnr = args.buf
        local client = assert(vim.lsp.get_client_by_id(args.data.client_id), "must have valid client")

        local settings = servers[client.name]
        if type(settings) ~= "table" then
          settings = {}
        end

        local builtin = require "telescope.builtin"

        vim.opt_local.omnifunc = "v:lua.vim.lsp.omnifunc"
        vim.keymap.set("n", "gd", builtin.lsp_definitions, { buffer = 0 })
        vim.keymap.set("n", "gr", builtin.lsp_references, { buffer = 0 })
        vim.keymap.set("n", "gD", vim.lsp.buf.declaration, { buffer = 0 })
        vim.keymap.set("n", "gT", vim.lsp.buf.type_definition, { buffer = 0 })
        vim.keymap.set("n", "K", vim.lsp.buf.hover, { buffer = 0 })

        vim.keymap.set("n", "<space>cr", vim.lsp.buf.rename, { buffer = 0 })
        vim.keymap.set("n", "<space>ca", vim.lsp.buf.code_action, { buffer = 0 })
        vim.keymap.set("n", "<space>wd", builtin.lsp_document_symbols, { buffer = 0 })

        local filetype = vim.bo[bufnr].filetype
        if disable_semantic_tokens[filetype] then
          client.server_capabilities.semanticTokensProvider = nil
        end

        -- Override server capabilities
        if settings.server_capabilities then
          for k, v in pairs(settings.server_capabilities) do
            if v == vim.NIL then
              ---@diagnostic disable-next-line: cast-local-type
              v = nil
            end

            client.server_capabilities[k] = v
          end
        end
      end,
    })

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
  end
}
