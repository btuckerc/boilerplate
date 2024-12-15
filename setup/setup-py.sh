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

# Default Python version (latest stable)
DEFAULT_PYTHON_VERSION="3.12"

# Function to show usage
show_usage() {
    cat << EOF
NAME
    $(basename "$0") - Set up Python development environment

SYNOPSIS
    $(basename "$0") [OPTIONS]

DESCRIPTION
    Sets up a Python development environment using pyenv for version management.
    Installs and configures the specified Python version or uses system default.

OPTIONS
    -v, --version VERSION
        Python version to install [default: $DEFAULT_PYTHON_VERSION]
        Format: 3.X or 3.X.X (e.g., 3.11 or 3.11.5)

    -h, --help
        Display this help message and exit

EXAMPLES
    $(basename "$0")
        Install default Python version ($DEFAULT_PYTHON_VERSION)

    $(basename "$0") -v 3.11
        Install Python 3.11.x (latest patch)

    $(basename "$0") --version 3.11.6
        Install specific Python version 3.11.6

NOTES
    - Uses pyenv to manage Python versions
    - Will install Homebrew and pyenv if not present
    - Updates shell configuration for pyenv
EOF
    exit 1
}

# Function to find the latest supported patch version
get_latest_patch_version() {
    local minor_version="$1"
    pyenv install --list | awk '{print $1}' | grep -E "^${minor_version}(\.[0-9]+)?$" | tail -n 1
}

# Parse command line arguments
PYTHON_VERSION="$DEFAULT_PYTHON_VERSION"  # Use default version if none specified

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--version)
            if [ -z "$2" ]; then
                print_error "Version argument is required"
                show_usage
            fi
            PYTHON_VERSION="$2"
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

# Ensure Homebrew is installed
ensure_homebrew

# Update and upgrade Homebrew
print_step "Updating and upgrading Homebrew..."
brew update >/dev/null && brew upgrade >/dev/null

# Check if pyenv is installed
if check_command pyenv; then
    print_success "pyenv is installed. Proceeding with pyenv setup."

    # Upgrade pyenv, suppress warnings for already installed
    print_step "Upgrading pyenv..."
    brew upgrade pyenv 2>/dev/null

    # Determine the latest patch version if input is a minor version
    if [[ "$PYTHON_VERSION" =~ ^[0-9]+\.[0-9]+$ ]]; then
        print_step "Detected minor version: $PYTHON_VERSION. Finding the latest patch version..."
        LATEST_VERSION=$(get_latest_patch_version "$PYTHON_VERSION")
        if [ -z "$LATEST_VERSION" ]; then
            print_error "No available versions for Python $PYTHON_VERSION found in pyenv"
            exit 1
        fi
        print_success "Found latest patch version: $LATEST_VERSION"
        PYTHON_VERSION="$LATEST_VERSION"
    fi

    # Check if the desired Python version is installed via pyenv
    if ! pyenv versions | grep -q "$PYTHON_VERSION"; then
        print_step "Installing Python $PYTHON_VERSION..."
        pyenv install "$PYTHON_VERSION"
    else
        print_warning "Python $PYTHON_VERSION is already installed."
    fi

    # Set the global Python version
    pyenv global "$PYTHON_VERSION"
    print_success "Set Python $PYTHON_VERSION as the global version."

    # Ensure pyenv is properly initialized
    if ! grep -q 'eval "$(pyenv init --path)"' ~/.bash_profile; then
        echo 'eval "$(pyenv init --path)"' >> ~/.bash_profile
    fi
    if ! grep -q 'eval "$(pyenv init -)"' ~/.bash_profile; then
        echo 'eval "$(pyenv init -)"' >> ~/.bash_profile
    fi

    # Reload the shell configuration
    if [ -n "$BASH_VERSION" ]; then
        source ~/.bash_profile
    elif [ -n "$ZSH_VERSION" ]; then
        source ~/.zshrc
    fi
else
    print_warning "pyenv is not installed. Installing pyenv..."
    install_brew_package pyenv
    print_success "✨ pyenv installed successfully. Please restart the script to continue."
    exit 1
fi

# Verify the installed Python version
print_step "Verifying Python installation..."
INSTALLED_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
if [[ "$INSTALLED_VERSION" == "$PYTHON_VERSION"* ]]; then
    print_success "✨ Python $PYTHON_VERSION is successfully installed and active!"
else
    print_error "Failed to activate Python $PYTHON_VERSION. Please check your setup."
    exit 1
fi
