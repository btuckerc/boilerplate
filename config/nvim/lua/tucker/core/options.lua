vim.g.netrw_liststyle = 3
vim.g.netrw_browse_split = 3
vim.g.netrw_banner = 0
vim.g.netrw_winsize = 20
vim.g.netrw_preview = 1

-- Keep the current directory and the browsing directory synced.
vim.g.netrw_keepdir = 0

-- Show directories first (sorting)
vim.g.netrw_sort_sequence = [[[\/]$,*]]
vim.g.netrw_sizestyle = "H"

local opt = vim.opt

-- line numbers
opt.relativenumber = true
opt.number = true

-- tabs & indentation
opt.tabstop = 4
opt.softtabstop = 4
opt.shiftwidth = 4
opt.expandtab = true
opt.smartindent = true

-- line wrapping
opt.wrap = false

-- cursor line
opt.cursorline = true

-- opt.scrolloff = 8
opt.scrolloff = 8
opt.sidescrolloff = 8

-- appearance
opt.showtabline = 2
opt.conceallevel = 0

-- turn on termguicolors for nightfly colorscheme to work
opt.termguicolors = true
opt.background = "dark"
opt.signcolumn = "yes"

-- backspace
opt.backspace = "indent,eol,start"

-- clipboard
opt.clipboard:append("unnamedplus")

-- split windows
opt.splitright = true
opt.splitbelow = true

-- turn off swapfile
opt.swapfile = false
opt.backup = false

opt.undodir = os.getenv("HOME") .. "/.vim/undodir"
opt.undofile = true

-- opt.updatetime = 50
opt.updatetime = 250

opt.colorcolumn = "80"

opt.shell = "/bin/bash"
