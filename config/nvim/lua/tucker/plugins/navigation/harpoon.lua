return {
  'ThePrimeagen/harpoon',
  branch = 'harpoon2',
  dependencies = { 'nvim-lua/plenary.nvim' },
  config = function()
    local harpoon = require('harpoon')
    local set = vim.keymap.set
    local opts = { noremap = true, silent = true }

    -- Configure harpoon
    harpoon.setup({
      global_settings = {
        save_on_toggle = true,
        save_on_change = true,
        enter_on_sendcmd = true,
        tmux_autoclose_windows = true,
        excluded_filetypes = { 'harpoon' },
        mark_branch = true,
        tabline = true,
        tabline_prefix = '   ',
        tabline_suffix = '   ',
      },
      menu = {
        width = vim.api.nvim_win_get_width(0) - 4,
      },
    })

    -- Key mappings
    -- Toggle quick menu
    set('n', '<C-e>', function()
      harpoon.ui:toggle_quick_menu(harpoon:list())
    end, { desc = 'Toggle harpoon quick menu' })

    -- Add current file to harpoon list
    set('n', '<leader>m', function()
      harpoon:list():add()
    end, { desc = 'Add file to harpoon list' })

    -- Remove current file from harpoon list
    set('n', '<leader>hr', function()
      harpoon:list():remove()
    end, { desc = 'Remove file from harpoon list' })

    -- Set <space>1..<space>5 be my shortcuts to moving to the files
    for _, idx in ipairs { 1, 2, 3, 4, 5 } do
      set("n", string.format("<leader>%d", idx), function()
        harpoon:list():select(idx)
      end, { desc = string.format("Go to harpoon file %d", idx) })
    end

    -- Toggle previous & next buffers stored within Harpoon list
    set('n', '<leader>p', function()
      harpoon:list():prev()
    end, { desc = 'Navigate to previous file' })
    set('n', '<leader>n', function()
      harpoon:list():next()
    end, { desc = 'Navigate to next file' })
  end,
}
