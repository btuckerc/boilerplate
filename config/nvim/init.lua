-- Minimal, fast, and XDG-compliant Neovim setup

-- Bootstrap lazy.nvim
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
    vim.fn.system({
        "git",
        "clone",
        "--filter=blob:none",
        "https://github.com/folke/lazy.nvim.git",
        "--branch=stable",
        lazypath,
    })
end
vim.opt.rtp:prepend(lazypath)

-- Load core configuration
require("config.options")
require("config.keymaps")
require("config.autocmds")
require("config.python-optimization")
require("config.performance-utils")
require("config.typing-performance")

-- Setup plugins
require("lazy").setup("plugins", {
    defaults = {
        lazy = true, -- Lazy load by default
        version = false, -- Don't use version constraints for git plugins
    },
    checker = {
        enabled = true,
        notify = false,
    },
    change_detection = {
        notify = false,
    },
    performance = {
        rtp = {
            disabled_plugins = {
                "gzip",
                "matchit",
                "matchparen",
                "netrwPlugin",
                "tarPlugin",
                "tohtml",
                "tutor",
                "zipPlugin",
                "2html_plugin",
                "getscript",
                "getscriptPlugin",
                "logipat",
                "rrhelper",
                "spellfile_plugin",
                "vimball",
                "vimballPlugin",
            },
        },
    },
    ui = {
        border = "rounded",
    },
})