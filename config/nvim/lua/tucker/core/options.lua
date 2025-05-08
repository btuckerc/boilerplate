local opt = vim.opt
local g = vim.g

-- Set file browser style
g.netrw_liststyle = 3

-- Line numbers and relative numbers
opt.number = true
opt.relativenumber = true

-- Indentation
opt.tabstop = 4
opt.softtabstop = 4
opt.shiftwidth = 4
opt.expandtab = true
opt.smartindent = true

-- Line wrapping
opt.wrap = false

-- Search settings
opt.ignorecase = true
opt.smartcase = true
opt.hlsearch = true
opt.incsearch = true

-- Clipboard
opt.clipboard:append("unnamedplus")

-- Undo settings
opt.undofile = true
opt.undodir = os.getenv("HOME") .. "/.vim/undodir"

-- Backup settings
opt.backup = false
opt.writebackup = false
opt.swapfile = false

-- Cursor settings
opt.cursorline = true
opt.cursorcolumn = false

-- Sign column
opt.signcolumn = "yes"

-- Split behavior
opt.splitbelow = true
opt.splitright = true

-- Terminal colors
opt.termguicolors = true

-- Command line
opt.cmdheight = 1
opt.showcmd = true
opt.showmode = true

-- Completion settings
opt.completeopt = { "menuone", "noselect" }
opt.wildmode = { "longest", "full" }

-- Scrolling
opt.scrolloff = 8
opt.sidescrolloff = 8

-- Timeouts
opt.timeoutlen = 500
opt.updatetime = 300

-- Mouse support
opt.mouse = "a"

-- File encoding
opt.encoding = "utf-8"
opt.fileencoding = "utf-8"

-- Format options
opt.formatoptions:remove({ "c", "r", "o" })

-- Folding
opt.foldmethod = "indent"
opt.foldlevel = 99
opt.foldenable = true

-- Performance
opt.lazyredraw = true
opt.synmaxcol = 240

-- UI
opt.showmatch = true
opt.matchtime = 2
opt.showtabline = 2
opt.laststatus = 2
opt.ruler = true
opt.title = true
opt.titlelen = 0
opt.titlestring = "%F"

-- Buffer settings
opt.hidden = true
opt.autoread = true
opt.autowrite = true

-- Command history
opt.history = 1000

-- Spell checking
opt.spell = false
opt.spelllang = { "en_us" }

-- Grep settings
opt.grepprg = "rg --vimgrep --smart-case --follow"
opt.grepformat = "%f:%l:%c:%m"
