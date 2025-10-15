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
                        next = "<M-]>",     -- Alt+] - cycle to next suggestion
                        prev = "<M-p>",     -- Alt+p - cycle to previous suggestion
                        dismiss = "<C-]>",  -- Ctrl+] - dismiss suggestion (explicitly set to avoid ambiguity)
                    },
                },
                panel = { enabled = false }, -- Use suggestion mode only
            })
        end,
    },
}