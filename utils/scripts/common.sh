#!/bin/bash
# Copyright (c) 2024 Tucker Craig
# See LICENSE file for full license details.

# Common utility functions used across scripts

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
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

# Function for single-key confirmation prompts
confirm() {
    local message="$1"
    local default="${2:-n}"  # Default to 'n' if not specified

    local prompt
    if [ "$default" = "y" ]; then
        prompt="[Y/n]"
    else
        prompt="[y/N]"
    fi

    echo -n "$message $prompt "

    # Save current tty settings
    local old_tty_settings
    old_tty_settings=$(stty -g)

    # Set tty to raw mode (-echo: don't echo typed characters)
    stty raw -echo

    # Read single character
    local response
    response=$(dd bs=1 count=1 2>/dev/null)

    # Restore tty settings
    stty "$old_tty_settings"

    # Print newline since we didn't echo the user's input
    echo

    # Convert empty response to default
    response=${response:-$default}

    case "$response" in
        [yY]) return 0 ;;
        *) return 1 ;;
    esac
}

# Function to handle existing dotfiles
handle_existing_file() {
    local target_file="$1"
    local file_type="$2"
    local backup=false

    if [ -L "$target_file" ]; then
        if confirm "Existing $file_type symlink found at $target_file. Would you like to replace it?"; then
            rm "$target_file"
            backup=true
        else
            print_warning "$file_type symlink unchanged"
            return 1
        fi
    elif [ -f "$target_file" ]; then
        if confirm "Existing $file_type found at $target_file. Would you like to backup and replace it?"; then
            mv "$target_file" "$target_file.bak.$(date +%Y%m%d_%H%M%S)"
            print_warning "Existing $file_type backed up"
            backup=true
        else
            print_warning "$file_type unchanged"
            return 1
        fi
    fi
    return 0
}
