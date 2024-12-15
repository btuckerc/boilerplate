#!/bin/bash
# Copyright (c) 2024 Tucker Craig
# See LICENSE file for full license details.

# Get the absolute directory of the current script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_step() {
    echo -e "${BLUE}==> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}! $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to show usage
show_usage() {
    cat << EOF
NAME
    $(basename "$0") - Convert Kitty terminal themes to Neovim themes

SYNOPSIS
    $(basename "$0") [OPTIONS] input-kitty-theme.conf output-nvim-theme.lua

DESCRIPTION
    Converts a Kitty terminal theme configuration file to a Neovim theme with
    enhanced tab bar improvements. The script automatically calculates appropriate
    tab bar colors based on the background color.

ARGUMENTS
    input-kitty-theme.conf
        Path to the input Kitty theme configuration file

    output-nvim-theme.lua
        Path where the converted Neovim theme will be saved

OPTIONS
    -h, --help
        Display this help message and exit

THEME CONVERSION
    The script converts the following color attributes:
    - Basic colors (color0-color15)
    - Background and foreground colors
    - Automatically generates tab bar colors:
        * Tab bar background
        * Active/inactive tab colors
        * Tab borders

EXAMPLES
    $(basename "$0") mytheme.conf mytheme.lua
        Convert mytheme.conf to a Neovim theme

    $(basename "$0") ~/.config/kitty/themes/dark.conf ~/.config/nvim/lua/themes/dark.lua
        Convert a Kitty theme to a Neovim theme with full paths

NOTES
    - Input file must be a valid Kitty theme configuration
    - Output will be a complete Neovim theme module
    - Includes automatic tab bar color calculations
    - Creates backup if output file exists
EOF
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            ;;
        *)
            break
            ;;
    esac
done

if [ "$#" -ne 2 ]; then
    print_error "Invalid number of arguments"
    print_warning "Usage: $(basename "$0") input-kitty-theme.conf output-nvim-theme.lua"
    print_warning "Use -h or --help for more information"
    exit 1
fi

input_file=$1
output_file=$2

# Validate input file
if [ ! -f "$input_file" ]; then
    print_error "Input file not found: $input_file"
    exit 1
fi

# Check if output file exists and create backup if needed
if [ -f "$output_file" ]; then
    backup_file="${output_file}.bak.$(date +%Y%m%d_%H%M%S)"
    print_warning "Output file exists, creating backup: $backup_file"
    mv "$output_file" "$backup_file"
fi

print_step "Converting Kitty theme to Neovim theme"
print_step "Input: $input_file"
print_step "Output: $output_file"

# Extract basic colors from the Kitty theme
declare -A colors

while IFS='=' read -r key value; do
    key=$(echo "$key" | xargs)
    value=$(echo "$value" | xargs)
    case "$key" in
        color[0-9]*) colors[$key]=$value ;;
        background) colors[background]=$value ;;
        foreground) colors[foreground]=$value ;;
    esac
done < "$input_file"

# Validate required colors
if [ -z "${colors[background]}" ] || [ -z "${colors[foreground]}" ]; then
    print_error "Input theme missing required colors (background/foreground)"
    exit 1
fi

# Infer tab bar colors based on the background
tab_bar_bg="${colors[background]}"
active_tab_bg=$(printf "#%02x%02x%02x" $((0x${tab_bar_bg:1:2} + 10)) $((0x${tab_bar_bg:3:2} + 10)) $((0x${tab_bar_bg:5:2} + 10)))
inactive_tab_bg=$(printf "#%02x%02x%02x" $((0x${tab_bar_bg:1:2} - 10)) $((0x${tab_bar_bg:3:2} - 10)) $((0x${tab_bar_bg:5:2} - 10)))
active_tab_fg="${colors[foreground]}"
inactive_tab_fg="#7e7e7e" # Default muted gray for inactive tabs
tab_border_color="#404040"

# Generate the Neovim theme
cat > "$output_file" <<EOF
-- Converted Neovim Theme
-- Generated from Kitty theme: $input_file
-- Generated on: $(date)

local M = {}

M.colors = {
    background = "${colors[background]}",
    foreground = "${colors[foreground]}",

    -- Tab bar improvements
    tab_bar_background = "$tab_bar_bg",
    active_tab_background = "$active_tab_bg",
    active_tab_foreground = "$active_tab_fg",
    inactive_tab_background = "$inactive_tab_bg",
    inactive_tab_foreground = "$inactive_tab_fg",
    tab_border_color = "$tab_border_color",

    -- Colors
    color0 = "${colors[color0]}",
    color1 = "${colors[color1]}",
    color2 = "${colors[color2]}",
    color3 = "${colors[color3]}",
    color4 = "${colors[color4]}",
    color5 = "${colors[color5]}",
    color6 = "${colors[color6]}",
    color7 = "${colors[color7]}",
    color8 = "${colors[color8]}",
    color9 = "${colors[color9]}",
    color10 = "${colors[color10]}",
    color11 = "${colors[color11]}",
    color12 = "${colors[color12]}",
    color13 = "${colors[color13]}",
    color14 = "${colors[color14]}",
    color15 = "${colors[color15]}",
}

-- Function to apply the theme
function M.apply()
    local colors = M.colors

    -- Basic highlights
    vim.cmd("highlight Normal guifg=" .. colors.foreground .. " guibg=" .. colors.background)

    -- Tabline highlights
    vim.cmd("highlight TabLine guibg=" .. colors.inactive_tab_background .. " guifg=" .. colors.inactive_tab_foreground)
    vim.cmd("highlight TabLineSel guibg=" .. colors.active_tab_background .. " guifg=" .. colors.active_tab_foreground)
    vim.cmd("highlight TabLineFill guibg=" .. colors.tab_bar_background)

    -- Tab borders
    vim.cmd("highlight TabBorder guibg=" .. colors.tab_bar_background .. " guifg=" .. colors.tab_border_color)
end

return M
EOF

print_success "Theme conversion complete"
print_success "Output saved to: $output_file"
