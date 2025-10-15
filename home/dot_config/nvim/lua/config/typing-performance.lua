-- Typing performance and buffer responsiveness optimizations

-- Critical timing settings for typing responsiveness
vim.opt.updatetime = 250        -- Balanced for responsiveness without excessive overhead
vim.opt.timeout = true          -- Enable timeout for key sequences
vim.opt.timeoutlen = 400        -- Key sequence timeout (default 1000ms is too slow)
vim.opt.ttimeout = true         -- Enable timeout for terminal key codes
vim.opt.ttimeoutlen = 50        -- Terminal timeout (increased from 10 to fix Esc delay)

-- Buffer and display optimizations
vim.opt.lazyredraw = false      -- Don't lazy redraw (can cause issues in modern Neovim)
vim.opt.ttyfast = true          -- Faster terminal connection
vim.opt.redrawtime = 10000      -- Max time for syntax highlighting (10 seconds)

-- Optimize treesitter for large files and comments
vim.api.nvim_create_autocmd("BufReadPost", {
    callback = function()
        local lines = vim.api.nvim_buf_line_count(0)
        local file_size = vim.fn.getfsize(vim.fn.expand("%"))

        -- For files with many lines or large size, optimize treesitter
        if lines > 1000 or file_size > 100 * 1024 then  -- 100KB
            -- Limit treesitter sync for large files
            vim.cmd("syntax sync minlines=50 maxlines=500")

            -- Disable some treesitter features that cause input lag
            local ok, ts_config = pcall(require, "nvim-treesitter.configs")
            if ok then
                -- Disable incremental selection for large files
                vim.b.ts_disable_incremental_selection = true
            end
        end
    end,
})

-- Optimize LSP for typing performance
vim.api.nvim_create_autocmd("LspAttach", {
    callback = function(args)
        local client = vim.lsp.get_client_by_id(args.data.client_id)
        if not client then return end

        -- Reduce LSP diagnostics frequency for better typing performance
        -- Use pcall to safely configure diagnostics
        pcall(function()
            vim.diagnostic.config({
                update_in_insert = false,  -- Don't update diagnostics while typing
                signs = {
                    priority = 8,  -- Lower priority to avoid frequent redraws
                },
            })
        end)

        -- Optimize inlay hints (if supported)
        if client.server_capabilities.inlayHintProvider then
            pcall(function()
                vim.lsp.inlay_hint.enable(false, { bufnr = args.buf })  -- Disable by default for performance
            end)
        end
    end,
})

-- Optimize cursor movement and search highlighting
vim.api.nvim_create_autocmd("CmdlineEnter", {
    pattern = { "/", "?" },
    callback = function()
        vim.opt.hlsearch = true
    end,
})

vim.api.nvim_create_autocmd("CmdlineLeave", {
    pattern = { "/", "?" },
    callback = function()
        vim.defer_fn(function()
            vim.cmd("nohlsearch")
        end, 3000)  -- Auto-clear search highlight after 3 seconds
    end,
})

-- Debounce CursorHold events to prevent excessive firing
local cursor_hold_timer = nil
vim.api.nvim_create_autocmd("CursorMoved", {
    callback = function()
        if cursor_hold_timer then
            cursor_hold_timer:stop()
        end
        cursor_hold_timer = vim.defer_fn(function()
            -- This helps plugins that rely on CursorHold but prevents spam
            vim.api.nvim_exec_autocmds("User", { pattern = "CursorHoldDeferred" })
        end, vim.opt.updatetime:get())
    end,
})

-- Memory and swap optimizations
vim.opt.directory = vim.fn.stdpath("state") .. "/swap"  -- Centralize swap files
vim.opt.updatecount = 100       -- Write swap file after 100 characters (default 200)

