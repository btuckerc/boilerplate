-- Enable Neovim 0.12 UI2 early so startup errors don't trigger hit-enter spam.
if vim.fn.has("nvim-0.12") == 1 then
  local ok, ui2 = pcall(require, "vim._core.ui2")
  if ok then
    ui2.enable()
  end
end

-- Bootstrap lazy.nvim
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
local uv = vim.uv
if not uv.fs_stat(lazypath) then
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

-- Setup plugins
require("lazy").setup("plugins", {
  defaults = {
    lazy = true, -- Lazy load by default
    version = false, -- Don't use version constraints for git plugins
  },
  checker = {
    enabled = false,
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
