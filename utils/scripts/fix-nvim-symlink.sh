#!/bin/bash
# Copyright (c) 2024 Tucker Craig
# See LICENSE file for full license details.

# Get the absolute directory of the current script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

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

# Paths
NVIM_CONFIG_DIR="$HOME/.config/nvim"
REPO_NVIM_DIR="$REPO_ROOT/config/nvim"

print_step "Fixing Neovim configuration symlink"

# Check if nvim directory exists in ~/.config
if [ -L "$NVIM_CONFIG_DIR" ]; then
    print_warning "Removing existing symlink at $NVIM_CONFIG_DIR"
    rm "$NVIM_CONFIG_DIR"
elif [ -d "$NVIM_CONFIG_DIR" ]; then
    backup_dir="${NVIM_CONFIG_DIR}.backup-$(date +%Y%m%d_%H%M%S)"
    print_warning "Backing up existing directory to $backup_dir"
    mv "$NVIM_CONFIG_DIR" "$backup_dir"
fi

# Create the symlink
print_step "Creating new symlink from $REPO_NVIM_DIR to $NVIM_CONFIG_DIR"
ln -s "$REPO_NVIM_DIR" "$NVIM_CONFIG_DIR"

print_success "Neovim configuration symlink has been fixed!"
