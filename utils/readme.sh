#!/bin/bash

# Copyright (c) 2024 Tucker Craig
# See LICENSE file for full license details.

# Get the absolute directory of the current script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to show usage
show_usage() {
    cat << EOF
Generate a README.md file for a project directory.

Usage: 
    $(basename "$0") [options] [directory]

Arguments:
    directory             Directory to generate README for [default: current directory]

Options:
    -f, --force          Overwrite existing README.md
    -h, --help          Show this help message

Examples:
    $(basename "$0")                    # Generate README in current directory
    $(basename "$0") ~/projects/app     # Generate README in specific directory
    $(basename "$0") -f                 # Overwrite existing README.md

Notes:
    - Will prompt for project name if not obvious from directory name
    - Will ask whether to include MIT license
    - Uses tree.sh to generate directory structure
EOF
    exit 1
}

# Default values
TARGET_DIR="."
FORCE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            FORCE=true
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

# Check if target directory exists
if [[ ! -d "$TARGET_DIR" ]]; then
    echo "Error: Directory not found: $TARGET_DIR"
    exit 1
fi

# Check if README.md already exists
if [[ -f "$TARGET_DIR/README.md" ]] && [[ "$FORCE" != true ]]; then
    echo "Error: README.md already exists. Use -f to overwrite."
    exit 1
fi

# Get project name (default to directory name)
PROJECT_NAME=$(basename "$(cd "$TARGET_DIR" && pwd)")
read -p "Project name [$PROJECT_NAME]: " input
PROJECT_NAME=${input:-$PROJECT_NAME}

# Get project description
read -p "Project description: " PROJECT_DESCRIPTION

# Ask about MIT license
read -p "Include MIT license? [Y/n]: " include_license
include_license=${include_license:-Y}

# Generate directory tree
echo "Generating directory structure..."
TREE_OUTPUT=$("$SCRIPT_DIR/tree.sh" -p "$TARGET_DIR")

# Generate README content
cat > "$TARGET_DIR/README.md" << EOF
# ${PROJECT_NAME}

${PROJECT_DESCRIPTION}

## Directory Structure

\`\`\`
${TREE_OUTPUT}
\`\`\`

## Getting Started

### Prerequisites

List any prerequisites here.

### Installation

1. Clone the repository
   \`\`\`bash
   git clone https://github.com/yourusername/${PROJECT_NAME}.git
   \`\`\`

2. Navigate to the project directory
   \`\`\`bash
   cd ${PROJECT_NAME}
   \`\`\`

## Usage

Add usage instructions here.

## Contributing

1. Fork the project
2. Create your feature branch (\`git checkout -b feature/AmazingFeature\`)
3. Commit your changes (\`git commit -m 'Add some AmazingFeature'\`)
4. Push to the branch (\`git push origin feature/AmazingFeature\`)
5. Open a Pull Request

EOF

# Add license if requested
if [[ "${include_license,,}" =~ ^y ]]; then
    cat >> "$TARGET_DIR/README.md" << EOF

## License

Copyright (c) $(date +%Y) ${USER^}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF
fi

echo "✨ README.md generated successfully!" 