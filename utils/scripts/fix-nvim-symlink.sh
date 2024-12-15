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

# Paths
NVIM_CONFIG_DIR="$HOME/.config/nvim"
REPO_NVIM_DIR="$REPO_ROOT/config/nvim"

print_step "Fixing Neovim configuration symlink"

# Check if nvim directory exists in ~/.config
if [ -L "$NVIM_CONFIG_DIR" ]; then
    print_warning "Removing existing symlink at $NVIM_CONFIG_DIR"
    rm "$NVIM_CONFIG_DIR"
elif [ -d "$NVIM_CONFIG_DIR" ]; then
    backup_dir="${NVIM_CONFIG_DIR}.bak-$(date +%Y%m%d_%H%M%S)"
    print_warning "Backing up existing directory to $backup_dir"
    mv "$NVIM_CONFIG_DIR" "$backup_dir"
fi

# Create the symlink
print_step "Creating new symlink from $REPO_NVIM_DIR to $NVIM_CONFIG_DIR"
ln -s "$REPO_NVIM_DIR" "$NVIM_CONFIG_DIR"

print_success "Neovim configuration symlink has been fixed!"
