-- Startup functions for Neovim
local M = {}

-- Check for Neovim updates on startup
local function check_nvim_updates()
  -- Delay checking to not slow down startup
  vim.defer_fn(function()
    local version_check = require("tucker.version-check")
    version_check.check_nvim_version()
  end, 3000)  -- Check after 3 seconds
end

-- Initialize startup functions
function M.setup()
  check_nvim_updates()
end

return M
