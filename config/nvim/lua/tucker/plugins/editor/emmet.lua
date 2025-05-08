return {
  "mattn/emmet-vim",
  ft = {
    "html",
    "css",
    "javascript",
    "javascriptreact",
    "typescriptreact",
    "svelte",
    "vue"
  },
  config = function()
    vim.g.user_emmet_mode = "n"
    vim.g.user_emmet_leader_key = "<C-y>"
    vim.g.user_emmet_settings = {
      javascript = {
        extends = "jsx",
      },
      typescript = {
        extends = "tsx",
      },
    }
  end,
}
