return {
  'epwalsh/obsidian.nvim',
  version = '*',
  lazy = true,
  ft = 'markdown',
  dependencies = {
    'nvim-lua/plenary.nvim',
    'hrsh7th/nvim-cmp',
    'nvim-telescope/telescope.nvim',
  },
  cmd = {
    'ObsidianOpen',
    'ObsidianNew',
    'ObsidianQuickSwitch',
    'ObsidianFollowLink',
    'ObsidianBacklinks',
    'ObsidianToday',
    'ObsidianYesterday',
    'ObsidianTomorrow',
    'ObsidianTemplate',
    'ObsidianSearch',
    'ObsidianLink',
    'ObsidianLinkNew',
    'ObsidianTags',
  },
  keys = {
    { "<leader>oo", "<cmd>ObsidianQuickSwitch<cr>", desc = "Quick Switch" },
    { "<leader>od", "<cmd>ObsidianToday<cr>", desc = "Today's Note" },
    { "<leader>oy", "<cmd>ObsidianYesterday<cr>", desc = "Yesterday's Note" },
    { "<leader>ot", "<cmd>ObsidianTomorrow<cr>", desc = "Tomorrow's Note" },
    { "<leader>ob", "<cmd>ObsidianBacklinks<cr>", desc = "Show Backlinks" },
    { "<leader>os", "<cmd>ObsidianSearch<cr>", desc = "Search Notes" },
    { "<leader>ol", "<cmd>ObsidianLink<cr>", desc = "Link Note" },
    { "<leader>on", "<cmd>ObsidianLinkNew<cr>", desc = "Link New Note" },
    { "<leader>og", "<cmd>ObsidianTags<cr>", desc = "Search Tags" },
    { "<leader>ch", "<cmd>ObsidianCheckbox<cr>", desc = "Toggle Checkbox" },
    { "<leader>lb", "<cmd>ObsidianBullet<cr>", desc = "Toggle Bullet" },
    { "<leader>lt", "<cmd>ObsidianTask<cr>", desc = "Toggle Task" },
    { "gf", function() return require('obsidian').util.gf_passthrough() end, expr = true, desc = "Follow Link" },
  },
  config = function()
    local obsidian = require('obsidian')

    -- Set conceallevel for markdown files
    vim.api.nvim_create_autocmd("FileType", {
      pattern = "markdown",
      callback = function()
        vim.opt_local.conceallevel = 2
      end,
    })

    obsidian.setup({
      dir = "~/Documents/00-Vault",
      notes_subdir = "00 - Inbox",
      new_notes_location = "notes_subdir",
      disable_frontmatter = true,

      daily_notes = {
        -- folder = "00 - Inbox/00 - Daily/%Y/%m",
        date_format = "%Y-%m-%d",
        alias_format = "%B %-d, %Y",
        template = "03 - Resources/Templates/Daily Note Template.md",
        default_tags = { "daily-notes" },
        -- Required default field
        default = true
      },

      note_path_func = function(spec)
        if spec.type == "daily" then
          local date = spec.date or os.date("*t")
          local year = tostring(date.year)
          local month = string.format("%02d", date.month)
          local day = string.format("%02d", date.day)
          return string.format("00 - Inbox/00 - Daily/%s/%s/%s-%s-%s",
            year, month, year, month, day)
        end
        return spec.title
      end,

      templates = {
        subdir = "03 - Resources/Templates",
        date_format = "%Y-%m-%d",
        time_format = "%H:%M",
        -- Support for Templater-style syntax
        substitutions = {
          date = function() return os.date("%Y-%m-%d") end,
          time = function() return os.date("%H:%M") end,
          title = function() return vim.fn.expand("%:t:r") end,
        },
      },

      -- Additional features to match Obsidian functionality
      follow_url_func = function(url)
        vim.fn.jobstart({"open", url})  -- Mac OS
      end,

      -- Optional note ID customization
      note_id_func = function(title)
        local suffix = ""
        if title ~= nil then
          suffix = title:gsub(" ", "-"):gsub("[^A-Za-z0-9-]", ""):lower()
        else
          suffix = os.date("%Y%m%d%H%M%S")
        end
        return suffix
      end,

      -- Optional path to ripgrep for faster search
      finder = "telescope.nvim",
      sort_by = "modified",
      sort_reversed = true,
      open_notes_in = "current",

      -- Additional settings for better integration
      use_advanced_uri = true,
      completion_prefix = "@",
      wiki_link_func = function(opts)
        if opts.id == nil then
          return string.format("[[%s]]", opts.label)
        elseif opts.label ~= opts.id then
          return string.format("[[%s|%s]]", opts.id, opts.label)
        else
          return string.format("[[%s]]", opts.id)
        end
      end,

      completion = {
        -- Required default field
        default = true,
        nvim_cmp = true,
        min_chars = 2,
        prepend_note_id = true,
        prepend_note_path = false,
        use_path_only = false,
      },

      -- UI configuration with required fields
      ui = {
        enable = true,
        update_debounce = 200,
        -- Checkboxes configuration
        checkboxes = {
          [" "] = { char = "☐", hl_group = "ObsidianTodo" },
          ["x"] = { char = "☒", hl_group = "ObsidianDone" },
          [">"] = { char = "▶", hl_group = "ObsidianRightArrow" },
          ["~"] = { char = "↻", hl_group = "ObsidianTilde" },
        },
        -- Bullets configuration
        bullets = {
          ["*"] = { char = "•", hl_group = "ObsidianBullet" },
          ["-"] = { char = "–", hl_group = "ObsidianBullet" },
          ["+"] = { char = "⋄", hl_group = "ObsidianBullet" },
        },
        external_link_icon = { char = "", hl_group = "ObsidianExternal" },
        reference_text = { hl_group = "ObsidianRefText" },
        highlight_text = { hl_group = "ObsidianHighlightText" },
        tags = { hl_group = "ObsidianTag" },
        hl_groups = {
          -- These groups are linked to standard highlights below
          ObsidianTodo = { bold = true },
          ObsidianDone = { bold = true },
          ObsidianRightArrow = { bold = true },
          ObsidianTilde = { bold = true },
          ObsidianBullet = { bold = true },
          ObsidianRefText = { underline = true },
          ObsidianExternal = { bold = true },
          ObsidianTag = { italic = true },
          ObsidianHighlightText = {},
        },
      },
    })

    -- Link Obsidian highlights to standard theme highlights for consistency
    vim.cmd([[
      hi def link ObsidianTodo Todo
      hi def link ObsidianDone Comment
      hi def link ObsidianRightArrow Operator
      hi def link ObsidianTilde Special
      hi def link ObsidianBullet Special
      hi def link ObsidianRefText Underlined
      hi def link ObsidianExternal Identifier
      hi def link ObsidianTag Tag
      hi def link ObsidianHighlightText Search
    ]])
  end
}
