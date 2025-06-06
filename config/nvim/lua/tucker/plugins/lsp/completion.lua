return {
  {
    "hrsh7th/nvim-cmp", -- tl;dr this plugin is the main plugin here
    event = "InsertEnter",
    dependencies = {
      "onsails/lspkind.nvim",
      "hrsh7th/cmp-nvim-lsp",
      "hrsh7th/cmp-path",
      "hrsh7th/cmp-buffer",
      { "L3MON4D3/LuaSnip", build = "make install_jsregexp" },
      "saadparwaiz1/cmp_luasnip",
      "rafamadriz/friendly-snippets",
      "roobert/tailwindcss-colorizer-cmp.nvim",
      "zbirenbaum/copilot.lua",
      "zbirenbaum/copilot-cmp",
    },
    config = function()
      local cmp = require("cmp")
      local lspkind = require("lspkind")
      local copilot = require("copilot")
      local copilot_cmp = require("copilot_cmp")
      local tailwind_cmp = require("tailwindcss-colorizer-cmp")
      local luasnip = require("luasnip")

      -- Load VSCode-style snippets
      require("luasnip.loaders.from_vscode").lazy_load()

      -- Copilot setup
      copilot.setup({
        node_command = "/opt/homebrew/bin/node",
        suggestion = { enabled = false },
        panel = { enabled = false },
      })
      copilot_cmp.setup()

      -- Editor options
      vim.opt.completeopt = { "menu", "menuone", "noselect" }
      vim.opt.shortmess:append("c")

      -- LSP Kind setup
      lspkind.init({ symbol_map = { Copilot = "" } })
      vim.api.nvim_set_hl(0, "CmpItemKindCopilot", { fg = "#6CC644" })

      -- Tailwind setup
      tailwind_cmp.setup({ color_square_width = 2 })

      -- Source menu labels
      local menu_labels = {
        buffer = "[buf]",
        nvim_lsp = "[LSP]",
        nvim_lua = "[api]",
        path = "[path]",
        luasnip = "[snip]",
        copilot = "[ai]",
        gh_issues = "[issues]",
        tn = "[TabNine]",
        eruby = "[erb]",
      }

      -- Helper function for mappings
      local map = function(keys, func, modes)
        modes = modes or { "i", "c" }
        return cmp.mapping(func, modes)
      end

      -- Main CMP setup
      cmp.setup({
        completion = {
          completeopt = "menu,menuone,preview,noselect",
        },

        sources = cmp.config.sources({
          { name = "copilot", group_index = 1 },
          { name = "nvim_lsp", group_index = 2 },
          { name = "luasnip", group_index = 2 },
          { name = "buffer", group_index = 3 },
          { name = "path", group_index = 3 },
        }),

        mapping = {
          -- Navigation
          ["<C-j>"] = map(nil, function(fallback)
            if cmp.visible() then
              cmp.select_next_item({ behavior = cmp.SelectBehavior.Insert })
            elseif luasnip.expand_or_jumpable() then
              luasnip.expand_or_jump()
            else
              fallback()
            end
          end),
          ["<C-k>"] = map(nil, function(fallback)
            if cmp.visible() then
              cmp.select_prev_item({ behavior = cmp.SelectBehavior.Insert })
            elseif luasnip.jumpable(-1) then
              luasnip.jump(-1)
            else
              fallback()
            end
          end),
          ["<C-b>"] = map(nil, function(fallback)
            cmp.scroll_docs(-4)
          end),
          ["<C-f>"] = map(nil, function(fallback)
            cmp.scroll_docs(4)
          end),
          ["<C-Space>"] = map(nil, function(fallback)
            if cmp.visible() then
              cmp.close()
            else
              cmp.complete()
            end
          end),
          ["<C-e>"] = map(nil, function(fallback)
            cmp.abort()
          end),
          ["<CR>"] = map(nil, function(fallback)
            if cmp.visible() then
              if luasnip.expandable() then
                luasnip.expand()
              else
                cmp.confirm({ select = false })
              end
            else
              fallback()
            end
          end),
          ["<C-l>"] = map(nil, function(fallback)
            if cmp.visible() then
              cmp.confirm({ behavior = cmp.ConfirmBehavior.Insert, select = true })
            else
              fallback()
            end
          end),
          ["<Tab>"] = map(nil, function(fallback)
            if cmp.visible() then
              cmp.select_next_item()
            elseif luasnip.expand_or_jumpable() then
              luasnip.expand_or_jump()
            else
              fallback()
            end
          end),
          ["<S-Tab>"] = map(nil, function(fallback)
            if cmp.visible() then
              cmp.select_prev_item()
            elseif luasnip.jumpable(-1) then
              luasnip.jump(-1)
            else
              fallback()
            end
          end),
        },

        snippet = {
          expand = function(args)
            luasnip.lsp_expand(args.body)
          end,
        },

        formatting = {
          fields = { "abbr", "kind", "menu" },
          expandable_indicator = true,
          format = function(entry, vim_item)
            -- Apply LSP kind formatting
            vim_item = lspkind.cmp_format({
              mode = "symbol_text",
              menu = menu_labels,
              maxwidth = 50,
              ellipsis_char = "...",
            })(entry, vim_item)
            -- Apply Tailwind formatting
            return tailwind_cmp.formatter(entry, vim_item)
          end,
        },

        sorting = {
          priority_weight = 2,
          comparators = {
            require("copilot_cmp.comparators").prioritize,
            cmp.config.compare.offset,
            cmp.config.compare.exact,
            cmp.config.compare.score,
            cmp.config.compare.recently_used,
            cmp.config.compare.locality,
            cmp.config.compare.kind,
            cmp.config.compare.sort_text,
            cmp.config.compare.length,
            cmp.config.compare.order,
          },
        },
      })

      -- SQL-specific setup
      cmp.setup.filetype({ "sql" }, {
        sources = {
          { name = "vim-dadbod-completion" },
          { name = "buffer" },
        },
      })
    end,
  },
}
