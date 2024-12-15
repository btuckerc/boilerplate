-- Highlight on yank
local highlight_group = vim.api.nvim_create_augroup('YankHighlight', { clear = true })
vim.api.nvim_create_autocmd('TextYankPost', {
  callback = function()
    vim.highlight.on_yank()
  end,
  group = highlight_group,
  pattern = '*',
})

-- Set kitty terminal padding to 0 when in nvim
vim.api.nvim_create_autocmd({ 'VimEnter', 'VimLeave' }, {
  group = vim.api.nvim_create_augroup('kitty_padding', { clear = true }),
  callback = function(ev)
    if ev.event == 'VimEnter' then
      vim.fn.system('kitty @ set-spacing padding=0 margin=0')
    else
      vim.fn.system('kitty @ set-spacing padding=default margin=default')
    end
  end,
})
