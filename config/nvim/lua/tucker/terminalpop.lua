-- Terminal Pop Configuration
-- Provides floating terminal functionality

local M = {}

-- Terminal buffer number
local term_buf = nil

-- Function to create a floating terminal
function M.create()
    -- Create a new buffer
    local buf = vim.api.nvim_create_buf(false, true)
    term_buf = buf

    -- Get the current window dimensions
    local width = vim.api.nvim_get_option("columns")
    local height = vim.api.nvim_get_option("lines")

    -- Calculate the floating window size and position
    local win_height = math.ceil(height * 0.8)
    local win_width = math.ceil(width * 0.8)
    local row = math.ceil((height - win_height) / 2)
    local col = math.ceil((width - win_width) / 2)

    -- Create the floating window
    local opts = {
        style = "minimal",
        relative = "editor",
        width = win_width,
        height = win_height,
        row = row,
        col = col,
        border = "rounded",
    }

    local win = vim.api.nvim_open_win(buf, true, opts)
    vim.api.nvim_command("terminal")
    vim.api.nvim_command("startinsert")
end

-- Function to toggle the floating terminal
function M.toggle()
    if term_buf and vim.api.nvim_buf_is_valid(term_buf) then
        vim.api.nvim_buf_delete(term_buf, { force = true })
        term_buf = nil
    else
        M.create()
    end
end

return M
