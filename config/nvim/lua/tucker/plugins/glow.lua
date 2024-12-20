return {
    'ellisonleao/glow.nvim',
    config = function()
        local glow = require('glow')
        glow.setup({
            style = "dark",
            width = 120,
        })
    end
}
