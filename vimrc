" Vimrc: A sensible and modern configuration for Vim

" General Settings
set nocompatible               " Disable compatibility with older vi
filetype off                   " Temporarily turn off filetype to load plugins
syntax on                      " Enable syntax highlighting
set filetype plugin indent on  " Enable filetype detection, plugins, and auto-indenting

" Visual and Usability Enhancements
set number                     " Show line numbers
set relativenumber             " Show relative line numbers
set cursorline                 " Highlight the current line
set showmatch                  " Highlight matching brackets
set wrap                       " Enable line wrapping
set scrolloff=5                " Keep 5 lines visible above/below the cursor
set sidescrolloff=5            " Keep 5 columns visible to the left/right of the cursor

" Indentation and Tabs
set expandtab                  " Convert tabs to spaces
set tabstop=4                  " Number of spaces that a tab represents
set shiftwidth=4               " Number of spaces for indentation
set softtabstop=4              " Number of spaces when pressing Tab
set autoindent                 " Automatically indent new lines
set smartindent                " Smart auto-indentation for programming

" Searching
set hlsearch                   " Highlight all matches
set incsearch                  " Incremental search
set ignorecase                 " Case-insensitive searching
set smartcase                  " Case-sensitive if search includes uppercase

" Performance
set lazyredraw                 " Improve performance for macros and scripts
set timeoutlen=500             " Reduce timeout for mapped sequences (ms)

" Backup and Undo
set backup                     " Enable backups
set backupdir=~/.vim/backups   " Directory for backup files
set undofile                   " Enable undo files
set undodir=~/.vim/undodir     " Directory for undo files
set swapfile                   " Enable swap files
set directory=~/.vim/swapfiles " Directory for swap files

" Better Splits
set splitbelow                 " Horizontal splits open below
set splitright                 " Vertical splits open to the right

" Status Bar and UI
set laststatus=2               " Always show the status line
set ruler                      " Show cursor position in the status line
set showcmd                    " Show incomplete commands in the status line
set wildmenu                   " Enhanced command-line completion

" Clipboard and Mouse
set clipboard=unnamedplus      " Use the system clipboard
set mouse=a                    " Enable mouse support in all modes

" Colors and Appearance
set termguicolors              " Enable true color support
colorscheme slate             " Use a default colorscheme; replace with your favorite

" Mappings (Shortcuts)
noremap <C-s> :w<CR>           " Ctrl-s to save the current file
noremap <C-q> :q!<CR>          " Ctrl-q to force quit without saving
nnoremap <C-j> <C-W>j          " Ctrl-j to move to the split below
nnoremap <C-k> <C-W>k          " Ctrl-k to move to the split above
nnoremap <C-h> <C-W>h          " Ctrl-h to move to the left split
nnoremap <C-l> <C-W>l          " Ctrl-l to move to the right split

" Plugin Management (vim-plug example)
call plug#begin('~/.vim/plugged')

" Essential Plugins
Plug 'junegunn/fzf', { 'do': { -> fzf#install() } } " Fuzzy file finder
Plug 'scrooloose/nerdtree'                          " File tree explorer
Plug 'airblade/vim-gitgutter'                      " Git diff in the gutter
Plug 'tpope/vim-fugitive'                          " Git integration
Plug 'sheerun/vim-polyglot'                        " Language pack
Plug 'jiangmiao/auto-pairs'                        " Auto-close brackets
Plug 'preservim/nerdcommenter'                     " Easy code commenting

" Optional Plugins
Plug 'vim-airline/vim-airline'                     " Status bar
Plug 'vim-airline/vim-airline-themes'              " Themes for vim-airline
Plug 'ryanoasis/vim-devicons'                      " File icons for plugins
Plug 'easymotion/vim-easymotion'                   " Motion shortcuts

call plug#end()

" Plugin-Specific Configurations
let g:airline#extensions#tabline#enabled = 1       " Enable airline tabline
let g:NERDTreeShowHidden = 1                       " Show hidden files in NERDTree
let g:NERDSpaceDelims = 1                          " Space after comment delimiters