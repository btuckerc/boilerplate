return {
    'epwalsh/obsidian.nvim',
    version = '*',
    lazy = true,
    ft = 'markdown',
    dependencies = {
        {'nvim-lua/plenary.nvim', opt = true},
    },
    cmd = { 'ObsidianToday' },
    config = function()
        local obsidian = require('obsidian')
        vim.opt_local.conceallevel = 2
        obsidian.setup({
            workspaces = {
                {
                    name = "Tucker",
                    path = "/Users/tucker/Documents/00-Vault",
                },
            },
            notes_subdir = "00 - Inbox",
            new_notes_location = "notes_subdir",
            disable_frontmatter = true,
            daily_notes = {
                -- Optional, if you keep daily notes in a separate directory.
                folder = "02 - Areas/00 - Daily",
                -- Optional, if you want to change the date format for the ID of daily notes.
                date_format = "%Y-%m-%d",
                -- Optional, if you want to change the date format of the default alias of daily notes.
                alias_format = "%B %-d, %Y",
                -- Optional, default tags to add to each new daily note created.
                default_tags = { "daily-notes" },
                -- Optional, if you want to automatically insert a template from your template directory like 'daily.md'
                template = nil
            },
            -- Uncomment and customize this function if you want to use a custom note ID generator
            -- note_id_func = function(title)
            --   local suffix = ""
            --   local current_datetime = os.date("!%Y-%m-%d-%H%M%S", os.time() - 5*3600)
            --   if title ~= nil then
            --     suffix = title:gsub(" ", "-"):gsub("[^A-Za-z0-9-]", ""):lower()
            --   else
            --     for _ = 1, 4 do
            --       suffix = suffix .. string.char(math.random(65, 90))
            --     end
            --   end
            --   return current_datetime .. "_" .. suffix
            -- end,
            mappings = {
                ["gf"] = {
                    action = function()
                        return obsidian.util.gf_passthrough()
                    end,
                    opts = { noremap = false, expr = true, buffer = true },
                },
                ["<leader>ti"] = {
                    action = function()
                        return obsidian.util.toggle_checkbox()
                    end,
                    opts = { buffer = true },
                },
            },
            completion = {
                nvim_cmp = true,
                min_chars = 2,
            },
            ui = {
                checkboxes = {},
                bullets = {},
            },
        })
    end
}

