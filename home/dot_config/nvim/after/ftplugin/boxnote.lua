-- nvim/after/ftplugin/boxnote.lua

-- This script is triggered when a file with the .boxnote extension is opened.
-- It reads the JSON content of the note, converts it to Markdown,
-- and displays it in a new, read-only scratch buffer.

local M = {}

-- Recursively traverses the Box Note JSON AST and converts it to Markdown.
function M.json_to_markdown(nodes)
  local markdown_lines = {}

  local function process_node(node)
    local node_type = node.type
    local text_content = ""

    if node.content then
      for _, child in ipairs(node.content) do
        text_content = text_content .. process_node(child)
      end
    elseif node.text then
      text_content = node.text
    end

    -- Apply marks (bold, italic, etc.)
    if node.marks then
      for i = #node.marks, 1, -1 do
        local mark = node.marks[i]
        if mark.type == "strong" then
          text_content = "**" .. text_content .. "**"
        elseif mark.type == "em" then
          text_content = "*" .. text_content .. "*"
        elseif mark.type == "underline" then
          text_content = "__" .. text_content .. "__"
        elseif mark.type == "strikethrough" then
          text_content = "~~" .. text_content .. "~~"
        elseif mark.type == "link" then
          text_content = "[" .. text_content .. "](" .. mark.attrs.href .. ")"
        end
      end
    end

    if node_type == "paragraph" then
      return text_content .. "\n\n"
    elseif node_type == "heading" then
      return string.rep("#", node.attrs.level) .. " " .. text_content .. "\n\n"
    elseif node_type == "bullet_list" then
      return text_content
    elseif node_type == "ordered_list" then
      local ordered_list_items = {}
      for i, child in ipairs(node.content) do
        table.insert(ordered_list_items, i .. ". " .. process_node(child))
      end
      return table.concat(ordered_list_items, "")
    elseif node_type == "list_item" then
      return "* " .. text_content
    elseif node_type == "check_list" then
      return text_content
    elseif node_type == "check_list_item" then
      if node.attrs.checked then
        return "- [x] " .. text_content
      else
        return "- [ ] " .. text_content
      end
    elseif node_type == "code_block" then
      local lang = node.attrs.language or ""
      return "```" .. lang .. "\n" .. text_content .. "\n```\n\n"
    elseif node_type == "blockquote" then
      return "> " .. text_content:gsub("\n\n", "\n> ")
    elseif node_type == "horizontal_rule" then
      return "\n---\n\n"
    elseif node_type == "image" then
      local alt = node.attrs.alt or node.attrs.fileName or "image"
      local src = node.attrs.boxSharedLink or "local image"
      return "![" .. alt .. "](" .. src .. ")\n\n"
    elseif node_type == "text" then
      return text_content
    else
      return text_content
    end
  end

  for _, node in ipairs(nodes) do
    table.insert(markdown_lines, process_node(node))
  end

  return table.concat(markdown_lines, "")
end

-- Renders the content of the current .boxnote buffer as Markdown.
function M.render_boxnote()
  -- Make sure cjson is available
  local cjson_ok, cjson = pcall(require, "cjson.safe")
  if not cjson_ok then
    vim.notify("cjson library not found. Please install it.", vim.log.levels.ERROR)
    return
  end

  local original_bufnr = vim.api.nvim_get_current_buf()
  local lines = vim.api.nvim_buf_get_lines(original_bufnr, 0, -1, false)
  local content = table.concat(lines, "\n")

  local ok, data = pcall(cjson.decode, content)
  if not ok or type(data) ~= "table" or not data.doc or not data.doc.content then
    vim.notify("Could not parse .boxnote file. It may be an old format or corrupted.", vim.log.levels.ERROR)
    return
  end

  local markdown_content = M.json_to_markdown(data.doc.content)

  -- Create a new scratch buffer to display the Markdown
  local new_bufnr = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(new_bufnr, 0, -1, false, vim.split(markdown_content, "\n"))

  -- Set buffer options
  vim.bo[new_bufnr].filetype = "markdown"
  vim.bo[new_bufnr].buftype = "nofile"
  vim.bo[new_bufnr].bufhidden = "hide"
  vim.bo[new_bufnr].swapfile = false
  vim.bo[new_bufnr].readonly = true

  -- Set buffer name
  local original_filename = vim.fn.fnamemodify(vim.api.nvim_buf_get_name(original_bufnr), ":t")
  vim.api.nvim_buf_set_name(new_bufnr, "BoxNote: " .. original_filename)

  -- Open the new buffer in the current window
  vim.api.nvim_set_current_buf(new_bufnr)
end

-- Run the render function automatically
M.render_boxnote()

return M
