#!/bin/bash
# Copyright (c) 2024 Tucker Craig
# See LICENSE file for full license details.

# Get the absolute directory of the current script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common utilities
source "$SCRIPT_DIR/common.sh"

# Function to show usage
show_usage() {
    cat << EOF
NAME
    $(basename "$0") - Convert Kitty terminal theme to Neovim Lua theme

SYNOPSIS
    $(basename "$0") <input-kitty-theme.conf> <output-nvim-theme.lua>

DESCRIPTION
    Converts a Kitty terminal theme configuration file to a Neovim Lua theme file.
    Maps color definitions and creates appropriate highlight groups.

ARGUMENTS
    input-kitty-theme.conf
        Input Kitty theme configuration file

    output-nvim-theme.lua
        Output Neovim Lua theme file

EXAMPLES
    $(basename "$0") mytheme.conf mytheme.lua
        Convert mytheme.conf to mytheme.lua

    $(basename "$0") ~/.config/kitty/themes/dark.conf ~/.config/nvim/lua/themes/dark.lua
        Convert Kitty theme to Neovim theme with full paths
EOF
    exit 1
}

# Show usage if help is requested
[[ "$1" == "-h" || "$1" == "--help" ]] && show_usage

# Validate arguments
if [[ $# -ne 2 ]]; then
    echo "Error: Exactly two arguments required"
    show_usage
fi

INPUT_FILE="$1"
OUTPUT_FILE="$2"

if [[ ! -f "$INPUT_FILE" ]]; then
    echo "Error: Input file '$INPUT_FILE' does not exist"
    exit 1
fi

if [[ -f "$OUTPUT_FILE" ]]; then
    read -p "Output file '$OUTPUT_FILE' already exists. Overwrite? [y/N] " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
fi

# Create output directory if it doesn't exist
OUTPUT_DIR=$(dirname "$OUTPUT_FILE")
mkdir -p "$OUTPUT_DIR" || { echo "Error: Failed to create output directory"; exit 1; }

# Initialize output file
{
    echo "-- Converted Neovim theme"
    echo "-- Source: $(basename "$INPUT_FILE")"
    echo "-- Generated by $(basename "$0")"
    echo "-- Date: $(date)"
    echo
    echo "local M = {}"
    echo "M.colors = {"
} > "$OUTPUT_FILE"

# Function to map Kitty colors to Neovim highlight groups
convert_color() {
    local name="$1"
    local color="$2"
    case "$name" in
        background) echo "    background = \"$color\"," ;;
        foreground) echo "    foreground = \"$color\"," ;;
        selection_background) echo "    selection_background = \"$color\"," ;;
        selection_foreground) echo "    selection_foreground = \"$color\"," ;;
        cursor) echo "    cursor = \"$color\"," ;;
        cursor_text_color) echo "    cursor_text_color = \"$color\"," ;;
        color[0-9]*) echo "    color${name/color/} = \"$color\"," ;;
        *) echo "    -- $name = \"$color\"," ;; # Unrecognized attributes are commented out
    esac
}

# Parse the Kitty theme file
while read -r line; do
    # Ignore comments and empty lines
    [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue

    # Extract key-value pairs
    if [[ "$line" =~ ([a-zA-Z0-9_]+)[[:space:]]+([#a-fA-F0-9]+) ]]; then
        name="${BASH_REMATCH[1]}"
        color="${BASH_REMATCH[2]}"
        convert_color "$name" "$color" >> "$OUTPUT_FILE"
    fi
done < "$INPUT_FILE" || { echo "Error: Failed to read input file"; exit 1; }

# Close colors table
echo "}" >> "$OUTPUT_FILE"

# Add theme application function
cat <<'EOF' >> "$OUTPUT_FILE" || { echo "Error: Failed to write output file"; exit 1; }

-- Function to apply the theme
function M.apply()
    local colors = M.colors
    vim.cmd("highlight Normal guifg=" .. colors.foreground .. " guibg=" .. colors.background)
    vim.cmd("highlight Visual guifg=" .. colors.selection_foreground .. " guibg=" .. colors.selection_background)
    vim.cmd("highlight Cursor guifg=" .. colors.cursor_text_color .. " guibg=" .. colors.cursor)
    -- Add more highlight groups as needed
end

return M
EOF

echo "✨ Conversion complete. Neovim theme saved to '$OUTPUT_FILE'"

