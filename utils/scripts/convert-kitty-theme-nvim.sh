#!/bin/bash
# Copyright (c) 2024 Tucker Craig
# See LICENSE file for full license details.

# Get the absolute directory of the current script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Define paths
KITTY_THEME="$REPO_ROOT/config/kitty/current-theme.conf"
NVIM_THEMES_DIR="$REPO_ROOT/config/nvim/lua/tucker/themes"
OUTPUT_THEME="$NVIM_THEMES_DIR/current-theme.lua"

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
    $(basename "$0") [OPTIONS]

DESCRIPTION
    Converts the current Kitty theme (current-theme.conf) to a Neovim theme with
    enhanced tab bar improvements. The script automatically calculates appropriate
    tab bar colors based on the background color.

OPTIONS
    -h, --help
        Display this help message and exit

PATHS
    Input:  $KITTY_THEME
    Output: $OUTPUT_THEME

THEME CONVERSION
    The script converts the following color attributes:
    - Basic colors (color0-color15)
    - Background and foreground colors
    - Automatically generates tab bar colors:
        * Tab bar background
        * Active/inactive tab colors
        * Tab borders

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
            print_error "Unknown argument: $1"
            print_warning "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Create necessary directories
mkdir -p "$NVIM_THEMES_DIR"

# Validate input file
if [ ! -f "$KITTY_THEME" ]; then
    print_error "Current theme not found: $KITTY_THEME"
    exit 1
fi

# Check if output file exists and create backup if needed
if [ -f "$OUTPUT_THEME" ]; then
    backup_file="${OUTPUT_THEME}.bak.$(date +%Y%m%d_%H%M%S)"
    print_warning "Output file exists, creating backup: $backup_file"
    mv "$OUTPUT_THEME" "$backup_file"
fi

print_step "Converting Kitty theme to Neovim theme"
print_step "Input: $KITTY_THEME"
print_step "Output: $OUTPUT_THEME"

# Create a temporary file to store the processed colors
tmp_file=$(mktemp)
trap 'rm -f "$tmp_file"' EXIT

# Extract colors from the Kitty theme
while IFS= read -r line; do
    # Skip comments and empty lines
    [[ $line =~ ^#.*$ ]] && continue
    [[ -z $line ]] && continue

    # Extract key and value, properly handling multiple spaces
    if [[ $line =~ ^[[:space:]]*([^[:space:]]+)[[:space:]]+([^[:space:]]+)[[:space:]]*$ ]]; then
        key="${BASH_REMATCH[1]}"
        value="${BASH_REMATCH[2]}"
        # Skip system and none values
        if [[ $value != "system" && $value != "none" ]]; then
            echo "${key}=${value}" >> "$tmp_file"
        fi
    fi
done < "$KITTY_THEME"

# Debug: show contents of tmp_file
echo "Contents of temp file:" >&2
cat "$tmp_file" >&2

# Function to get color value
get_color() {
    local color
    color=$(grep "^$1=" "$tmp_file" | cut -d'=' -f2)
    if [ -z "$color" ]; then
        case $1 in
            selection_background) echo "$(get_color background)" ;;
            selection_foreground) echo "$(get_color foreground)" ;;
            cursor) echo "$(get_color foreground)" ;;
            cursor_text_color) echo "$(get_color background)" ;;
            *) echo "#000000" ;;
        esac
    else
        echo "$color"
    fi
}

# Validate required colors
if [ -z "$(get_color background)" ] || [ -z "$(get_color foreground)" ]; then
    print_error "Input theme missing required colors (background/foreground)"
    exit 1
fi

# Infer tab bar colors based on the background
tab_bar_bg="$(get_color background)"
active_tab_bg=$(printf "#%02x%02x%02x" $((0x${tab_bar_bg:1:2} + 10)) $((0x${tab_bar_bg:3:2} + 10)) $((0x${tab_bar_bg:5:2} + 10)))
inactive_tab_bg=$(printf "#%02x%02x%02x" $((0x${tab_bar_bg:1:2} - 10)) $((0x${tab_bar_bg:3:2} - 10)) $((0x${tab_bar_bg:5:2} - 10)))
active_tab_fg="$(get_color foreground)"
inactive_tab_fg="#7e7e7e" # Default muted gray for inactive tabs
tab_border_color="#404040"

# Get theme name from the input file
theme_name=$(grep "^## name:" "$KITTY_THEME" | sed 's/^## name: //')
if [ -z "$theme_name" ]; then
    theme_name="Converted Kitty Theme"
fi

# Generate the Neovim theme
cat > "$OUTPUT_THEME" <<EOF
-- Converted Neovim Theme
-- Generated from Kitty theme: $KITTY_THEME
-- Generated on: $(date)

local M = {}

M.colors = {
    background = "$(get_color background)",
    foreground = "$(get_color foreground)",

    -- Tab bar improvements
    tab_bar_background = "$tab_bar_bg",
    active_tab_background = "$active_tab_bg",
    active_tab_foreground = "$active_tab_fg",
    inactive_tab_background = "$inactive_tab_bg",
    inactive_tab_foreground = "$inactive_tab_fg",
    tab_border_color = "$tab_border_color",

    -- Colors
    color0 = "$(get_color color0)",
    color1 = "$(get_color color1)",
    color2 = "$(get_color color2)",
    color3 = "$(get_color color3)",
    color4 = "$(get_color color4)",
    color5 = "$(get_color color5)",
    color6 = "$(get_color color6)",
    color7 = "$(get_color color7)",
    color8 = "$(get_color color8)",
    color9 = "$(get_color color9)",
    color10 = "$(get_color color10)",
    color11 = "$(get_color color11)",
    color12 = "$(get_color color12)",
    color13 = "$(get_color color13)",
    color14 = "$(get_color color14)",
    color15 = "$(get_color color15)",
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
print_success "Output saved to: $OUTPUT_THEME"
