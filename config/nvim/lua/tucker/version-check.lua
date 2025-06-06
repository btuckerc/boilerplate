local M = {}

-- Function to check if a newer version of Neovim is available
function M.check_nvim_version()
  local current_version = vim.version()

  -- Don't check for updates if on a development version
  if current_version.prerelease then
    return
  end

  local function parse_version(v_str)
    local major, minor, patch = v_str:match("(%d+)%.(%d+)%.(%d+)")
    if major then
      return {
        major = tonumber(major),
        minor = tonumber(minor),
        patch = tonumber(patch),
      }
    end
    return nil
  end

  local function is_newer(latest, current)
    if latest.major > current.major then return true end
    if latest.major < current.major then return false end
    if latest.minor > current.minor then return true end
    if latest.minor < current.minor then return false end
    if latest.patch > current.patch then return true end
    return false
  end

  local function notify_update(latest_str, install_cmd)
    local latest_version = parse_version(latest_str)
    if not latest_version then return end

    if is_newer(latest_version, current_version) then
      local current_version_str = string.format("%d.%d.%d", current_version.major, current_version.minor, current_version.patch)
      -- Wrap notification in vim.schedule to prevent "E5560: nvim_echo must not be called in a fast event context"
      vim.schedule(function()
        local msg = string.format(
          "New Neovim version available: %s (you have %s)\nUpdate with: %s",
          latest_str,
          current_version_str,
          install_cmd or "See https://github.com/neovim/neovim/releases/latest"
        )
        vim.notify(msg, vim.log.levels.INFO, {
          title = "Neovim Update Available",
          timeout = 10000,
        })
      end)
    end
  end

  -- Use plenary.curl to check for updates via GitHub API
  local has_plenary, curl = pcall(require, "plenary.curl")
  if not has_plenary then return end

  curl.get({
    url = "https://api.github.com/repos/neovim/neovim/releases/latest",
    headers = {
      Accept = "application/vnd.github.v3+json",
      ["User-Agent"] = "neovim-version-check",
    },
    callback = function(response)
      if response and response.status == 200 and response.body then
        local ok, decoded = pcall(vim.json.decode, response.body)
        if ok and decoded and decoded.tag_name then
          local latest_version_str = decoded.tag_name:gsub("v", "")
          notify_update(latest_version_str, "brew upgrade neovim")
        end
      end
    end,
  })
end

return M
