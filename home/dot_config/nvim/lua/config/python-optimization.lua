-- Python provider performance optimization
-- Fixes slow Python file loading on macOS (common Neovim issue)

-- Fix #1: Explicitly set Python host program to avoid slow provider search
local python_path = vim.fn.exepath("python3")
if python_path ~= "" then
  vim.g.python3_host_prog = python_path
else
  -- Fallback paths
  local fallback_paths = {
    "/opt/homebrew/bin/python3",
    "/usr/local/bin/python3",
    "/usr/bin/python3",
  }
  for _, path in ipairs(fallback_paths) do
    if vim.fn.executable(path) == 1 then
      vim.g.python3_host_prog = path
      break
    end
  end
end

-- Fix #2: Disable unused providers for better startup performance
vim.g.loaded_python_provider = 0 -- Disable Python 2 provider (deprecated)
vim.g.loaded_ruby_provider = 0 -- Disable Ruby provider if not needed
vim.g.loaded_perl_provider = 0 -- Disable Perl provider if not needed
vim.g.loaded_node_provider = 0 -- Disable Node.js provider if not needed

-- Keep Python 3 provider enabled since we optimized it
-- vim.g.loaded_python3_provider = 0

-- Fix #3: Optimize Python filetype settings for speed
vim.api.nvim_create_autocmd("FileType", {
  pattern = "python",
  callback = function()
    -- Disable the slowest Python runtime options
    vim.bo.include = ""
    vim.bo.define = ""
    vim.bo.includeexpr = ""
    vim.bo.formatexpr = ""

    -- Use faster syntax sync
    vim.cmd("syntax sync minlines=50 maxlines=100")
  end,
})
