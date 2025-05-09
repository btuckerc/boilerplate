#!/bin/bash

# MIT License
#
# Copyright (c) 2024 Tucker Craig
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Get the absolute directory of the current script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common utilities
source "$SCRIPT_DIR/../utils/scripts/common.sh"

# Function to show usage
show_usage() {
    cat << EOF
NAME
    $(basename "$0") - Set up Go development environment

SYNOPSIS
    $(basename "$0") [OPTIONS]

DESCRIPTION
    Sets up a Go development environment by installing and configuring Go and its
    dependencies using Homebrew. Ensures all necessary tools are available.

OPTIONS
    -h, --help
        Display this help message and exit

EXAMPLES
    $(basename "$0")
        Set up Go development environment with default settings

NOTES
    - Will install Homebrew if not present
    - Installs latest version of Go via Homebrew
    - Installs Git if not present
    - Updates shell configuration as needed
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
            echo "Error: Unknown option: $1"
            show_usage
            ;;
    esac
done

# Ensure Homebrew is installed
ensure_homebrew

# Ensure Go is installed
if ! check_command go; then
    echo "Installing Go..."
    install_brew_package go
else
    echo "Go is already installed."
fi

# Ensure Git is installed
ensure_git

echo "✨ Go development environment setup complete!"