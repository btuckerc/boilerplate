#!/bin/bash
# Copyright (c) 2024 Tucker Craig
# See LICENSE file for full license details.

# Get the absolute directory of the current script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source common utilities
COMMON_SCRIPT="$REPO_ROOT/utils/scripts/common.sh"
if [ -f "$COMMON_SCRIPT" ]; then
    source "$COMMON_SCRIPT"
else
    echo "Error: common.sh not found at: $COMMON_SCRIPT"
    exit 1
fi

# Backup existing Zsh files
print_step "Backing up existing Zsh files..."
backup_file() {
    if [ -f "$1" ]; then
        cp "$1" "$1.bak.$(date +%Y%m%d_%H%M%S)"
        print_success "Backed up $1"
    fi
}

backup_file ~/.zshrc
backup_file ~/.zprofile
backup_file ~/.zsh_aliases

# Create new Zsh configuration files
print_step "Creating new Zsh configuration files..."

# Create .zsh_aliases if it doesn't exist
if [ ! -f ~/.zsh_aliases ]; then
    if [ -f ~/.bash_aliases ]; then
        print_step "Converting bash_aliases to zsh_aliases..."
        cp ~/.bash_aliases ~/.zsh_aliases
    else
        print_step "Creating new zsh_aliases..."
        touch ~/.zsh_aliases
    fi
fi

# Initialize new .zshrc
print_step "Creating new .zshrc..."
cat > ~/.zshrc << 'EOL'
# Generated by bash-to-zsh migration script
# Sourcing order: zshenv -> zprofile -> zshrc -> zlogin

# Load aliases
[ -f ~/.zsh_aliases ] && source ~/.zsh_aliases

# Zsh-specific settings
setopt AUTO_CD              # If command is a directory path, cd into it
setopt NO_CASE_GLOB        # Case insensitive globbing
setopt NUMERIC_GLOB_SORT   # Sort filenames numerically when relevant
setopt EXTENDED_GLOB       # Extended globbing capabilities

# History settings
HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000
setopt SHARE_HISTORY
setopt HIST_IGNORE_DUPS
setopt HIST_IGNORE_SPACE
setopt EXTENDED_HISTORY
setopt INC_APPEND_HISTORY
EOL

# Transfer relevant non-Bash-specific content from .bashrc
if [ -f ~/.bashrc ]; then
    print_step "Analyzing .bashrc for compatible configurations..."
    # Extract environment variables
    grep "^export" ~/.bashrc >> ~/.zshrc
    # Extract functions (excluding those with Bash-specific syntax)
    awk '/^[a-zA-Z_-]+\(\).*{/,/^}/ { print }' ~/.bashrc >> ~/.zshrc
fi

# Transfer relevant content from .bash_profile to .zprofile
if [ -f ~/.bash_profile ]; then
    print_step "Creating .zprofile from .bash_profile..."
    # Extract PATH and environment variables
    grep "^export" ~/.bash_profile > ~/.zprofile
    # Extract non-Bash-specific evaluations
    grep "^eval" ~/.bash_profile | grep -v "bash" >> ~/.zprofile
fi

# Add common source commands
print_step "Adding common source commands..."
cat >> ~/.zshrc << 'EOL'

# Load Homebrew
eval "$(/opt/homebrew/bin/brew shellenv)"

# Initialize pyenv if installed
if command -v pyenv >/dev/null; then
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init --path)"
    eval "$(pyenv init -)"
fi

# Load starship prompt if installed
if command -v starship >/dev/null; then
    eval "$(starship init zsh)"
fi

# Source additional configurations
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh
[ -f "$HOME/.cargo/env" ] && source "$HOME/.cargo/env"
[ -f "$HOME/.deno/env" ] && source "$HOME/.deno/env"
[ -f ~/.secrets ] && source ~/.secrets
EOL

print_success "Migration complete! New Zsh configuration files have been created."

# Offer to switch to Zsh if not already the default
if [ "$SHELL" != "/bin/zsh" ]; then
    if confirm "Your current shell is $SHELL. Would you like to switch to Zsh?"; then
        print_step "Changing default shell to Zsh..."
        chsh -s /bin/zsh
        print_success "Default shell changed to Zsh. Please restart your terminal."
    else
        print_warning "Default shell not changed."
    fi
fi

print_success "✨ Done! Please restart your terminal for changes to take effect."
