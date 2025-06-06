-- Set leader key to space
vim.g.mapleader = " "
vim.g.maplocalleader = " "

local set = vim.keymap.set
local k = vim.keycode

-- Helper function for creating keymaps
local function create_keymap(mode, lhs, rhs, desc)
    local opts = { noremap = true, silent = true, desc = desc }
    set(mode, lhs, rhs, opts)
end

-- Prevent space from moving cursor, allowing which-key to trigger
create_keymap({ 'n', 'v' }, '<Space>', '<Nop>', "Nop")

-- General mappings
create_keymap("i", "jk", "<ESC>", "Exit insert mode")
create_keymap("i", "kj", "<ESC>", "Exit insert mode")
create_keymap("n", "<leader>hc", ":nohl<CR>", "Clear search highlights")

-- Toggle hlsearch on <CR>
set("n", "<CR>", function()
    if vim.v.hlsearch == 1 then
        vim.cmd.nohl()
        return ""
    else
        return k "<CR>"
    end
end, { expr = true, silent = true, desc = "Clear highlight on <CR>" })

-- Increment/decrement numbers
create_keymap("n", "<leader>+", "<C-a>", "Increment number")
create_keymap("n", "<leader>-", "<C-x>", "Decrement number")

-- Window management
create_keymap("n", "<leader>wv", "<C-w>v", "Split window vertically")
create_keymap("n", "<leader>wh", "<C-w>s", "Split window horizontally")
create_keymap("n", "<leader>w=", "<C-w>=", "Make splits equal size")
create_keymap("n", "<leader>wq", "<cmd>close<CR>", "Close current split")
create_keymap('n', '<Up>', ':resize -1<CR>', "Resize window up")
create_keymap('n', '<Down>', ':resize +1<CR>', "Resize window down")
create_keymap('n', '<Left>', ':vertical resize -1<CR>', "Resize window left")
create_keymap('n', '<Right>', ':vertical resize +1<CR>', "Resize window right")

-- Tab management
create_keymap("n", "<leader>tn", "<cmd>tabnew<CR>", "New tab")
create_keymap("n", "<leader>tq", "<cmd>tabclose<CR>", "Close tab")
create_keymap("n", "<leader>tl", "<cmd>tabn<CR>", "Next tab")
create_keymap("n", "<leader>th", "<cmd>tabp<CR>", "Previous tab")
create_keymap("n", "<leader>ts", "<cmd>tabnew %<CR>", "Split tab")
create_keymap("n", "<leader>to", "<cmd>tabonly<CR>", "Close other tabs")

-- Buffer management
create_keymap("n", "<S-L>", ":bnext<CR>", "Next buffer")
create_keymap("n", "<S-H>", ":bprevious<CR>", "Previous buffer")
create_keymap("n", "<leader>bd", ":bdelete<CR>", "Delete buffer")

-- Scrolling and centering
create_keymap('n', '<C-d>', '<C-d>zz', "Scroll down and center")
create_keymap('n', '<C-u>', '<C-u>zz', "Scroll up and center")
create_keymap('n', 'n', 'nzzzv', "Find next and center")
create_keymap('n', 'N', 'Nzzzv', "Find previous and center")

-- Text movement
create_keymap('v', 'J', ':m .+1<CR>==', "Move text down")
create_keymap('v', 'K', ':m .-2<CR>==', "Move text up")

-- Diagnostics
create_keymap('n', '<leader>dp', vim.diagnostic.goto_prev, "Previous diagnostic")
create_keymap('n', '<leader>dn', vim.diagnostic.goto_next, "Next diagnostic")
create_keymap('n', '<leader>dl', vim.diagnostic.setloclist, "List diagnostics")

-- Lua execution
create_keymap("n", "<leader>xl", "<cmd>luafile %<CR>", "Execute current file")
create_keymap("v", "<leader>xl", ":lua print(vim.inspect(vim.fn.getreg('\"')))<CR>", "Execute selection")

-- Plugin management
create_keymap('n', '<leader>L', ':Lazy<CR>', "Lazy load plugins")

-- Terminal
create_keymap("n", "<leader>tT", function() require("tucker.terminalpop").toggle() end, "Toggle terminal")

-- Line wrapping
create_keymap('n', ',', ':set wrap!<CR>', "Toggle line wrapping")

-- Toggle inlay hints
set("n", "<leader>ti", function()
    vim.lsp.inlay_hint.enable(not vim.lsp.inlay_hint.is_enabled { bufnr = 0 }, { bufnr = 0 })
end, { desc = "Toggle inlay hints" })

-- Unmap conflicting default plugin keymaps safely
pcall(vim.keymap.del, "n", "<leader>t")
pcall(vim.keymap.del, "n", "<leader>l")
pcall(vim.keymap.del, "n", "<leader>c")

-- File explorer
create_keymap("n", "-", "<CMD>Oil<CR>", "Open parent directory (replace current buffer)")
create_keymap("n", "_", "<CMD>vsplit | Oil<CR>", "Open parent directory in new split")
