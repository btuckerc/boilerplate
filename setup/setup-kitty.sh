#!/bin/bash
# Copyright (c) 2024 Tucker Craig
# See LICENSE file for full license details.

# Get the absolute directory of the current script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Source common utilities
COMMON_SCRIPT="$REPO_ROOT/utils/scripts/common.sh"
if [ -f "$COMMON_SCRIPT" ]; then
    source "$COMMON_SCRIPT"
else
    echo "Error: common.sh not found at: $COMMON_SCRIPT"
    exit 1
fi

# Function to show usage
show_usage() {
    cat << EOF
NAME
    $(basename "$0") - Set up Kitty terminal configuration

SYNOPSIS
    $(basename "$0") [OPTIONS]

DESCRIPTION
    Sets up Kitty terminal configuration with sensible defaults and themes.
    Backs up existing configuration and installs new settings.

OPTIONS
    -f, --force
        Overwrite existing configuration without backup

    -t, --theme THEME
        Specify theme to use [default: nord]
        Available: nord, catppuccin-mocha

    -h, --help
        Display this help message and exit

EXAMPLES
    $(basename "$0")
        Set up Kitty with default Nord theme

    $(basename "$0") -f
        Force setup without backup

    $(basename "$0") -t catppuccin-mocha
        Set up with Catppuccin Mocha theme

NOTES
    - Backs up existing configuration to ~/.config/kitty.bak
    - Installs Nord theme by default
    - Creates necessary directories if they don't exist
EOF
    exit 1
}

# Default values
FORCE=false
THEME="nord"
KITTY_CONFIG_DIR="$HOME/.config/kitty"
BACKUP_DIR="$HOME/.config/kitty.bak"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            FORCE=true
            shift
            ;;
        -t|--theme)
            if [ -z "$2" ]; then
                print_error "Theme name is required"
                show_usage
            fi
            THEME="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            ;;
    esac
done

# Check if Kitty is installed
if ! check_command kitty; then
    print_step "Installing Kitty..."
    install_brew_package kitty
fi

# Backup existing configuration if it exists
if [[ -d "$KITTY_CONFIG_DIR" && "$FORCE" != true ]]; then
    print_step "Backing up existing Kitty configuration..."
    if [[ -d "$BACKUP_DIR" ]]; then
        rm -rf "$BACKUP_DIR"
    fi
    mv "$KITTY_CONFIG_DIR" "$BACKUP_DIR"
    print_success "Configuration backed up to $BACKUP_DIR"
fi

# Create config directory
mkdir -p "$KITTY_CONFIG_DIR"

# Copy configuration files
print_step "Installing Kitty configuration..."
cp "$SCRIPT_DIR/config/kitty.conf" "$KITTY_CONFIG_DIR/"
cp "$SCRIPT_DIR/config/$THEME.conf" "$KITTY_CONFIG_DIR/theme.conf"

print_success "✨ Kitty configuration installed successfully!"
print_warning "Please restart Kitty terminal to apply changes."
