-- set leader key to space
vim.g.mapleader = " "
vim.g.maplocalleader = " "

local function map(mode, lhs, rhs, desc)
    local opts = { noremap = true, silent = true, desc = desc }
    vim.keymap.set(mode, lhs, rhs, opts)
end

-- Disable the spacebar key's default behavior in Normal and Visual modes
map({ 'n', 'v' }, '<Space>', '<Nop>', "Disable space default behavior")

-- use jk to exit insert mode
map("i", "jk", "<ESC>", "Exit insert mode with jk")

-- clear search highlights
map("n", "<leader>h", ":nohl<CR>", "Clear search highlights")

-- delete single character without copying into register
map("n", "x", '"_x', "Delete character without copying to register")

-- increment/decrement numbers
map("n", "<leader>+", "<C-a>", "Increment number")
map("n", "<leader>-", "<C-x>", "Decrement number")

-- window management (using 'w' prefix)
map("n", "<leader>wv", "<C-w>v", "Split window vertically")
map("n", "<leader>ws", "<C-w>s", "Split window horizontally")
map("n", "<leader>we", "<C-w>=", "Make splits equal size")
map("n", "<leader>wx", "<cmd>close<CR>", "Close current split")

-- tab management
map("n", "<leader>to", "<cmd>tabnew<CR>", "Open new tab")
map("n", "<leader>tx", "<cmd>tabclose<CR>", "Close current tab")
map("n", "<leader>tn", "<cmd>tabn<CR>", "Go to next tab")
map("n", "<leader>tp", "<cmd>tabp<CR>", "Go to previous tab")
map("n", "<leader>tf", "<cmd>tabnew %<CR>", "Open current buffer in new tab")

-- buffer management
map("n", "[b", ":bprev<CR>", "Previous buffer")
map("n", "]b", ":bnext<CR>", "Next buffer")
map("n", "<leader>bd", ":bdelete<CR>", "Delete buffer")

-- clipboard management
map("n", "dd", '"_dd', "Delete line without affecting clipboard")
map("n", "<leader>d", '"+dd', "Delete line and yank to clipboard")
map("n", "dG", '"_dG', "Delete to end of file without affecting clipboard")

-- Vertical scroll and center
map('n', '<C-d>', '<C-d>zz', "Scroll down and center")
map('n', '<C-u>', '<C-u>zz', "Scroll up and center")

-- Find and center
map('n', 'n', 'nzzzv', "Find next and center")
map('n', 'N', 'Nzzzv', "Find previous and center")

-- Resize with arrows
map('n', '<Up>', ':resize -2<CR>', "Resize window up")
map('n', '<Down>', ':resize +2<CR>', "Resize window down")
map('n', '<Left>', ':vertical resize -2<CR>', "Resize window left")
map('n', '<Right>', ':vertical resize +2<CR>', "Resize window right")

-- Navigate between splits
map('n', '<C-k>', ':wincmd k<CR>', "Move to upper window")
map('n', '<C-j>', ':wincmd j<CR>', "Move to lower window")
map('n', '<C-h>', ':wincmd h<CR>', "Move to left window")
map('n', '<C-l>', ':wincmd l<CR>', "Move to right window")

-- Move text up and down
map('v', '<A-j>', ':m .+1<CR>==', "Move text down")
map('v', '<A-k>', ':m .-2<CR>==', "Move text up")

-- Diagnostic keymaps
map('n', '[d', vim.diagnostic.goto_prev, 'Go to previous diagnostic message')
map('n', ']d', vim.diagnostic.goto_next, 'Go to next diagnostic message')
map('n', '<leader>q', vim.diagnostic.setloclist, 'Open diagnostics list')

-- Session management (capital S to avoid conflicts)
map('n', '<leader>Ss', ':mksession! .session.vim<CR>', 'Save session')
map('n', '<leader>Sl', ':source .session.vim<CR>', 'Load session')

-- Plugin management
map('n', '<leader>L', ':Lazy<CR>', 'Lazy load plugins')
