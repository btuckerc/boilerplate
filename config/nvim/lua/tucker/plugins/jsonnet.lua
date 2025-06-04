return {
    "google/vim-jsonnet",
    ft = "jsonnet",
    config = function()
        vim.g.jsonnet_fmt_on_save = 1 -- Enable formatting on save (if desired)
    end,
}
