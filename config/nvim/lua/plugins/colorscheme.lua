-- Custom colorscheme configuration

return {
    {
        dir = vim.fn.stdpath("config") .. "/lua/themes",
        priority = 1000,
        config = function()
            local currenttheme = require("themes.current-theme")
            currenttheme.apply(true)

            -- Ensure theme persists after other plugins load
            vim.api.nvim_create_autocmd({ "ColorScheme", "VimEnter" }, {
                callback = function()
                    vim.defer_fn(function()
                        currenttheme.apply(true)
                    end, 100) -- Slight delay to ensure it runs after other plugins
                end,
            })
        end,
    },
}