return {
  "mfussenegger/nvim-lint",
  event = { "BufReadPre", "BufNewFile" },
  config = function()
    local lint = require("lint")

    -- Configure linters for different filetypes
    lint.linters_by_ft = {
      python = { "pylint" },
      javascript = { "eslint_d" },
      typescript = { "eslint_d" },
      lua = { "luacheck" },
      sh = { "shellcheck" },
      markdown = { "markdownlint" },
      yaml = { "yamllint" },
    }

    -- Configure markdownlint to ignore Dataview syntax
    lint.linters.markdownlint.args = {
      '--config',
      vim.fn.stdpath('config') .. '/linters/markdownlint.jsonc'
    }

    -- Create autocommand group
    local group = vim.api.nvim_create_augroup("lint", { clear = true })

    -- Try to lint if linters exist for filetype
    local function try_lint()
      local names = lint._resolve_linter_by_ft(vim.bo.filetype)
      if #names > 0 then
        lint.try_lint()
      end
    end

    -- Setup auto-linting
    vim.api.nvim_create_autocmd(
      { "BufWritePost", "BufReadPost", "InsertLeave" },
      {
        group = group,
        pattern = "*",
        callback = try_lint,
      }
    )

    -- Manual lint trigger
    vim.keymap.set("n", "<leader>ll", try_lint, { desc = "Trigger linting for current file" })
  end,
}
