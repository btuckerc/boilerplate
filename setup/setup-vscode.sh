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
    print_error "common.sh not found at: $COMMON_SCRIPT"
    exit 1
fi

# Check for required dependencies
if ! command -v jq &> /dev/null; then
    print_error "jq is required but not installed. Please install it with: brew install jq"
    exit 1
fi

# VSCode config paths
VSCODE_CONFIG_DIR="$HOME/Library/Application Support/Code/User"
VSCODE_EXTENSIONS_DIR="$HOME/.vscode/extensions"
REPO_CONFIG_DIR="$REPO_ROOT/config/vscode"
REPO_EXTENSIONS_DIR="$REPO_CONFIG_DIR/extensions"
EXTENSIONS_JSON="$VSCODE_EXTENSIONS_DIR/extensions.json"

# Create necessary directories
mkdir -p "$REPO_CONFIG_DIR/snippets"
mkdir -p "$VSCODE_CONFIG_DIR/snippets"
mkdir -p "$VSCODE_EXTENSIONS_DIR"

# Function to resolve symlink and get real path
resolve_symlink() {
    local file="$1"
    if [ -L "$file" ]; then
        local target=$(readlink "$file")
        if [[ "$target" = /* ]]; then
            echo "$target"
        else
            echo "$(dirname "$file")/$target"
        fi
    else
        echo "$file"
    fi
}

# Function to backup and symlink a file
backup_and_symlink() {
    local source_file="$1"
    local target_file="$2"
    local backup_file="${source_file}.bak-$(date +%Y%m%d_%H%M%S)"

    # Resolve the real paths
    target_file=$(resolve_symlink "$target_file")

    # Create parent directory if it doesn't exist
    local parent_dir=$(dirname "$source_file")
    [ ! -d "$parent_dir" ] && mkdir -p "$parent_dir"

    # Check if source file exists and is not already the correct symlink
    if [ ! -e "$source_file" ]; then
        ln -sf "$target_file" "$source_file"
        print_success "Created symlink: $(basename "$source_file")"
    elif [ -L "$source_file" ]; then
        current_target=$(readlink "$source_file")
        if [ "$current_target" = "$target_file" ]; then
            print_success "Already linked: $(basename "$source_file")"
            return 0
        fi
        rm -f "$source_file"
        ln -sf "$target_file" "$source_file"
        print_success "Updated symlink: $(basename "$source_file")"
    else
        cp "$source_file" "$backup_file"
        rm -f "$source_file"
        ln -sf "$target_file" "$source_file"
        print_success "Backed up and linked: $(basename "$source_file")"
    fi
}

# Function to register extension
register_extension() {
    local extension_name="$1"
    local extension_path="$VSCODE_EXTENSIONS_DIR/$extension_name"
    local package_json="$extension_path/package.json"

    # Create extensions.json if it doesn't exist
    if [ ! -f "$EXTENSIONS_JSON" ]; then
        echo "[]" > "$EXTENSIONS_JSON"
    else
        # Create backup of existing extensions.json
        local backup_file="${EXTENSIONS_JSON}.bak-$(date +%Y%m%d_%H%M%S)"
        echo "Creating backup of extensions.json at $backup_file"
        cp "$EXTENSIONS_JSON" "$backup_file"
    fi

    # Read metadata from package.json if it exists
    if [ -f "$package_json" ]; then
        local version=$(jq -r '.version' "$package_json")
        local publisher=$(jq -r '.publisher' "$package_json")
        local display_name=$(jq -r '.displayName' "$package_json")
        local description=$(jq -r '.description' "$package_json")
    else
        echo "Warning: package.json not found for extension $extension_name"
        return 1
    fi

    # Check if extension is already registered
    if ! jq -e ".[] | select(.identifier.id == \"${publisher}.${extension_name}\")" "$EXTENSIONS_JSON" > /dev/null; then
        # Create temporary file
        local tmp_file=$(mktemp)

        # Add new extension while preserving existing ones
        jq ". + [{
            \"identifier\": {
                \"id\": \"${publisher}.${extension_name}\"
            },
            \"version\": \"${version}\",
            \"location\": {
                \"scheme\": \"file\",
                \"path\": \"$extension_path\"
            },
            \"relativeLocation\": \"$extension_name\",
            \"metadata\": {
                \"displayName\": \"${display_name}\",
                \"description\": \"${description}\"
            }
        }]" "$EXTENSIONS_JSON" > "$tmp_file"

        if [ $? -eq 0 ]; then
            mv "$tmp_file" "$EXTENSIONS_JSON"
            echo "Registered extension: $extension_name (${publisher}.${extension_name})"
        else
            echo "Error: Failed to update extensions.json"
            rm -f "$tmp_file"
            return 1
        fi
    else
        echo "Extension already registered: ${publisher}.${extension_name}"
    fi
}

# Function to setup VSCode extension
setup_extension() {
    local extension_dir="$1"
    local extension_name=$(basename "$extension_dir")
    local target_dir="$VSCODE_EXTENSIONS_DIR/$extension_name"

    print_step "Setting up extension: $extension_name"

    # Check if target directory is already a symlink
    if [ -L "$target_dir" ]; then
        current_target=$(readlink "$target_dir")
        if [ "$current_target" = "$extension_dir" ]; then
            print_success "Extension already linked"
            register_extension "$extension_name"
            return 0
        fi
        rm "$target_dir"
    elif [ -d "$target_dir" ]; then
        mv "$target_dir" "${target_dir}.bak-$(date +%Y%m%d_%H%M%S)"
        print_success "Backed up existing extension"
    fi

    # Create the symlink for the entire extension directory
    ln -sf "$extension_dir" "$target_dir"

    if [ -L "$target_dir" ] && [ -d "$target_dir" ]; then
        print_success "Extension linked successfully"
        register_extension "$extension_name"
        return 0
    else
        print_error "Failed to link extension"
        return 1
    fi
}

# Handle settings.json
print_step "Setting up VSCode configuration"
backup_and_symlink "$VSCODE_CONFIG_DIR/settings.json" "$REPO_CONFIG_DIR/settings.json"

# Handle extensions directory
print_step "Setting up extensions"
for extension_dir in "$REPO_EXTENSIONS_DIR"/*; do
    [ -d "$extension_dir" ] && setup_extension "$extension_dir"
done

# Handle snippets
print_step "Setting up snippets"
for snippet_file in "$REPO_CONFIG_DIR/snippets"/*.json; do
    [ -f "$snippet_file" ] && backup_and_symlink "$VSCODE_CONFIG_DIR/snippets/$(basename "$snippet_file")" "$snippet_file"
done

print_success "✨ VSCode configuration complete!"
