#!/bin/bash
# Copyright (c) 2024 Tucker Craig
# See LICENSE file for full license details.

# Get the absolute directory of the current script

# Function to show usage
show_usage() {
    cat << EOF
NAME
    $(basename "$0") - Generate a directory tree structure

SYNOPSIS
    $(basename "$0") [OPTIONS] [DIRECTORY]

DESCRIPTION
    Creates a visual tree representation of a directory structure, with support
    for depth limits, exclusion patterns, and documentation placeholders.

ARGUMENTS
    DIRECTORY
        Directory to generate tree for [default: current directory]

OPTIONS
    -d, --depth DEPTH
        Maximum depth to traverse [default: unlimited]

    -e, --exclude PATTERN
        Exclude pattern (e.g., "node_modules|.git")

    -p, --placeholder
        Add aligned comment placeholders (#) for documentation

    -h, --help
        Display this help message and exit

EXAMPLES
    $(basename "$0")
        Basic tree of current directory

    $(basename "$0") ~/projects/app
        Tree of specific directory

    $(basename "$0") -d 2
        Limit depth to 2 levels

    $(basename "$0") -e "node_modules"
        Exclude node_modules directory

    $(basename "$0") -p
        Add aligned comment placeholders

NOTES
    - Hidden files and directories are excluded by default
    - Use -p to add placeholders for your own documentation
    - Comments will be aligned with at least 2 spaces after the longest line
    - Maximum line length (including comments) is capped at 80 characters
EOF
    exit 1
}

# Default values
MAX_DEPTH=""
EXCLUDE_PATTERN="^\.|^node_modules$"
ADD_PLACEHOLDERS=false
TARGET_DIR="."
MIN_PADDING=2        # Minimum spaces before comment
MAX_LINE_LENGTH=80   # Traditional max line length
LONGEST_LINE=0       # Will be calculated if placeholders are enabled

# Calculate the indentation level
get_indent_level() {
    local prefix="$1"
    echo $(( (${#prefix} + 4) / 4 ))  # 4 spaces per level
}

# Calculate the total line length including prefix and filename
get_line_length() {
    local prefix="$1"
    local file="$2"
    local indent_level=$(get_indent_level "$prefix")
    echo $(( ${#prefix} + ${#file} + 4 ))  # +4 for "└── " or "├── "
}

# Find the longest line in the tree
find_longest_line() {
    local dir="$1"
    local prefix="$2"
    local files=($(ls -A "$dir" | grep -Ev "$EXCLUDE_PATTERN" | sort))
    
    for file in "${files[@]}"; do
        local length=$(get_line_length "$prefix" "$file")
        if (( length > LONGEST_LINE )); then
            LONGEST_LINE=$length
        fi
        
        local path="$dir/$file"
        if [[ -d "$path" ]]; then
            find_longest_line "$path" "${prefix}│   "
        fi
    done
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--depth)
            if [ -z "$2" ]; then
                echo "Error: Depth argument is required"
                show_usage
            fi
            MAX_DEPTH="-L $2"
            shift 2
            ;;
        -e|--exclude)
            if [ -z "$2" ]; then
                echo "Error: Exclude pattern is required"
                show_usage
            fi
            EXCLUDE_PATTERN="$2"
            shift 2
            ;;
        -p|--placeholder)
            ADD_PLACEHOLDERS=true
            shift
            ;;
        -h|--help)
            show_usage
            ;;
        -*)
            echo "Error: Unknown option: $1"
            show_usage
            ;;
        *)
            TARGET_DIR="$1"
            shift
            ;;
    esac
done

# Generate tree structure
generate_tree() {
    local dir="$1"
    local prefix="$2"
    local last="$3"
    local files=($(ls -A "$dir" | grep -Ev "$EXCLUDE_PATTERN" | sort))
    local count=${#files[@]}
    local i=0

    for file in "${files[@]}"; do
        ((i++))
        local is_last=$([[ $i -eq $count ]] && echo true || echo false)
        local path="$dir/$file"
        local line_length=$(get_line_length "$prefix" "$file")
        local padding_length=$((LONGEST_LINE - line_length + MIN_PADDING))
        local padding=""
        
        # Ensure we don't exceed MAX_LINE_LENGTH
        if (( LONGEST_LINE + MIN_PADDING + 2 > MAX_LINE_LENGTH )); then
            padding_length=$((MAX_LINE_LENGTH - line_length - 2))  # -2 for " #"
        fi
        
        if (( padding_length > 0 )); then
            padding=$(printf "%*s" $padding_length "")
        fi
        
        # Output the line
        if [[ $is_last == true ]]; then
            echo "${prefix}└── ${file}${padding}${ADD_PLACEHOLDERS:+ #}"
            new_prefix="${prefix}    "
        else
            echo "${prefix}├── ${file}${padding}${ADD_PLACEHOLDERS:+ #}"
            new_prefix="${prefix}│   "
        fi
        
        if [[ -d "$path" ]]; then
            generate_tree "$path" "$new_prefix" "$is_last"
        fi
    done
}

# Start tree generation
if [[ ! -d "$TARGET_DIR" ]]; then
    echo "Error: Directory not found: $TARGET_DIR"
    exit 1
fi

# If placeholders are requested, first find the longest line
if [[ $ADD_PLACEHOLDERS == true ]]; then
    find_longest_line "$TARGET_DIR" ""
fi

echo "."
generate_tree "$TARGET_DIR" "" true 