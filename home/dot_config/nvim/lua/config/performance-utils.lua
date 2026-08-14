-- Performance optimization utilities (no diagnostics)

local uv = vim.uv
local large_file_group = vim.api.nvim_create_augroup("nvim_large_file", { clear = true })
local large_file_bytes = 512 * 1024
local large_file_lines = 5000

local function mark_large_file(buf)
  if vim.b[buf].large_file then
    return
  end

  vim.b[buf].large_file = true
  vim.bo[buf].swapfile = false
  vim.bo[buf].undofile = false
  vim.bo[buf].syntax = "OFF"
  vim.opt_local.foldmethod = "manual"
  vim.opt_local.spell = false
end

vim.api.nvim_create_autocmd("BufReadPre", {
  group = large_file_group,
  callback = function(event)
    local file = vim.api.nvim_buf_get_name(event.buf)
    if file == "" then
      return
    end

    local stat = uv.fs_stat(file)
    if stat and stat.size > large_file_bytes then
      mark_large_file(event.buf)
    end
  end,
})

vim.api.nvim_create_autocmd("BufReadPost", {
  group = large_file_group,
  callback = function(event)
    if vim.b[event.buf].large_file then
      return
    end

    if vim.api.nvim_buf_line_count(event.buf) > large_file_lines then
      mark_large_file(event.buf)
    end
  end,
})
