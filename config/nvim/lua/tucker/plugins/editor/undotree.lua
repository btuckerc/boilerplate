return {
  "mbbill/undotree",
  config = function()
    -- Undotree configuration
    vim.g.undotree_WindowLayout = 2  -- Layout 2 puts diff window on bottom
    vim.g.undotree_ShortIndicators = 1  -- Use short indicators
    vim.g.undotree_SplitWidth = 30  -- Set tree window width
    vim.g.undotree_DiffpanelHeight = 10  -- Set diff window height
    vim.g.undotree_SetFocusWhenToggle = 1  -- Focus undotree when opening
    vim.g.undotree_DiffAutoOpen = 1  -- Auto open diff window
    vim.g.undotree_RelativeTimestamp = 1  -- Use relative timestamps
    vim.g.undotree_HighlightChangedText = 1  -- Highlight changed text
    vim.g.undotree_HighlightSyntaxAdd = "DiffAdd"  -- Syntax for additions
    vim.g.undotree_HighlightSyntaxChange = "DiffChange"  -- Syntax for changes

    -- Keybindings
    local keymap = vim.keymap.set

    -- Main toggle
    keymap("n", "<leader>u", vim.cmd.UndotreeToggle, { desc = "Toggle Undotree" })

    -- Additional keybindings when undotree is open
    -- These work when focus is in the undotree window
    vim.api.nvim_create_autocmd("FileType", {
      pattern = "undotree",
      callback = function()
        local opts = { buffer = true, silent = true }
        -- Navigation
        keymap("n", "k", "k", opts)  -- Move up in tree
        keymap("n", "j", "j", opts)  -- Move down in tree
        keymap("n", "K", "5k", opts)  -- Move up faster
        keymap("n", "J", "5j", opts)  -- Move down faster
        -- Actions
        keymap("n", "<CR>", "<plug>UndotreeEnter", opts)  -- Revert to selected state
        keymap("n", "u", "<plug>UndotreeUndo", opts)  -- Undo
        keymap("n", "<C-r>", "<plug>UndotreeRedo", opts)  -- Redo
        keymap("n", "q", ":UndotreeHide<CR>", opts)  -- Close undotree
      end,
    })
  end
}
