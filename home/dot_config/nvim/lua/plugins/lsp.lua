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

      -- Global LSP performance settings
      vim.diagnostic.config({
        update_in_insert = false, -- Don't show diagnostics while typing
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
          priority = 8, -- Lower priority for less frequent updates
        },
      })

      -- LSP keymaps and completion setup
      vim.api.nvim_create_autocmd("LspAttach", {
        callback = function(event)
          local client = vim.lsp.get_client_by_id(event.data.client_id)
          local map = function(keys, func, desc)
            vim.keymap.set("n", keys, func, { buffer = event.buf, desc = "LSP: " .. desc })
          end

          map("gd", vim.lsp.buf.definition, "Go to definition")
          map("gr", vim.lsp.buf.references, "Go to references")
          map("gI", vim.lsp.buf.implementation, "Go to implementation")
          map("gD", vim.lsp.buf.declaration, "Go to declaration")
          map("grt", vim.lsp.buf.type_definition, "Type definition")
          map("<leader>rn", vim.lsp.buf.rename, "Rename")
          map("<leader>ca", vim.lsp.buf.code_action, "Code action")
          map("K", vim.lsp.buf.hover, "Hover documentation")

          if client and client.server_capabilities.inlayHintProvider then
            pcall(function()
              vim.lsp.inlay_hint.enable(false, { bufnr = event.buf })
            end)
          end

          -- Enable native LSP completion for this buffer/client
          if client and client:supports_method("textDocument/completion") then
            vim.lsp.completion.enable(true, client.id, event.buf, { autotrigger = true })
          end
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
              diagnosticMode = "openFilesOnly",
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
      local function command_works(cmd)
        local ok, result = pcall(vim.system, cmd, { text = true })
        if not ok then
          return false
        end

        return result:wait().code == 0
      end

      local formatters_by_ft = {
        lua = { "stylua" },
        python = { "black" },
        javascript = { "prettier" },
        typescript = { "prettier" },
        json = { "prettier" },
        yaml = { "prettier" },
        markdown = { "prettier" },
        go = { "gofmt" },
        rust = { "rustfmt" },
      }

      if command_works({ "ruff", "--version" }) then
        formatters_by_ft.python = { "ruff_format", "black" }
      end

      if command_works({ "gofumpt", "--version" }) and command_works({ "goimports", "-help" }) then
        formatters_by_ft.go = { "gofumpt", "goimports" }
      elseif command_works({ "goimports", "-help" }) then
        formatters_by_ft.go = { "goimports" }
      end

      if command_works({ "rubocop", "--version" }) then
        formatters_by_ft.ruby = { "robocop" }
      end

      if command_works({ "terraform", "version" }) then
        formatters_by_ft.terraform = { "terraform_fmt" }
      end

      if command_works({ "shfmt", "--version" }) then
        formatters_by_ft.sh = { "shfmt" }
      end

      require("conform").setup({
        formatters_by_ft = formatters_by_ft,
        format_on_save = {
          timeout_ms = 500,
          lsp_fallback = true,
        },
      })
    end,
  },
}
