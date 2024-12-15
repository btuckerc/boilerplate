#!/bin/bash
# Copyright (c) 2024 Tucker Craig
# See LICENSE file for full license details.

# Common utility functions used across scripts

# Function to check if a command exists
check_command() {
    if ! command -v "$1" &>/dev/null; then
        echo "$1 is not installed."
        return 1
    else
        return 0
    fi
}

# Function to install a tool via Homebrew
install_brew_package() {
    local package="$1"
    echo "Installing $package..."
    brew install "$package" || { echo "Failed to install $package. Exiting."; exit 1; }
}

# Function to check if directory is empty (ignoring hidden files)
is_directory_empty() {
    local dir="$1"
    if [ -z "$(ls -A "$dir" | grep -v '^\..*')" ]; then
        return 0
    else
        return 1
    fi
}

# Function to replace PROJECT_NAME in a file
replace_project_name() {
    local file="$1"
    local project_name="$2"
    if [ -f "$file" ]; then
        sed -i '' "s/PROJECT_NAME/$project_name/g" "$file"
    fi
}

# Function to copy and process templates
copy_templates() {
    local src_dir="$1"
    local dest_dir="$2"
    local project_name="$3"

    # Check if template directory exists
    if [ ! -d "$src_dir" ]; then
        echo "Error: Template directory not found at $src_dir"
        exit 1
    fi

    # Copy all templates
    cp -r "$src_dir"/* "$dest_dir"/ 2>/dev/null || true

    # Replace PROJECT_NAME in all text files
    find "$dest_dir" -type f -not -name "*.pyc" -not -path "*/\.*" | while read -r file; do
        if file "$file" | grep -q text; then
            replace_project_name "$file" "$project_name"
        fi
    done
}

# Function to ensure Homebrew is installed
ensure_homebrew() {
    if ! check_command brew; then
        echo "Homebrew is not installed. Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || { echo "Homebrew installation failed. Exiting."; exit 1; }
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
}

# Function to ensure Git is installed
ensure_git() {
    if ! check_command git; then
        echo "Git is not installed. Installing Git..."
        install_brew_package git
    fi
} 