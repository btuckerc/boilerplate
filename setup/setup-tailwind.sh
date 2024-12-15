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

# Check for required commands
check_command "node"
check_command "npm"
check_command "git"

# Get user input for project name
read -p "Enter the name of your new T3 project: " PROJECT_NAME

# Run npx create-t3-app@latest
npx create-t3-app@latest "$PROJECT_NAME" || handle_error "Failed to initialize the T3 app project."

# Navigate to the project directory
cd "$PROJECT_NAME" || handle_error "Failed to navigate to $PROJECT_NAME directory."

# Install dependencies
echo "Installing dependencies..."
npm install || handle_error "Failed to install dependencies."

# Generate a custom README file
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
git init || handle_error "Failed to initialize Git repository."
git add . || handle_error "Failed to stage files."
git commit -m "Initial commit for $PROJECT_NAME using T3 App" || handle_error "Failed to create initial commit."

echo "T3 App project setup complete! Navigate to the $PROJECT_NAME directory and start building your app."
