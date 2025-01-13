return {
  "nvim-treesitter/nvim-treesitter",
  build = ":TSUpdate",
  config = function()
    ---@diagnostic disable-next-line: undefined-field
    local uv = vim.loop

    ---@type TSConfig
    local config = {
      modules = {},
      ignore_install = {},
      ensure_installed = {
        "vimdoc", "javascript", "typescript", "c", "lua", "rust",
        "jsdoc", "bash",
      },

      -- Install parsers synchronously (only applied to `ensure_installed`)
      sync_install = false,
      auto_install = true,
      indent = { enable = true },
      highlight = {
        -- `false` will disable the whole extension
        enable = true,
        disable = function(lang, buf)
          if lang == "html" then
            return true
          end

          local max_filesize = 100 * 1024 -- 100 KB
          local ok, stats = pcall(uv.fs_stat, vim.api.nvim_buf_get_name(buf))
          if ok and stats and stats.size > max_filesize then
            vim.notify(
              "File larger than 100KB treesitter disabled for performance",
              vim.log.levels.WARN,
              { title = "Treesitter" }
            )
            return true
          end
        end,

        -- Setting this to true will run `:h syntax` and tree-sitter at the same time.
        -- Set this to `true` if you depend on "syntax" being enabled (like for indentation).
        -- Using this option may slow down your editor, and you may see some duplicate highlights.
        -- Instead of true it can also be a list of languages
        additional_vim_regex_highlighting = { "markdown" },
      },
    }

    require("nvim-treesitter.configs").setup(config)

    ---@type table<string, ParserInfo>
    local parser_config = require("nvim-treesitter.parsers").get_parser_configs()
    parser_config.templ = {
      install_info = {
        url = "https://github.com/vrischmann/tree-sitter-templ.git",
        files = { "src/parser.c", "src/scanner.c" },
        branch = "master",
      },
      filetype = "templ", -- the filetype to associate with this parser
      maintainers = { "@vrischmann" }, -- maintainer's GitHub handle
    }

    vim.treesitter.language.register("templ", "templ")
  end
}