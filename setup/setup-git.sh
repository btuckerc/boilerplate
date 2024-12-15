#!/bin/bash

echo "Setting up Git authentication..."

# Step 1: Configure Git Username
read -p "Enter your GitHub username: " GITHUB_USERNAME
git config --global user.name "$GITHUB_USERNAME"

# Step 2: Configure Git Email
echo "GitHub provides an option to use a private 'noreply' email address for commits."
read -p "Do you want to use your public email address or GitHub's private noreply email? (public/private): " EMAIL_PREF

if [[ "$EMAIL_PREF" == "private" ]]; then
    GITHUB_EMAIL="$GITHUB_USERNAME@users.noreply.github.com"
else
    read -p "Enter your public email address: " GITHUB_EMAIL
fi

git config --global user.email "$GITHUB_EMAIL"
echo "Git user configuration set with email: $GITHUB_EMAIL"

# Step 3: Choose Authentication Method
read -p "Do you want to use SSH or HTTPS for authentication? (ssh/https): " AUTH_METHOD

if [[ "$AUTH_METHOD" == "ssh" ]]; then
    # SSH setup
    SSH_KEY="$HOME/.ssh/id_rsa"
    if [ -f "$SSH_KEY" ]; then
        echo "SSH key already exists: $SSH_KEY"
    else
        echo "Generating a new SSH key..."
        ssh-keygen -t rsa -b 4096 -C "$GITHUB_EMAIL" -f "$SSH_KEY" -N ""
        eval "$(ssh-agent -s)"
        ssh-add "$SSH_KEY"
    fi
    echo "Your public SSH key is:"
    cat "$SSH_KEY.pub"

    # Copy SSH key to clipboard on macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        pbcopy < "$SSH_KEY.pub"
        echo "The SSH key has been copied to your clipboard."
    else
        echo "Manually copy the SSH key from above."
    fi

    # Add a clickable link
    echo "Add it to GitHub: https://github.com/settings/keys"
    echo -e "\033]8;;https://github.com/settings/keys\033\\Click here to add the key to GitHub\033]8;;\033\\"

    # Set Git to use SSH
    git config --global url."git@github.com:".insteadOf "https://github.com/"
    echo "Git is now configured to use SSH for GitHub."
elif [[ "$AUTH_METHOD" == "https" ]]; then
    # HTTPS setup
    echo "Go to https://github.com/settings/tokens and generate a new Personal Access Token."
    echo -e "\033]8;;https://github.com/settings/tokens\033\\Click here to generate a Personal Access Token\033]8;;\033\\"
    read -p "Enter your PAT: " PAT
    git config --global credential.helper store
    echo "https://$GITHUB_USERNAME:$PAT@github.com" > ~/.git-credentials
    echo "Personal Access Token configured."

    # Remove SSH preference, if previously set
    git config --global --unset url."git@github.com:".insteadOf
    echo "Git is now configured to use HTTPS for GitHub."
else
    echo "Invalid option. Please choose ssh or https."
    exit 1
fi

# Step 4: Test Connection
if [[ "$AUTH_METHOD" == "ssh" ]]; then
    ssh -T git@github.com
elif [[ "$AUTH_METHOD" == "https" ]]; then
    git ls-remote https://github.com/$GITHUB_USERNAME/test-repo.git
fi

# Step 5: Verify and Display Git Configuration
echo "Git authentication setup complete."
echo "Current Git configuration:"
git config --global --list