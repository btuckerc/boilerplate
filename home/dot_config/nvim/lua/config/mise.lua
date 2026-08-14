local M = {}

local function split_path(path)
  local entries = {}

  for entry in string.gmatch(path or "", "([^:]+)") do
    entries[#entries + 1] = entry
  end

  return entries
end

function M.prefer_install_dirs(patterns)
  local path = vim.env.PATH or ""
  local entries = split_path(path)

  if #entries == 0 then
    return
  end

  local prioritized = {}
  local seen = {}

  for _, pattern in ipairs(patterns) do
    for _, entry in ipairs(entries) do
      if entry:find("/.local/share/mise/installs/", 1, true) and entry:find(pattern, 1, true) then
        if not seen[entry] then
          prioritized[#prioritized + 1] = entry
          seen[entry] = true
        end
      end
    end
  end

  if #prioritized == 0 then
    return
  end

  local normalized = vim.list_extend({}, prioritized)
  for _, entry in ipairs(entries) do
    if not seen[entry] then
      normalized[#normalized + 1] = entry
      seen[entry] = true
    end
  end

  vim.env.PATH = table.concat(normalized, ":")
end

return M
