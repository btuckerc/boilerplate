-- Performance optimization utilities (no diagnostics)

-- Performance-aware large file handling
vim.api.nvim_create_autocmd("BufReadPre", {
  callback = function()
    local file_size = vim.fn.getfsize(vim.fn.expand("<afile>"))
    if file_size > 512 * 1024 then -- 512KB threshold
      vim.opt_local.foldmethod = "manual"
      vim.opt_local.spell = false
      vim.opt_local.swapfile = false
      vim.opt_local.undofile = false
      vim.cmd("syntax off")
    end
  end,
})
