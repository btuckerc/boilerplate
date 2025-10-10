-- Essential keymaps for efficiency

local map = vim.keymap.set

-- Escape from insert mode (explicit mapping to ensure it works)
map("i", "<Esc>", "<ESC>", { desc = "Exit insert mode with Escape" })
-- Additional escape options
map("i", "jk", "<ESC>", { desc = "Exit insert mode with jk" })
map("i", "kj", "<ESC>", { desc = "Exit insert mode with kj" })

-- Prevent space from moving cursor in normal/visual mode
map({ "n", "v" }, "<Space>", "<Nop>", { desc = "Disable space movement" })

-- Clear search highlights (using leader+hc to not override Escape default behavior)
map("n", "<leader>hc", "<cmd>nohlsearch<CR>", { desc = "Clear search highlights" })

-- Toggle hlsearch on Enter (preserve original behavior)
map("n", "<CR>", function()
    if vim.v.hlsearch == 1 then
        vim.cmd.nohl()
        return ""
    else
        return vim.keycode("<CR>")
    end
end, { expr = true, silent = true, desc = "Clear highlight on Enter" })

-- Better up/down (wrapped lines)
map({ "n", "x" }, "j", "v:count == 0 ? 'gj' : 'j'", { expr = true, silent = true })
map({ "n", "x" }, "k", "v:count == 0 ? 'gk' : 'k'", { expr = true, silent = true })

-- Scrolling and centering (restore original behavior)
map("n", "<C-d>", "<C-d>zz", { desc = "Scroll down and center" })
map("n", "<C-u>", "<C-u>zz", { desc = "Scroll up and center" })
map("n", "n", "nzzzv", { desc = "Find next and center" })
map("n", "N", "Nzzzv", { desc = "Find previous and center" })

-- Move lines up/down (restore original behavior)
map("v", "J", ":m '>+1<CR>gv=gv", { desc = "Move selection down" })
map("v", "K", ":m '<-2<CR>gv=gv", { desc = "Move selection up" })

-- Better indenting
map("v", "<", "<gv", { desc = "Indent left and reselect" })
map("v", ">", ">gv", { desc = "Indent right and reselect" })

-- Paste without overwriting register
map("x", "<leader>p", [["_dP]], { desc = "Paste without overwriting register" })

-- Copy to system clipboard
map({ "n", "v" }, "<leader>y", [["+y]], { desc = "Copy to system clipboard" })
map("n", "<leader>Y", [["+Y]], { desc = "Copy line to system clipboard" })

-- Delete to void register
map({ "n", "v" }, "<leader>d", [["_d]], { desc = "Delete to void register" })

-- Increment/decrement numbers
map("n", "<leader>+", "<C-a>", { desc = "Increment number" })
map("n", "<leader>-", "<C-x>", { desc = "Decrement number" })

-- Window management
map("n", "<leader>wv", "<C-w>v", { desc = "Split window vertically" })
map("n", "<leader>wh", "<C-w>s", { desc = "Split window horizontally" })
map("n", "<leader>w=", "<C-w>=", { desc = "Make splits equal size" })
map("n", "<leader>wq", "<cmd>close<CR>", { desc = "Close current split" })

-- Window navigation
map("n", "<C-h>", "<C-w>h", { desc = "Go to left window" })
map("n", "<C-j>", "<C-w>j", { desc = "Go to lower window" })
map("n", "<C-k>", "<C-w>k", { desc = "Go to upper window" })
map("n", "<C-l>", "<C-w>l", { desc = "Go to right window" })

-- Window resizing with arrow keys (restore original)
map("n", "<Up>", ":resize -1<CR>", { desc = "Resize window up" })
map("n", "<Down>", ":resize +1<CR>", { desc = "Resize window down" })
map("n", "<Left>", ":vertical resize -1<CR>", { desc = "Resize window left" })
map("n", "<Right>", ":vertical resize +1<CR>", { desc = "Resize window right" })

-- Tab management
map("n", "<leader>tc", "<cmd>tabnew<CR>", { desc = "New tab" })
map("n", "<leader>tx", "<cmd>tabclose<CR>", { desc = "Close tab" })
map("n", "<leader>tn", "<cmd>tabn<CR>", { desc = "Next tab" })
map("n", "<leader>tp", "<cmd>tabp<CR>", { desc = "Previous tab" })
map("n", "<leader>ts", "<cmd>tabnew %<CR>", { desc = "Split tab" })
map("n", "<leader>tq", "<cmd>tabonly<CR>", { desc = "Close other tabs" })

-- Buffer management
map("n", "<S-h>", "<cmd>bprevious<cr>", { desc = "Previous buffer" })
map("n", "<S-l>", "<cmd>bnext<cr>", { desc = "Next buffer" })
map("n", "<S-L>", ":bnext<CR>", { desc = "Next buffer (original)" })
map("n", "<S-H>", ":bprevious<CR>", { desc = "Previous buffer (original)" })
map("n", "<leader>bd", "<cmd>bdelete<CR>", { desc = "Delete buffer" })

-- Quick save (quit is handled by Oil plugin for better directory navigation)
map("n", "<leader>w", "<cmd>w<cr>", { desc = "Save file" })

-- Diagnostics (restore original + new)
map("n", "[d", vim.diagnostic.goto_prev, { desc = "Go to previous diagnostic message" })
map("n", "]d", vim.diagnostic.goto_next, { desc = "Go to next diagnostic message" })
map("n", "<leader>dp", vim.diagnostic.goto_prev, { desc = "Previous diagnostic" })
map("n", "<leader>dn", vim.diagnostic.goto_next, { desc = "Next diagnostic" })
map("n", "<leader>e", vim.diagnostic.open_float, { desc = "Open floating diagnostic message" })
map("n", "<leader>dl", vim.diagnostic.setloclist, { desc = "Open diagnostics list" })

-- Lua execution (restore original)
map("n", "<leader>xl", "<cmd>luafile %<CR>", { desc = "Execute current file" })
map("v", "<leader>xl", ":lua print(vim.inspect(vim.fn.getreg('\"')))<CR>", { desc = "Execute selection" })

-- Plugin management (restore original)
map("n", "<leader>L", "<cmd>Lazy<CR>", { desc = "Open Lazy plugin manager" })

-- Transparency toggle
map("n", "<leader>tt", function()
    if vim.g.transparent_enabled == nil then
        vim.g.transparent_enabled = true
    end
    vim.g.transparent_enabled = not vim.g.transparent_enabled
    require("themes.current-theme").apply(vim.g.transparent_enabled)
    vim.notify("Transparency " .. (vim.g.transparent_enabled and "enabled" or "disabled"))
end, { desc = "Toggle transparency" })