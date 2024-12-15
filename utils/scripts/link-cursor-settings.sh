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

# Config paths
VSCODE_CONFIG_DIR="$HOME/Library/Application Support/Code/User"
CURSOR_CONFIG_DIR="$HOME/Library/Application Support/Cursor/User"
REPO_CONFIG_DIR="$REPO_ROOT/config/vscode"

# Function to backup and symlink a file
backup_and_symlink() {
    local source_file="$1"
    local target_file="$2"
    local backup_file="${source_file}.bak-$(date +%Y%m%d_%H%M%S)"

    # Check if source file exists
    if [ ! -f "$source_file" ] && [ ! -L "$source_file" ]; then
        print_warning "Source file $source_file does not exist. Creating new symlink..."
    elif [ ! -L "$source_file" ]; then
        print_step "Backing up $source_file to $backup_file"
        cp "$source_file" "$backup_file"
    fi

    # Remove existing file/symlink
    rm -f "$source_file"

    # Create symlink
    print_step "Creating symlink for $(basename "$source_file")"
    ln -s "$target_file" "$source_file"
}

# Ensure Cursor config directory exists
mkdir -p "$CURSOR_CONFIG_DIR"
mkdir -p "$CURSOR_CONFIG_DIR/snippets"
mkdir -p "$CURSOR_CONFIG_DIR/themes"

print_step "Linking Cursor settings to VSCode settings..."

# Link settings.json
backup_and_symlink "$CURSOR_CONFIG_DIR/settings.json" "$VSCODE_CONFIG_DIR/settings.json"

# Link snippets directory
for snippet_file in "$VSCODE_CONFIG_DIR/snippets"/*.json; do
    if [ -f "$snippet_file" ]; then
        filename=$(basename "$snippet_file")
        backup_and_symlink "$CURSOR_CONFIG_DIR/snippets/$filename" "$snippet_file"
    fi
done

# Link themes directory
for theme_file in "$VSCODE_CONFIG_DIR/themes"/*.json; do
    if [ -f "$theme_file" ]; then
        filename=$(basename "$theme_file")
        backup_and_symlink "$CURSOR_CONFIG_DIR/themes/$filename" "$theme_file"
    fi
done

print_success "✨ Cursor settings have been linked to VSCode settings!"
print_success "Your Cursor settings will now stay in sync with VSCode."
print_warning "Note: You may need to restart Cursor for changes to take effect."
