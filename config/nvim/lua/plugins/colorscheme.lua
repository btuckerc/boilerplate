-- Custom colorscheme configuration

return {
    {
        dir = vim.fn.stdpath("config") .. "/lua/themes",
        priority = 1000,
        lazy = false,
        config = function()
            local currenttheme = require("themes.current-theme")

            -- Initialize transparency state
            vim.g.transparent_enabled = true

            -- Function to apply theme with transparency
            local function apply_transparent_theme()
                currenttheme.apply(true)
            end

            -- Apply immediately
            apply_transparent_theme()

            -- Re-apply after plugins load to override any opaque backgrounds
            vim.api.nvim_create_autocmd({ "VimEnter", "ColorScheme" }, {
                callback = function()
                    vim.schedule(apply_transparent_theme)
                end,
            })

            -- Also apply when entering buffers to ensure consistency
            vim.api.nvim_create_autocmd({ "BufWinEnter", "WinEnter" }, {
                callback = function()
                    -- Only reapply on first buffer enter to avoid performance issues
                    if not vim.g.theme_applied_once then
                        vim.g.theme_applied_once = true
                        vim.schedule(apply_transparent_theme)
                    end
                end,
                once = true,
            })
        end,
    },
}