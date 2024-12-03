#!/bin/bash

# Function to handle errors and exit
handle_error() {
    echo "Error: $1"
    exit 1
}

# Check if required commands are available
check_command() {
    if ! command -v $1 &>/dev/null; then
        echo "$1 is not installed. Installing..."
        case $1 in
        node | npm)
            if [[ "$OSTYPE" == "darwin"* ]]; then
                brew install node || handle_error "Failed to install Node.js. Install it manually."
            else
                handle_error "Automatic installation for $1 is not supported on this OS. Please install it manually."
            fi
            ;;
        git)
            if [[ "$OSTYPE" == "darwin"* ]]; then
                brew install git || handle_error "Failed to install Git. Install it manually."
            else
                handle_error "Automatic installation for $1 is not supported on this OS. Please install it manually."
            fi
            ;;
        *)
            handle_error "Unknown command $1. Cannot install automatically."
            ;;
        esac
    fi
}

# Verify Node.js version
verify_node_version() {
    NODE_VERSION=$(node -v | sed 's/v//')
    MIN_NODE_VERSION="14.13.1"
    if [[ $(printf "%s\n" "$MIN_NODE_VERSION" "$NODE_VERSION" | sort -V | head -n1) != "$MIN_NODE_VERSION" ]]; then
        handle_error "Node.js version must be >= $MIN_NODE_VERSION. Current version: $NODE_VERSION. Update Node.js."
    fi
}

# Verify npm version
verify_npm_version() {
    NPM_VERSION=$(npm -v)
    MIN_NPM_VERSION="6.0.0"
    if [[ $(printf "%s\n" "$MIN_NPM_VERSION" "$NPM_VERSION" | sort -V | head -n1) != "$MIN_NPM_VERSION" ]]; then
        handle_error "npm version must be >= $MIN_NPM_VERSION. Current version: $NPM_VERSION. Update npm."
    fi
}

# Clear npm cache
clear_npm_cache() {
    echo "Clearing npm cache..."
    npm cache clean --force || handle_error "Failed to clear npm cache."
}

# Check required commands and versions
check_command "node"
check_command "npm"
check_command "git"
verify_node_version
verify_npm_version

# Get user input for project directory name
read -p "Enter the name of your new project directory: " PROJECT_NAME

# Create the project directory
mkdir "$PROJECT_NAME" || handle_error "Failed to create directory $PROJECT_NAME"
cd "$PROJECT_NAME" || handle_error "Failed to navigate to $PROJECT_NAME"

# Initialize Git repository
git init || handle_error "Failed to initialize Git repository."

# Create package.json with npm
npm init -y || handle_error "Failed to initialize npm project."

# Install Tailwind CSS Beta
npm install -D tailwindcss@4.0.0-beta.1 || handle_error "Failed to install Tailwind CSS 4 Beta."

# Ensure `npx` resolves correctly by using an explicit path
NPX_PATH=$(npm bin)
if [ -z "$NPX_PATH" ]; then
    handle_error "Failed to locate npm binaries. Ensure npm is properly installed."
fi
export PATH="$NPX_PATH:$PATH"

# Initialize Tailwind CSS configuration
if ! npx tailwindcss init; then
    handle_error "Failed to initialize Tailwind CSS configuration. Ensure npx is functional."
fi

# Create project structure and files
mkdir src || handle_error "Failed to create src directory."

cat <<EOF >src/index.html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tailwind Project</title>
    <link href="styles.css" rel="stylesheet">
</head>
<body>
    <h1 class="text-3xl font-bold underline">Hello, Tailwind!</h1>
</body>
</html>
EOF

cat <<EOF >src/styles.css
@tailwind base;
@tailwind components;
@tailwind utilities;
EOF

# Manually create package.json scripts for the build command
cat <<EOF > package.json
{
  "name": "$PROJECT_NAME",
  "version": "1.0.0",
  "description": "",
  "main": "index.js",
  "scripts": {
    "build": "npx tailwindcss -i ./src/styles.css -o ./dist/styles.css --watch"
  },
  "author": "",
  "license": "ISC",
  "dependencies": {}
}
EOF

# Create README file
cat <<EOF >README.md
# $PROJECT_NAME

This project uses Tailwind.

## Setup

1. Ensure Node.js, npm, and Git are installed.
2. Navigate to the project directory:
   \`\`\`bash
   cd $PROJECT_NAME
   \`\`\`
3. Install dependencies:
   \`\`\`bash
   npm install
   \`\`\`

## Usage

To build your Tailwind CSS files and watch for changes:

\`\`\`bash
npm run build
\`\`\`

Open \`src/index.html\` in a browser to view your project.
EOF

# Git operations
git add . || handle_error "Failed to stage files in Git."
git commit -m "Initial commit with Tailwind setup." || handle_error "Failed to commit files to Git."

echo "Project setup complete. Navigate to $PROJECT_NAME and start building with Tailwind CSS!"
