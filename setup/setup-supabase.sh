#!/bin/bash
# Copyright (c) 2024 Tucker Craig
# See LICENSE file for full license details.

# Get the absolute directory of the current script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common utilities
source "$SCRIPT_DIR/../utils/scripts/common.sh"

# Function to handle errors and exit
handle_error() {
    echo "Error: $1"
    exit 1
}

# Function to show usage
show_usage() {
    cat << EOF
NAME
    $(basename "$0") - Set up a Supabase project with interactive configuration

SYNOPSIS
    $(basename "$0") [OPTIONS] [PROJECT_NAME]

DESCRIPTION
    Sets up a new Supabase project with interactive configuration options.
    Supports both local development and cloud deployment setups.

ARGUMENTS
    PROJECT_NAME
        Name for your Supabase project [default: current directory name]

OPTIONS
    -l, --local
        Set up only local development environment

    -f, --force
        Skip confirmation prompts

    -h, --help
        Display this help message and exit

EXAMPLES
    $(basename "$0")
        Interactive setup in current directory

    $(basename "$0") my-app
        Create new project named 'my-app'

    $(basename "$0") -l
        Local development setup only

    $(basename "$0") -f my-app
        Create project 'my-app' without confirmation prompts

NOTES
    - Requires Docker for local development
    - Will create .env file with necessary configurations
    - Can integrate with existing projects
    - Supports both local and cloud deployments
EOF
    exit 1
}

# Default values
PROJECT_NAME=$(basename "$(pwd)")
LOCAL_ONLY=false
FORCE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -l|--local)
            LOCAL_ONLY=true
            shift
            ;;
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
            PROJECT_NAME="$1"
            shift
            ;;
    esac
done

# Function to check Docker
check_docker() {
    echo "Checking Docker installation..."
    if ! check_command docker; then
        echo "Docker is not installed. Installing Docker..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            install_brew_package docker
        else
            handle_error "Please install Docker manually: https://docs.docker.com/get-docker/"
        fi
    fi
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        handle_error "Docker is not running. Please start Docker Desktop."
    fi
}

# Function to check Supabase CLI
check_supabase_cli() {
    echo "Checking Supabase CLI..."
    if ! check_command supabase; then
        echo "Supabase CLI is not installed. Installing..."
        install_brew_package supabase
    fi
}

# Function to initialize local development
init_local_dev() {
    echo "Initializing local Supabase development environment..."
    
    # Initialize Supabase project
    supabase init || handle_error "Failed to initialize Supabase project"
    
    # Start Supabase services
    echo "Starting Supabase services..."
    supabase start || handle_error "Failed to start Supabase services"
    
    # Get local credentials
    local db_url=$(supabase status | grep "DB URL" | awk '{print $NF}')
    local anon_key=$(supabase status | grep "anon key" | awk '{print $NF}')
    local service_role_key=$(supabase status | grep "service_role key" | awk '{print $NF}')
    
    # Create .env file
    cat > .env << EOF
# Supabase Configuration
SUPABASE_URL=http://localhost:54321
SUPABASE_ANON_KEY=$anon_key
SUPABASE_SERVICE_ROLE_KEY=$service_role_key
DATABASE_URL=$db_url
EOF
    
    echo "Created .env file with local credentials"
}

# Function to set up cloud project
setup_cloud_project() {
    # Check if logged in
    if ! supabase projects list >/dev/null 2>&1; then
        echo "Please log in to Supabase:"
        supabase login || handle_error "Failed to log in to Supabase"
    fi
    
    # Create new project
    echo "Creating Supabase project: $PROJECT_NAME"
    supabase projects create "$PROJECT_NAME" --org-id "$(supabase orgs list | grep -v ID | head -n1 | awk '{print $1}')" || handle_error "Failed to create project"
    
    # Link to local project
    echo "Linking to local project..."
    supabase link --project-ref "$(supabase projects list | grep "$PROJECT_NAME" | awk '{print $1}')" || handle_error "Failed to link project"
}

# Main setup flow
echo "🚀 Setting up Supabase project: $PROJECT_NAME"

# Check prerequisites
check_docker
check_supabase_cli

# Initialize local development
echo "Setting up local development environment..."
init_local_dev

# Set up cloud project if requested
if [ "$LOCAL_ONLY" = false ]; then
    if [ "$FORCE" = false ]; then
        read -p "Would you like to create a cloud project? [Y/n] " create_cloud
        create_cloud=${create_cloud:-Y}
    else
        create_cloud="Y"
    fi
    
    if [[ "${create_cloud,,}" =~ ^y ]]; then
        setup_cloud_project
    fi
fi

# Create .gitignore if it doesn't exist
if [ ! -f .gitignore ]; then
    cat > .gitignore << EOF
# Supabase
.env
.env.*
!.env.example

# Database
**/supabase/.temp/
EOF
fi

# Success message
echo "✨ Supabase setup complete!"
echo
echo "Next steps:"
echo "1. Review your .env file"
echo "2. Start developing with 'supabase start'"
echo "3. Use 'supabase db diff' to track schema changes"
if [ "$LOCAL_ONLY" = false ]; then
    echo "4. Deploy changes with 'supabase db push'"
fi 