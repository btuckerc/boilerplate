-- options.lua
--
-- Core editor options for Neovim.

local opt = vim.opt

-- SECTION: Behavior
opt.clipboard:append("unnamedplus") -- Use system clipboard
opt.mouse = "a" -- Enable mouse support
opt.hidden = true -- Allow buffer switching without saving
opt.autoread = true -- Automatically re-read files when changed outside of Neovim

-- SECTION: Appearance
opt.number = true -- Show line numbers
opt.relativenumber = true -- Show relative line numbers
opt.cursorline = true -- Highlight the current line
opt.signcolumn = "yes" -- Always show the sign column
opt.termguicolors = true -- Enable true color support
opt.wrap = false -- Disable line wrapping
opt.showmatch = true -- Highlight matching brackets
opt.matchtime = 2 -- Time in tenths of a second to show matching bracket

-- SECTION: Indentation
opt.tabstop = 4 -- Number of spaces a <Tab> in the file counts for
opt.softtabstop = 4 -- Number of spaces to insert for a <Tab>
opt.shiftwidth = 4 -- Number of spaces to use for each step of (auto)indent
opt.expandtab = true -- Use spaces instead of tabs
opt.smartindent = true -- Smarter auto-indenting for new lines

-- SECTION: Search
opt.ignorecase = true -- Ignore case in search patterns
opt.smartcase = true -- Override 'ignorecase' if the search pattern contains upper case letters
opt.hlsearch = true -- Highlight all matches on search
opt.incsearch = true -- Show search results as you type

-- SECTION: Performance
opt.lazyredraw = true -- Don't redraw screen during macros and other operations
opt.synmaxcol = 240 -- Max column for syntax highlighting

-- SECTION: Backups & History
opt.undofile = true -- Enable persistent undo
opt.undodir = vim.fn.stdpath("data") .. "/undodir" -- Set undo directory
opt.backup = false -- Disable backup files
opt.writebackup = false -- Disable backup files before writing
opt.swapfile = false -- Disable swap files
opt.history = 1000 -- Set command history size

-- SECTION: Window & Command Line
opt.splitbelow = true -- Force new splits to appear below the current window
opt.splitright = true -- Force new vertical splits to appear to the right of the current window
opt.cmdheight = 1 -- Set command line height
opt.showcmd = true -- Show command in the last line of the screen
opt.showmode = true -- Show the current mode
opt.showtabline = 2 -- Always show the tabline
opt.laststatus = 2 -- Always show the status line
opt.ruler = true -- Show cursor position
opt.title = true -- Set terminal title
opt.titlelen = 0 -- Use full file path for title
opt.titlestring = "%F" -- Set title string to full file path

-- SECTION: Completion
opt.completeopt = { "menuone", "noselect" } -- Set completion options
opt.wildmode = { "longest", "full" } -- Command-line completion mode

-- SECTION: Scrolling
opt.scrolloff = 8 -- Minimum number of screen lines to keep above and below the cursor
opt.sidescrolloff = 8 -- Minimum number of screen columns to keep to the left and right of the cursor

-- SECTION: Timeouts
opt.timeoutlen = 500 -- Time in milliseconds to wait for a mapped sequence to complete
opt.updatetime = 300 -- Time in milliseconds for 'CursorHold' event

-- SECTION: File Handling
opt.encoding = "utf-8" -- Set character encoding
opt.fileencoding = "utf-8" -- Set file character encoding
opt.formatoptions:remove({ "c", "r", "o" }) -- Modify format options

-- SECTION: Folding
opt.foldlevel = 99 -- Don't auto-fold anything on file open
opt.foldenable = true -- Enable folding

-- SECTION: Spell Checking
opt.spell = false -- Disable spell checking by default
opt.spelllang = { "en_us" } -- Set default spell language

-- SECTION: External Tools
opt.grepprg = "rg --vimgrep --smart-case --follow" -- Use ripgrep for grep
opt.grepformat = "%f:%l:%c:%m" -- Define grep format
