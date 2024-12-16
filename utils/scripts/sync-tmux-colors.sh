#!/bin/bash

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
KITTY_THEME="$REPO_ROOT/config/kitty/current-theme.conf"
TMUX_CONFIG="$REPO_ROOT/config/tmux/tmux.conf"

# Function to extract color from kitty theme
extract_color() {
    local color_name=$1
    grep "^$color_name " "$KITTY_THEME" | awk '{print $2}'
}

# Extract colors from kitty theme
BACKGROUND=$(extract_color "background")
FOREGROUND=$(extract_color "foreground")
ACTIVE_TAB_BG=$(extract_color "active_tab_background")
INACTIVE_TAB_BG=$(extract_color "inactive_tab_background")
ACTIVE_TAB_FG=$(extract_color "active_tab_foreground")
INACTIVE_TAB_FG=$(extract_color "inactive_tab_foreground")
COLOR4=$(extract_color "color4")  # Blue
COLOR6=$(extract_color "color6")  # Cyan
COLOR7=$(extract_color "color7")  # White
COLOR8=$(extract_color "color8")  # Bright black/gray

# Update tmux configuration with new colors
sed -i.bak "
    /^set -g @catppuccin_/d
    /# Tmux theme configuration/a\\
set -g @catppuccin_flavour 'custom'\\
set -g @catppuccin_status_modules_right 'directory session'\\
set -g @catppuccin_status_modules_left ''\\
set -g @catppuccin_status_left_separator ''\\
set -g @catppuccin_status_right_separator ''\\
set -g @catppuccin_status_right_separator_inverse 'no'\\
set -g @catppuccin_status_fill 'icon'\\
set -g @catppuccin_status_connect_separator 'no'\\
\\
set -g @catppuccin_directory_text '#W'\\
\\
set -g @catppuccin_status_background '$BACKGROUND'\\
set -g @catppuccin_status_bg_color '$BACKGROUND'\\
set -g @catppuccin_status_fg_color '$FOREGROUND'\\
set -g @catppuccin_status_text_color '$FOREGROUND'\\
\\
set -g @catppuccin_window_default_background '$INACTIVE_TAB_BG'\\
set -g @catppuccin_window_default_color '$INACTIVE_TAB_FG'\\
set -g @catppuccin_window_current_background '$ACTIVE_TAB_BG'\\
set -g @catppuccin_window_current_color '$ACTIVE_TAB_FG'\\
set -g @catppuccin_window_left_separator_color '$COLOR8'\\
set -g @catppuccin_window_right_separator_color '$COLOR8'\\
set -g @catppuccin_window_middle_separator ' '\\
set -g @catppuccin_window_number_color '$COLOR4'\\
\\
set -g @catppuccin_window_default_fill 'number'\\
set -g @catppuccin_window_current_fill 'number'\\
set -g @catppuccin_window_default_text ' #W'\\
set -g @catppuccin_window_current_text ' #W'\\
\\
set -g @catppuccin_directory_color '$COLOR4'\\
set -g @catppuccin_date_time_color '$COLOR8'\\
set -g @catppuccin_session_color '$COLOR8'
" "$TMUX_CONFIG"

# Remove backup file
rm "${TMUX_CONFIG}.bak"

echo "Tmux colors have been synchronized with Kitty theme"
