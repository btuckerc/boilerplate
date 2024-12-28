#!/bin/bash
# Copyright (c) 2024 Tucker Craig
# See LICENSE file for full license details.

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
print_step() {
    echo -e "\n${GREEN}==>${NC} $1"
}

print_error() {
    echo -e "${RED}Error:${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}Warning:${NC} $1"
}

confirm() {
    local message="$1"
    local default="${2:-n}"

    local prompt
    if [ "$default" = "y" ]; then
        prompt="[Y/n]"
    else
        prompt="[y/N]"
    fi

    read -p "$message $prompt " response
    response=${response:-$default}

    case "$response" in
        [yY][eE][sS]|[yY]) return 0 ;;
        *) return 1 ;;
    esac
}

# Check if running on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    print_error "This script is only for macOS!"
    exit 1
fi

print_step "Welcome to the boilerplate setup script!"

# Check if Xcode Command Line Tools are installed
if ! xcode-select -p &> /dev/null; then
    print_step "Installing Xcode Command Line Tools..."
    xcode-select --install

    # Wait for installation to complete
    print_warning "Please complete the Xcode Command Line Tools installation."
    print_warning "Press any key once installation is complete..."
    read -n 1
fi

# Check if git is installed
if ! command -v git &> /dev/null; then
    print_step "Git not found. Installing git..."
    # Git should be available after Xcode CLI tools installation
    if ! command -v git &> /dev/null; then
        print_error "Failed to install git. Please install it manually and try again."
        exit 1
    fi
fi

# Clone the repository
REPO_DIR="$HOME/Documents/GitHub/boilerplate"
if [ ! -d "$REPO_DIR" ]; then
    print_step "Cloning boilerplate repository..."
    mkdir -p "$(dirname "$REPO_DIR")"
    git clone https://github.com/btuckerc/boilerplate.git "$REPO_DIR"
else
    print_warning "Boilerplate repository already exists at $REPO_DIR"
    if confirm "Would you like to update it?"; then
        cd "$REPO_DIR"
        git pull
    fi
fi

# Change to repository directory
cd "$REPO_DIR"

# Ask if they want to run init-mac
if confirm "Would you like to set up your macOS development environment now?" "y"; then
    ./utils/init-mac
else
    print_warning "You can run the setup later with: $REPO_DIR/utils/init-mac"
fi

print_step "Bootstrap complete!"
echo -e "Your boilerplate repository is located at: ${GREEN}$REPO_DIR${NC}"
