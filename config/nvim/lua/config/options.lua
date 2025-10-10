-- Core editor options

local opt = vim.opt

-- Leader key
vim.g.mapleader = " "
vim.g.maplocalleader = " "

-- Core Behavior
opt.clipboard = "unnamedplus"
opt.mouse = "a"
opt.autoread = true
opt.confirm = true

-- UI & Appearance
opt.number = true
opt.relativenumber = true
opt.cursorline = true
opt.signcolumn = "yes"
opt.termguicolors = true
opt.wrap = false
opt.showmatch = true
opt.matchtime = 2
opt.showmode = true

-- Indentation
opt.tabstop = 4
opt.softtabstop = 4
opt.shiftwidth = 4
opt.expandtab = true
opt.smartindent = true

-- Search
opt.ignorecase = true
opt.smartcase = true
opt.hlsearch = true
opt.incsearch = true

-- Performance
opt.lazyredraw = true
opt.synmaxcol = 240
opt.updatetime = 300

-- Files & Backups
opt.undofile = true
opt.backup = false
opt.writebackup = false
opt.swapfile = false

-- Windows
opt.splitbelow = true
opt.splitright = true

-- Scrolling
opt.scrolloff = 8
opt.sidescrolloff = 8

-- Timeouts
opt.timeoutlen = 500

-- Completion
opt.completeopt = { "menuone", "noselect" }
opt.shortmess:append("c")

-- Command line
opt.cmdheight = 1
opt.showcmd = true
opt.showtabline = 0  -- Hide tabline (lualine shows buffer info)
opt.laststatus = 2
opt.ruler = true
opt.title = true
opt.wildmode = { "longest", "full" }

-- Folding
opt.foldcolumn = "1"
opt.foldlevel = 99
opt.foldlevelstart = 99
opt.foldenable = true

-- File handling
opt.encoding = "utf-8"
opt.fileencoding = "utf-8"
opt.formatoptions:remove({ "c", "r", "o" })

-- External tools
opt.grepprg = "rg --vimgrep --smart-case --follow"
opt.grepformat = "%f:%l:%c:%m"

-- Additional features
if vim.fn.has("nvim-0.10") == 1 then
    opt.smoothscroll = true
end