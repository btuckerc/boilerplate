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

print_step "Setting up Git authentication..."

# Step 1: Configure Git Username
read -p "Enter your GitHub username: " GITHUB_USERNAME
git config --global user.name "$GITHUB_USERNAME"

# Step 2: Configure Git Email
print_step "Configuring Git email..."
if confirm "Do you want to use GitHub's private noreply email instead of your public email?" "n"; then
    GITHUB_EMAIL="$GITHUB_USERNAME@users.noreply.github.com"
else
    read -p "Enter your public email address: " GITHUB_EMAIL
fi

git config --global user.email "$GITHUB_EMAIL"
print_success "Git user configuration set with email: $GITHUB_EMAIL"

# Step 3: Choose Authentication Method
if confirm "Do you want to use SSH for authentication? (Choose 'n' for HTTPS)" "y"; then
    AUTH_METHOD="ssh"
else
    AUTH_METHOD="https"
fi

if [[ "$AUTH_METHOD" == "ssh" ]]; then
    # SSH setup
    SSH_KEY="$HOME/.ssh/id_rsa"
    if [ -f "$SSH_KEY" ]; then
        print_warning "SSH key already exists: $SSH_KEY"
    else
        print_step "Generating a new SSH key..."
        ssh-keygen -t rsa -b 4096 -C "$GITHUB_EMAIL" -f "$SSH_KEY" -N "" || {
            print_error "Failed to generate SSH key."
            exit 1
        }
        eval "$(ssh-agent -s)"
        ssh-add "$SSH_KEY"
    fi
    print_step "Your public SSH key is:"
    cat "$SSH_KEY.pub"

    # Copy SSH key to clipboard on macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        pbcopy < "$SSH_KEY.pub"
        print_success "The SSH key has been copied to your clipboard."
    else
        print_warning "Manually copy the SSH key from above."
    fi

    # Add a clickable link
    print_step "Add it to GitHub: https://github.com/settings/keys"
    echo -e "\033]8;;https://github.com/settings/keys\033\\Click here to add the key to GitHub\033]8;;\033\\"

    # Set Git to use SSH
    git config --global url."git@github.com:".insteadOf "https://github.com/"
    print_success "Git is now configured to use SSH for GitHub."
elif [[ "$AUTH_METHOD" == "https" ]]; then
    # HTTPS setup
    print_step "Go to https://github.com/settings/tokens and generate a new Personal Access Token."
    echo -e "\033]8;;https://github.com/settings/tokens\033\\Click here to generate a Personal Access Token\033]8;;\033\\"
    read -p "Enter your PAT: " PAT
    git config --global credential.helper store
    echo "https://$GITHUB_USERNAME:$PAT@github.com" > ~/.git-credentials
    print_success "Personal Access Token configured."

    # Remove SSH preference, if previously set
    git config --global --unset url."git@github.com:".insteadOf
    print_success "Git is now configured to use HTTPS for GitHub."
else
    print_error "Invalid option. Please choose ssh or https."
    exit 1
fi

# Step 4: Test Connection
print_step "Testing GitHub connection..."
if [[ "$AUTH_METHOD" == "ssh" ]]; then
    ssh -T git@github.com || {
        print_error "Failed to connect to GitHub via SSH. Please check your configuration."
        exit 1
    }
elif [[ "$AUTH_METHOD" == "https" ]]; then
    git ls-remote "https://github.com/$GITHUB_USERNAME/test-repo.git" &>/dev/null || {
        print_error "Failed to connect to GitHub via HTTPS. Please check your configuration."
        exit 1
    }
fi

# Step 5: Verify and Display Git Configuration
print_success "Git authentication setup complete."
print_step "Current Git configuration:"
git config --global --list
