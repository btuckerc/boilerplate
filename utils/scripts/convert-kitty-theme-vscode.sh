#!/bin/bash
# Copyright (c) 2024 Tucker Craig
# See LICENSE file for full license details.

# Get the absolute directory of the current script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source common utilities
COMMON_SCRIPT="$REPO_ROOT/utils/scripts/common.sh"
if [ -f "$COMMON_SCRIPT" ]; then
    source "$COMMON_SCRIPT"
else
    echo "Error: common.sh not found at: $COMMON_SCRIPT"
    exit 1
fi

# Define paths
KITTY_THEME="$REPO_ROOT/config/kitty/current-theme.conf"
REPO_EXTENSION_DIR="$REPO_ROOT/config/vscode/extensions/current-theme"
REPO_THEMES_DIR="$REPO_EXTENSION_DIR/themes"
OUTPUT_THEME="$REPO_THEMES_DIR/current-theme.json"

# Get current user for publisher ID
CURRENT_USER=$(whoami)

# Function to show usage
show_usage() {
    cat << EOF
NAME
    $(basename "$0") - Convert Kitty terminal themes to VSCode themes

SYNOPSIS
    $(basename "$0") [OPTIONS]

DESCRIPTION
    Converts the current Kitty theme (current-theme.conf) to a VSCode theme.
    The script automatically generates appropriate VSCode theme colors based on
    the Kitty theme colors.

OPTIONS
    -h, --help
        Display this help message and exit

PATHS
    Input:  $KITTY_THEME
    Output: $OUTPUT_THEME

NOTES
    - The theme will be installed as a VSCode extension
    - The theme name will be derived from the Kitty theme
    - Existing theme files will be backed up before overwriting
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

# Function to safely write to a file
safe_write() {
    local target_file="$1"
    local target_dir=$(dirname "$target_file")

    # Ensure directory exists
    mkdir -p "$target_dir"

    # Remove any existing symlink or file
    if [ -L "$target_file" ]; then
        rm "$target_file"
    elif [ -f "$target_file" ]; then
        backup_file="${target_file}.bak-$(date +%Y%m%d_%H%M%S)"
        print_warning "Backing up: $(basename "$target_file")"
        cp "$target_file" "$backup_file"
        rm "$target_file"
    fi

    # Create the new file
    cat > "$target_file"

    if [ $? -eq 0 ] && [ -s "$target_file" ]; then
        print_success "Created: $(basename "$target_file")"
        return 0
    else
        print_error "Failed to create: $(basename "$target_file")"
        return 1
    fi
}

print_step "Converting Kitty theme to VSCode theme"

# Create necessary directories
mkdir -p "$REPO_THEMES_DIR"
mkdir -p "$REPO_EXTENSION_DIR"

# Validate input file
[ ! -f "$KITTY_THEME" ] && { print_error "Theme not found: $KITTY_THEME"; exit 1; }

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

# Get theme name from the input file
theme_name="Current Theme"

# Generate the VSCode theme
print_step "Generating theme files"
safe_write "$OUTPUT_THEME" <<EOF
{
    "\$schema": "vscode://schemas/color-theme",
    "name": "$theme_name",
    "type": "dark",
    "semanticHighlighting": true,
    "colors": {
        "editor.background": "$(get_color background)",
        "editor.foreground": "$(get_color foreground)",
        "editor.selectionBackground": "$(get_color selection_background)",
        "editor.selectionForeground": "$(get_color selection_foreground)",
        "editorCursor.foreground": "$(get_color cursor)",
        "editorCursor.background": "$(get_color cursor_text_color)",
        "terminal.ansiBlack": "$(get_color color0)",
        "terminal.ansiRed": "$(get_color color1)",
        "terminal.ansiGreen": "$(get_color color2)",
        "terminal.ansiYellow": "$(get_color color3)",
        "terminal.ansiBlue": "$(get_color color4)",
        "terminal.ansiMagenta": "$(get_color color5)",
        "terminal.ansiCyan": "$(get_color color6)",
        "terminal.ansiWhite": "$(get_color color7)",
        "terminal.ansiBrightBlack": "$(get_color color8)",
        "terminal.ansiBrightRed": "$(get_color color9)",
        "terminal.ansiBrightGreen": "$(get_color color10)",
        "terminal.ansiBrightYellow": "$(get_color color11)",
        "terminal.ansiBrightBlue": "$(get_color color12)",
        "terminal.ansiBrightMagenta": "$(get_color color13)",
        "terminal.ansiBrightCyan": "$(get_color color14)",
        "terminal.ansiBrightWhite": "$(get_color color15)",
        "activityBar.background": "$(get_color background)",
        "activityBar.foreground": "$(get_color foreground)",
        "sideBar.background": "$(get_color background)",
        "sideBar.foreground": "$(get_color foreground)",
        "statusBar.background": "$(get_color color4)",
        "statusBar.foreground": "$(get_color color15)",
        "titleBar.activeBackground": "$(get_color background)",
        "titleBar.activeForeground": "$(get_color foreground)",
        "titleBar.inactiveBackground": "$(get_color background)",
        "titleBar.inactiveForeground": "$(get_color color8)",
        "editorGroupHeader.tabsBackground": "$(get_color background)",
        "tab.activeBackground": "$(get_color selection_background)",
        "tab.inactiveBackground": "$(get_color background)",
        "tab.activeForeground": "$(get_color foreground)",
        "tab.inactiveForeground": "$(get_color color8)",
        "list.activeSelectionBackground": "$(get_color selection_background)",
        "list.activeSelectionForeground": "$(get_color foreground)",
        "list.inactiveSelectionBackground": "$(get_color background)",
        "list.inactiveSelectionForeground": "$(get_color foreground)",
        "list.hoverBackground": "$(get_color selection_background)",
        "list.hoverForeground": "$(get_color foreground)"
    },
    "tokenColors": [
        {
            "scope": ["comment"],
            "settings": {
                "foreground": "$(get_color color8)",
                "fontStyle": "italic"
            }
        },
        {
            "scope": ["string", "string.quoted", "string.quoted.single", "string.quoted.double"],
            "settings": {
                "foreground": "$(get_color color2)"
            }
        },
        {
            "scope": ["keyword", "storage.type", "storage.modifier"],
            "settings": {
                "foreground": "$(get_color color5)"
            }
        },
        {
            "scope": ["variable", "variable.other", "variable.parameter", "variable.language"],
            "settings": {
                "foreground": "$(get_color color4)"
            }
        },
        {
            "scope": ["constant", "constant.numeric", "constant.language", "constant.character"],
            "settings": {
                "foreground": "$(get_color color3)"
            }
        },
        {
            "scope": ["entity.name.function", "support.function"],
            "settings": {
                "foreground": "$(get_color color6)"
            }
        }
    ]
}
EOF

# Create package.json
safe_write "$REPO_EXTENSION_DIR/package.json" <<EOF
{
    "name": "current-theme",
    "displayName": "Current Theme",
    "description": "Current theme converted from Kitty",
    "version": "1.0.0",
    "publisher": "$CURRENT_USER",
    "engines": {
        "vscode": "^1.84.0"
    },
    "categories": [
        "Themes"
    ],
    "contributes": {
        "themes": [
            {
                "label": "Current Theme",
                "uiTheme": "vs-dark",
                "path": "./themes/current-theme.json"
            }
        ]
    }
}
EOF

# Verify files were created
if [ -f "$OUTPUT_THEME" ] && [ -f "$REPO_EXTENSION_DIR/package.json" ]; then
    print_success "✨ Theme conversion complete"
    print_warning "Run setup-vscode.sh to install the theme"
else
    print_error "Theme conversion failed"
    exit 1
fi
