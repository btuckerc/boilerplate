-- Editor enhancements and functionality

return {
    -- Syntax highlighting
    {
        "nvim-treesitter/nvim-treesitter",
        build = ":TSUpdate",
        event = { "BufReadPre", "BufNewFile" },
        config = function()
            -- Add custom parser for Templ (Go templates)
            local parser_config = require("nvim-treesitter.parsers").get_parser_configs()
            parser_config.templ = {
                install_info = {
                    url = "https://github.com/vrischmann/tree-sitter-templ",
                    files = { "src/parser.c", "src/scanner.c" },
                    branch = "main",
                },
            }

            local uv = vim.loop

            require("nvim-treesitter.configs").setup({
                ensure_installed = {
                    "bash",
                    "c",
                    "html",
                    "lua",
                    "luadoc",
                    "markdown",
                    "markdown_inline",
                    "vim",
                    "vimdoc",
                    "javascript",
                    "typescript",
                    "python",
                    "go",
                    "rust",
                    "json",
                    "yaml",
                    "toml",
                    "dockerfile",
                    "terraform",
                    "sql",
                    "jsdoc",
                    "templ",
                },
                auto_install = true,
                highlight = {
                    enable = true,
                    disable = function(lang, buf)
                        -- Disable HTML parsing as it can be problematic
                        if lang == "html" then
                            return true
                        end

                        -- Performance optimization: disable for large files
                        local max_filesize = 100 * 1024 -- 100 KB
                        local ok, stats = pcall(uv.fs_stat, vim.api.nvim_buf_get_name(buf))
                        if ok and stats and stats.size > max_filesize then
                            vim.notify(
                                "File larger than 100KB, Treesitter disabled for performance",
                                vim.log.levels.WARN,
                                { title = "Treesitter" }
                            )
                            return true
                        end

                        -- Check line count for typing performance
                        local lines = vim.api.nvim_buf_line_count(buf)
                        if lines > 2000 then
                            return true
                        end
                    end,
                    -- Better Markdown rendering with both Treesitter and Vim regex
                    additional_vim_regex_highlighting = { "markdown" },
                },
                -- Optimize incremental selection for performance
                incremental_selection = {
                    enable = true,
                    disable = function(lang, buf)
                        local lines = vim.api.nvim_buf_line_count(buf)
                        return lines > 1000  -- Disable for large files
                    end,
                },
                indent = { enable = true },
            })
        end,
    },

    -- Autopairs
    {
        "windwp/nvim-autopairs",
        event = "InsertEnter",
        config = function()
            require("nvim-autopairs").setup({})
        end,
    },

    -- Comments
    {
        "numToStr/Comment.nvim",
        event = { "BufReadPre", "BufNewFile" },
        config = function()
            require("Comment").setup()
        end,
    },

    -- Undo tree
    {
        "mbbill/undotree",
        cmd = "UndotreeToggle",
        keys = {
            { "<leader>u", "<cmd>UndotreeToggle<cr>", desc = "Toggle undotree" },
        },
    },

    -- Vim practice game
    {
        "theprimeagen/vim-be-good",
        dependencies = {
            "nvim-lua/plenary.nvim"
        },
        config = function()
        end
    },
}