-- Editor enhancements and functionality

return {
  -- Syntax highlighting
  {
    "nvim-treesitter/nvim-treesitter",
    lazy = false,
    build = ":TSUpdate",
    config = function()
      local ensure_installed = {
        "bash",
        "c",
        "html",
        "lua",
        "luadoc",
        "markdown",
        "markdown_inline",
        "vim",
        "vimdoc",
        "javascript",
        "typescript",
        "python",
        "go",
        "rust",
        "json",
        "yaml",
        "toml",
        "dockerfile",
        "terraform",
        "sql",
        "jsdoc",
        "templ",
      }
      local uv = vim.uv or vim.loop

      local function prefer_real_treesitter_binary()
        local exepath = vim.fn.exepath("tree-sitter")
        if exepath == "" or not exepath:match("/mise/shims/tree%-sitter$") then
          return
        end

        local result = vim.system({ "mise", "which", "tree-sitter" }, {
          cwd = uv.os_homedir(),
          text = true,
        }):wait()
        if result.code ~= 0 then
          return
        end

        local real_bin = vim.trim(result.stdout or "")
        if real_bin == "" then
          return
        end

        local real_dir = vim.fs.dirname(real_bin)
        local path_sep = package.config:sub(1, 1) == "\\" and ";" or ":"
        local current_path = vim.env.PATH or ""
        if current_path == real_dir or current_path:find("^" .. vim.pesc(real_dir .. path_sep)) then
          return
        end

        vim.env.PATH = real_dir .. path_sep .. current_path
      end

      local function get_parser_configs()
        local parser_configs = require("nvim-treesitter.parsers")
        if type(parser_configs.get_parser_configs) == "function" then
          parser_configs = parser_configs.get_parser_configs()
        end
        return parser_configs
      end

      local function ensure_custom_parsers()
        local parser_configs = get_parser_configs()
        if not parser_configs.templ then
          parser_configs.templ = {
            install_info = {
              url = "https://github.com/vrischmann/tree-sitter-templ",
              files = { "src/parser.c", "src/scanner.c" },
              branch = "main",
            },
          }
        end
      end

      local function treesitter_disabled(lang, buf)
        if lang == "html" then
          return true
        end

        if vim.b[buf].large_file then
          return true
        end

        local max_filesize = 100 * 1024 -- 100 KB
        local ok, stats = pcall(uv.fs_stat, vim.api.nvim_buf_get_name(buf))
        if ok and stats and stats.size > max_filesize then
          vim.b[buf].large_file = true
          vim.schedule(function()
            vim.notify(
              "File larger than 100KB, Treesitter disabled for performance",
              vim.log.levels.WARN,
              { title = "Treesitter" }
            )
          end)
          return true
        end

        if vim.api.nvim_buf_line_count(buf) > 2000 then
          vim.b[buf].large_file = true
          return true
        end

        return false
      end

      ensure_custom_parsers()
      prefer_real_treesitter_binary()

      vim.api.nvim_create_autocmd("User", {
        group = vim.api.nvim_create_augroup("nvim_treesitter_parsers", { clear = true }),
        pattern = "TSUpdate",
        callback = ensure_custom_parsers,
      })

      local ok_configs, ts_configs = pcall(require, "nvim-treesitter.configs")
      if ok_configs and type(ts_configs.setup) == "function" then
        ts_configs.setup({
          ensure_installed = ensure_installed,
          auto_install = true,
          highlight = {
            enable = true,
            disable = treesitter_disabled,
            additional_vim_regex_highlighting = { "markdown" },
          },
          indent = { enable = true },
        })
        return
      end

      local ts = require("nvim-treesitter")
      ts.setup({})

      vim.api.nvim_create_user_command("TSInstallManaged", function()
        ensure_custom_parsers()
        prefer_real_treesitter_binary()
        ts.install(ensure_installed, { summary = true })
      end, { desc = "Install managed treesitter parsers" })

      vim.api.nvim_create_autocmd("FileType", {
        group = vim.api.nvim_create_augroup("nvim_treesitter_features", { clear = true }),
        callback = function(args)
          local filetype = vim.bo[args.buf].filetype
          local lang = vim.treesitter.language.get_lang(filetype)
          if not lang or treesitter_disabled(lang, args.buf) then
            return
          end

          local loaded = vim.treesitter.language.add(lang)
          if not loaded then
            return
          end

          local ok = pcall(vim.treesitter.start, args.buf, lang)
          if not ok then
            return
          end

          if filetype == "markdown" then
            vim.bo[args.buf].syntax = "on"
          end

          vim.bo[args.buf].indentexpr = "v:lua.require'nvim-treesitter'.indentexpr()"
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

  -- Vim practice game
  {
    "theprimeagen/vim-be-good",
    dependencies = {
      "nvim-lua/plenary.nvim",
    },
    config = function() end,
  },
}
