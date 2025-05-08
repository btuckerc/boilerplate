-- Highlight on yank
local highlight_group = vim.api.nvim_create_augroup('YankHighlight', { clear = true })
vim.api.nvim_create_autocmd('TextYankPost', {
  callback = function()
    vim.highlight.on_yank()
  end,
  group = highlight_group,
  pattern = '*',
})

-- Kitty terminal padding (commented out by default)
--[[
local kitty_group = vim.api.nvim_create_augroup('KittyPadding', { clear = true })
vim.api.nvim_create_autocmd('VimEnter', {
    callback = function()
        vim.fn.system('kitty @ set-spacing padding=10')
    end,
    group = kitty_group
})

vim.api.nvim_create_autocmd('VimLeave', {
    callback = function()
        vim.fn.system('kitty @ set-spacing padding=0')
    end,
    group = kitty_group
})
--]]
