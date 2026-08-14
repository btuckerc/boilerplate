-- Editor enhancements and functionality

return {
  -- Syntax highlighting
  {
    "nvim-treesitter/nvim-treesitter",
    branch = "main",
    lazy = false,
    build = ":TSUpdate",
    config = function()
      require("config.mise").prefer_install_dirs({
        "/node/",
        "/ubi-tree-sitter-tree-sitter/",
      })

      local treesitter = require("nvim-treesitter")
      treesitter.setup()

      local parsers = {
        "bash",
        "c",
        "dockerfile",
        "go",
        "html",
        "javascript",
        "jsdoc",
        "json",
        "lua",
        "luadoc",
        "markdown",
        "markdown_inline",
        "python",
        "rust",
        "sql",
        "templ",
        "terraform",
        "toml",
        "typescript",
        "vim",
        "vimdoc",
        "yaml",
      }

      local installed = {}
      for _, lang in ipairs(treesitter.get_installed("parsers")) do
        installed[lang] = true
      end

      local missing = vim.tbl_filter(function(lang)
        return not installed[lang]
      end, parsers)

      if #missing > 0 and #vim.api.nvim_list_uis() > 0 then
        vim.api.nvim_create_autocmd("User", {
          group = vim.api.nvim_create_augroup("nvim_treesitter_install", { clear = true }),
          pattern = "LazyDone",
          once = true,
          callback = function()
            treesitter.install(missing, { summary = true })
          end,
        })
      end

      vim.api.nvim_create_autocmd("FileType", {
        group = vim.api.nvim_create_augroup("nvim_treesitter_features", { clear = true }),
        callback = function(event)
          if vim.bo[event.buf].buftype ~= "" or vim.b[event.buf].large_file then
            return
          end

          local ok = pcall(vim.treesitter.start, event.buf)
          if ok then
            vim.bo[event.buf].indentexpr = "v:lua.require'nvim-treesitter'.indentexpr()"
          end
        end,
      })
    end,
  },

  -- Autopairs
  {
    "windwp/nvim-autopairs",
    event = "InsertEnter",
    config = function()
      require("nvim-autopairs").setup({})
    end,
  },

  -- Comments
  {
    "numToStr/Comment.nvim",
    event = { "BufReadPre", "BufNewFile" },
    config = function()
      require("Comment").setup()
    end,
  },

  -- Undo tree
  {
    "mbbill/undotree",
    cmd = "UndotreeToggle",
    keys = {
      { "<leader>u", "<cmd>UndotreeToggle<cr>", desc = "Toggle undotree" },
    },
  },
}
