return {
  {
    "echasnovski/mini.nvim",
    version = false,
    config = function()
      -- Trailspace: Remove trailing whitespace
      require("mini.trailspace").setup()

      -- Splitjoin: Split and join code blocks
      require("mini.splitjoin").setup()

      -- Surround: Surround text objects
      require("mini.surround").setup({
        mappings = {
          add = "ys", -- Add surrounding
          delete = "ds", -- Delete surrounding
          find = "fs", -- Find surrounding
          find_left = "Fs", -- Find surrounding to the left
          highlight = '', -- Disable 'hs' mapping
          replace = "cs", -- Replace surrounding
          update_n_lines = "ns", -- Update `n_lines`
        },
      })

      -- Comment: Comment/uncomment code
      require("mini.comment").setup({
        mappings = {
          comment = 'gcc', -- Add comment
          comment_line = 'gcc', -- Add comment on a line
          comment_visual = 'gcc', -- Add comment in visual mode
        }
      })
    end,
  },
}
