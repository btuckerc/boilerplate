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

# Check for required commands
print_step "Checking required dependencies..."
check_command "node" || install_brew_package "node"
check_command "npm" || install_brew_package "node"  # npm comes with node
check_command "git" || install_brew_package "git"

# Get user input for project name
read -p "Enter the name of your new T3 project: " PROJECT_NAME

# Run npx create-t3-app@latest
print_step "Creating new T3 project: $PROJECT_NAME..."
npx create-t3-app@latest "$PROJECT_NAME" || {
    print_error "Failed to initialize the T3 app project."
    exit 1
}

# Navigate to the project directory
cd "$PROJECT_NAME" || {
    print_error "Failed to navigate to $PROJECT_NAME directory."
    exit 1
}

# Install dependencies
print_step "Installing dependencies..."
npm install || {
    print_error "Failed to install dependencies."
    exit 1
}

# Generate a custom README file
print_step "Generating README.md..."
cat <<EOF >README.md
# $PROJECT_NAME

This project was created using the T3 App.

## Features
- Next.js
- Tailwind CSS
- TypeScript
- Optional integrations (e.g., Prisma, NextAuth)

## Setup Instructions

1. Navigate to the project directory:
   \`\`\`bash
   cd $PROJECT_NAME
   \`\`\`

2. Start the development server:
   \`\`\`bash
   npm run dev
   \`\`\`

3. Customize your project as needed and enjoy!

## Learn More
For additional documentation, visit the [T3 Stack website](https://create.t3.gg).
EOF

# Initialize Git repository
print_step "Initializing Git repository..."
git init || {
    print_error "Failed to initialize Git repository."
    exit 1
}

git add . || {
    print_error "Failed to stage files."
    exit 1
}

git commit -m "Initial commit for $PROJECT_NAME using T3 App" || {
    print_error "Failed to create initial commit."
    exit 1
}

print_success "✨ T3 App project setup complete!"
print_success "Navigate to the $PROJECT_NAME directory and start building your app."
