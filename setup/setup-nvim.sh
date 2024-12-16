#!/bin/bash
# Copyright (c) 2024 Tucker Craig
# See LICENSE file for full license details.

# Get the absolute directory of the current script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common utilities
COMMON_SCRIPT="$SCRIPT_DIR/../utils/scripts/common.sh"
if [ -f "$COMMON_SCRIPT" ]; then
    source "$COMMON_SCRIPT"
else
    echo "Error: common.sh not found at: $COMMON_SCRIPT"
    exit 1
fi

# Repository root directory
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Function to show usage
show_usage() {
    cat << EOF
NAME
    $(basename "$0") - Set up Neovim configuration

SYNOPSIS
    $(basename "$0") [OPTIONS]

DESCRIPTION
    Sets up Neovim with custom configuration and plugins.

OPTIONS
    -h, --help
        Display this help message and exit

COMPONENTS
    - Installs Neovim if not present
    - Sets up custom configuration
    - Links configuration files
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
            print_error "Unknown option: $1"
            show_usage
            ;;
    esac
done

# Main setup function
setup_neovim() {
    print_step "Setting up Neovim"

    if ! command -v nvim &> /dev/null; then
        if confirm "Neovim not found. Would you like to install it?"; then
            if ! command -v brew &> /dev/null; then
                print_error "Homebrew is required but not installed"
                exit 1
            fi
            brew install neovim
            print_success "Neovim installed"
        else
            print_warning "Neovim installation skipped"
            return 1
        fi
    else
        print_warning "Neovim already installed"
    fi

    # Handle existing neovim configuration
    if ! handle_existing_file "$HOME/.config/nvim" "Neovim configuration directory"; then
        return 1
    fi

    mkdir -p ~/.config
    ln -sf "$REPO_DIR/config/nvim" ~/.config/nvim
    print_success "Neovim configuration linked"

    print_success "Neovim setup complete!"
    return 0
}

# Run main function
setup_neovim
