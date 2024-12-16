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
COLOR8=$(extract_color "color8")  # Bright black/gray
COLOR15=$(extract_color "color15") # Bright white

# Create a temporary file with the new configuration
cat > /tmp/tmux_theme.conf << EOF
# Tmux theme configuration
set -g @catppuccin_flavour 'custom'
set -g @catppuccin_status_modules_right 'directory session'
set -g @catppuccin_status_modules_left ''
set -g @catppuccin_status_left_separator ''
set -g @catppuccin_status_right_separator ''
set -g @catppuccin_status_right_separator_inverse 'no'
set -g @catppuccin_status_fill 'icon'
set -g @catppuccin_status_connect_separator 'no'

set -g @catppuccin_directory_text '#W'

set -g @catppuccin_status_background '$BACKGROUND'
set -g @catppuccin_status_bg_color '$BACKGROUND'
set -g @catppuccin_status_fg_color '$COLOR4'
set -g @catppuccin_status_text_color '$FOREGROUND'

set -g @catppuccin_window_default_background '$INACTIVE_TAB_BG'
set -g @catppuccin_window_default_color '$INACTIVE_TAB_FG'
set -g @catppuccin_window_current_background '$ACTIVE_TAB_BG'
set -g @catppuccin_window_current_color '$COLOR15'
set -g @catppuccin_window_left_separator_color '$COLOR8'
set -g @catppuccin_window_right_separator_color '$COLOR8'
set -g @catppuccin_window_middle_separator ' '
set -g @catppuccin_window_number_color '$COLOR4'

set -g @catppuccin_window_default_fill 'number'
set -g @catppuccin_window_current_fill 'number'
set -g @catppuccin_window_default_text ' #W'
set -g @catppuccin_window_current_text ' #W'

set -g @catppuccin_directory_color '$COLOR4'
set -g @catppuccin_date_time_color '$COLOR8'
set -g @catppuccin_session_color '$COLOR8'
EOF

# Create a temporary file for the full tmux config
TEMP_CONF=$(mktemp)

# Keep everything up to the theme configuration
sed '/^# Tmux theme configuration/,$d' "$TMUX_CONFIG" > "$TEMP_CONF"

# Add our new theme configuration
cat /tmp/tmux_theme.conf >> "$TEMP_CONF"

# Add the TPM initialization line
echo -e "\n# Initialize TPM (keep this at the bottom)\nrun '~/.tmux/plugins/tpm/tpm'" >> "$TEMP_CONF"

# Replace the original file
mv "$TEMP_CONF" "$TMUX_CONFIG"

# Clean up
rm -f /tmp/tmux_theme.conf

echo "Tmux colors have been synchronized with Kitty theme"
