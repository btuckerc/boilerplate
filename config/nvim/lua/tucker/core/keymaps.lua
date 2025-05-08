-- Set leader key to space
vim.g.mapleader = " "
vim.g.maplocalleader = " "

local set = vim.keymap.set
local k = vim.keycode

-- Helper function to create keymaps with consistent options
local function create_keymap(mode, lhs, rhs, desc)
    local opts = { noremap = true, silent = true, desc = desc }
    set(mode, lhs, rhs, opts)
end

-- Disable spacebar key's default behavior in Normal and Visual modes
create_keymap({ 'n', 'v' }, '<Space>', '<Nop>', "Disable space default behavior")

-- Exit insert mode with jk/kj
create_keymap("i", "jk", "<ESC>", "Exit insert mode")
create_keymap("i", "kj", "<ESC>", "Exit insert mode")

-- Clear search highlights
create_keymap("n", "<leader>h", ":nohl<CR>", "Clear search highlights")

-- Toggle hlsearch if enabled, otherwise execute normal enter
set("n", "<CR>", function()
    if vim.v.hlsearch == 1 then
        vim.cmd.nohl()
        return ""
    else
        return k "<CR>"
    end
end, { expr = true })

-- Delete single character without copying to register
create_keymap("n", "x", '"_x', "Delete character without copying to register")

-- Increment/decrement numbers
create_keymap("n", "<leader>+", "<C-a>", "Increment number")
create_keymap("n", "<leader>-", "<C-x>", "Decrement number")

-- Window management
create_keymap("n", "<leader>wv", "<C-w>v", "Split window vertically")
create_keymap("n", "<leader>wh", "<C-w>s", "Split window horizontally")
create_keymap("n", "<leader>w=", "<C-w>=", "Make splits equal size")
create_keymap("n", "<leader>wq", "<cmd>close<CR>", "Close current split")

-- Tab management
create_keymap("n", "<leader>tn", "<cmd>tabnew<CR>", "New tab")
create_keymap("n", "<leader>tq", "<cmd>tabclose<CR>", "Close tab")
create_keymap("n", "<leader>tl", "<cmd>tabn<CR>", "Next tab")
create_keymap("n", "<leader>th", "<cmd>tabp<CR>", "Previous tab")
create_keymap("n", "<leader>ts", "<cmd>tabnew %<CR>", "Split tab")

-- File browser in current buffer's directory
create_keymap("n", "<leader>e", function()
    local buftype = vim.bo.buftype
    local current_buf_dir = buftype == '' and vim.fn.expand('%:p:h') or vim.fn.getcwd()
    vim.cmd('bd')
    vim.cmd('e ' .. current_buf_dir)
end, "Open file browser in current buffer's directory")

-- Buffer management
create_keymap("n", "<leader>bh", ":bprev<CR>", "Previous buffer")
create_keymap("n", "<leader>bl", ":bnext<CR>", "Next buffer")
create_keymap("n", "<leader>bd", ":bdelete<CR>", "Delete buffer")

-- Clipboard management
create_keymap("n", "dd", '"_dd', "Delete line without affecting clipboard")
create_keymap("n", "<leader>y", '"+dd', "Yank line to clipboard")
create_keymap("n", "dG", '"_dG', "Delete to end of file without affecting clipboard")

-- Scrolling and centering
create_keymap('n', '<C-d>', '<C-d>zz', "Scroll down and center")
create_keymap('n', '<C-u>', '<C-u>zz', "Scroll up and center")
create_keymap('n', 'n', 'nzzzv', "Find next and center")
create_keymap('n', 'N', 'Nzzzv', "Find previous and center")

-- Window resizing
create_keymap('n', '<Up>', ':resize -1<CR>', "Resize window up")
create_keymap('n', '<Down>', ':resize +1<CR>', "Resize window down")
create_keymap('n', '<Left>', ':vertical resize -1<CR>', "Resize window left")
create_keymap('n', '<Right>', ':vertical resize +1<CR>', "Resize window right")

-- Text movement
create_keymap('v', 'J', ':m .+1<CR>==', "Move text down")
create_keymap('v', 'K', ':m .-2<CR>==', "Move text up")

-- Diagnostics
create_keymap('n', '<leader>dp', vim.diagnostic.goto_prev, "Previous diagnostic")
create_keymap('n', '<leader>dn', vim.diagnostic.goto_next, "Next diagnostic")
create_keymap('n', '<leader>dl', vim.diagnostic.setloclist, "List diagnostics")

-- Lua execution
create_keymap("n", "<leader>xl", "<cmd>.lua<CR>", "Execute current line")
create_keymap("n", "<leader>xf", "<cmd>source %<CR>", "Execute current file")

-- Session management
create_keymap('n', '<leader>ss', ':mksession! .session.vim<CR>', "Save session")
create_keymap('n', '<leader>sl', ':source .session.vim<CR>', "Load session")

-- Plugin management
create_keymap('n', '<leader>L', ':Lazy<CR>', "Lazy load plugins")

-- Line wrapping
create_keymap('n', ',', ':set wrap!<CR>', "Toggle line wrapping")

-- Toggle inlay hints
set("n", "<leader>th", function()
    vim.lsp.inlay_hint.enable(not vim.lsp.inlay_hint.is_enabled { bufnr = 0 }, { bufnr = 0 })
end, { desc = "Toggle inlay hints" })
