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
    $(basename "$0") - Set up Tmux configuration

SYNOPSIS
    $(basename "$0") [OPTIONS]

DESCRIPTION
    Sets up Tmux with custom configuration and plugins.

OPTIONS
    -h, --help
        Display this help message and exit

COMPONENTS
    - Installs Tmux if not present
    - Sets up custom configuration
    - Installs Tmux Plugin Manager (TPM)
    - Installs plugins
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
setup_tmux() {
    print_step "Setting up Tmux"

    if ! command -v tmux &> /dev/null; then
        if confirm "Tmux not found. Would you like to install it?"; then
            if ! command -v brew &> /dev/null; then
                print_error "Homebrew is required but not installed"
                exit 1
            fi
            brew install tmux
            print_success "Tmux installed"
        else
            print_warning "Tmux installation skipped"
            return 1
        fi
    else
        print_warning "Tmux already installed"
    fi

    # Handle existing tmux configuration
    if ! handle_existing_file "$HOME/.tmux.conf" "tmux configuration"; then
        print_warning "Keeping existing tmux configuration"
        # Don't return, continue with TPM setup
    else
        # Link tmux.conf from new location
        ln -sf "$REPO_DIR/config/tmux/tmux.conf" ~/.tmux.conf
        print_success "Tmux configuration linked"
    fi

    # Set up TPM
    local tpm_dir="$HOME/.tmux/plugins/tpm"
    if [ -d "$tpm_dir" ]; then
        if confirm "Existing TPM installation found. Would you like to replace it?"; then
            rm -rf "$tpm_dir"
            mkdir -p "$HOME/.tmux/plugins"
            ln -sf "$REPO_DIR/config/tmux/plugins/tpm" "$tpm_dir"
            print_success "TPM linked"
        else
            print_warning "Using existing TPM installation"
        fi
    else
        # Create .tmux/plugins directory if it doesn't exist
        mkdir -p "$HOME/.tmux/plugins"
        # Link TPM from our config
        ln -sf "$REPO_DIR/config/tmux/plugins/tpm" "$tpm_dir"
        print_success "TPM linked"
    fi

    # Install plugins
    if [ -f "$tpm_dir/bin/install_plugins" ]; then
        if confirm "Would you like to install Tmux plugins now?"; then
            "$tpm_dir/bin/install_plugins"
            print_success "Tmux plugins installed"
        else
            print_warning "Plugin installation skipped. You can install them later with prefix + I"
        fi
    else
        print_error "TPM installation appears to be incomplete. Plugin installation skipped."
    fi

    print_success "Tmux setup complete!"
    return 0
}

# Run main function
setup_tmux
