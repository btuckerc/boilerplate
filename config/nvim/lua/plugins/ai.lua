-- AI assistance and productivity tools

return {
    -- AI assistance (Copilot)
    {
        "zbirenbaum/copilot.lua",
        cmd = "Copilot",
        event = "InsertEnter",
        config = function()
            require("copilot").setup({
                suggestion = {
                    enabled = true,
                    auto_trigger = true,
                    keymap = {
                        accept = "<C-g>",
                        next = "<C-]>",
                        prev = "<C-[>",
                    },
                },
                panel = { enabled = false }, -- Use suggestion mode only
            })
        end,
    },
}