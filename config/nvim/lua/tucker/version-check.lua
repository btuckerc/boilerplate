local M = {}

-- Function to check if a newer version of Neovim is available
function M.check_nvim_version()
  local current_version = vim.version()
  local current_version_str = string.format("%d.%d.%d", current_version.major, current_version.minor, current_version.patch)

  local function notify_update(latest, install_cmd)
    -- Wrap notification in vim.schedule to prevent "E5560: nvim_echo must not be called in a fast event context"
    vim.schedule(function()
      if latest and latest ~= current_version_str then
        local msg = string.format(
          "New Neovim version available: %s (you have %s)\nUpdate with: %s",
          latest,
          current_version_str,
          install_cmd or "brew upgrade neovim"
        )
        vim.notify(msg, vim.log.levels.INFO, {
          title = "Neovim Update Available",
          timeout = 10000,
        })
      end
    end)
  end

  -- Check if we're on macOS and if Homebrew is installed
  local is_mac = vim.fn.has("mac") == 1
  local has_brew = vim.fn.executable("brew") == 1

  -- First try to check via Homebrew if on Mac and Homebrew is installed
  if is_mac and has_brew then
    -- Check if Neovim was installed via Homebrew
    vim.fn.jobstart("brew list --versions neovim", {
      on_stdout = function(_, data)
        if data and #data > 0 and data[1] ~= "" then
          -- Neovim is installed via Homebrew, check for updates
          vim.fn.jobstart("brew outdated --verbose | grep neovim", {
            on_stdout = function(_, update_data)
              if update_data and #update_data > 0 and update_data[1] ~= "" then
                -- Extract the available version
                local version_match = string.match(update_data[1], "neovim%s+(%S+)%s+")
                if version_match then
                  notify_update(version_match, "brew upgrade neovim")
                  return
                end
              end
            end,
            on_exit = function(_, exit_code)
              -- If exit code is non-zero or no output, it means no updates available
              -- or we couldn't check properly, so fall back to GitHub API
              if exit_code ~= 0 then
                check_via_github()
              end
            end
          })
          return
        end
        -- Neovim is not installed via Homebrew, fall back to GitHub API
        check_via_github()
      end,
      on_exit = function(_, exit_code)
        -- If exit code is non-zero, it means Neovim is not managed by Homebrew
        if exit_code ~= 0 then
          check_via_github()
        end
      end
    })
  else
    -- Not on Mac or no Homebrew, use GitHub API
    check_via_github()
  end

  -- Check for updates via GitHub API
  function check_via_github()
    -- Use plenary.curl if available, otherwise use system curl
    local has_plenary, curl = pcall(require, "plenary.curl")

    if has_plenary then
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
              local latest_version = decoded.tag_name:gsub("v", "")
              notify_update(latest_version, "See https://github.com/neovim/neovim/releases/latest")
            end
          end
        end,
      })
    else
      -- Fallback to system curl if plenary isn't available
      vim.schedule(function()
        vim.fn.jobstart("curl -s https://api.github.com/repos/neovim/neovim/releases/latest", {
          on_stdout = function(_, data)
            if data and #data > 0 and data[1] ~= "" then
              local ok, decoded = pcall(vim.json.decode, table.concat(data, ""))
              if ok and decoded and decoded.tag_name then
                local latest_version = decoded.tag_name:gsub("v", "")
                notify_update(latest_version, "See https://github.com/neovim/neovim/releases/latest")
              end
            end
          end,
        })
      end)
    end
  end
end

return M
