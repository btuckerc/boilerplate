#!/bin/sh
# Managed by chezmoi - https://github.com/btuckerc/boilerplate
# Shared POSIX-compatible shell configuration
# Sourced by both ~/.zshrc and ~/.bashrc

# === Environment Variables ===
export EDITOR="nvim"
export DEV_DIR=~/Documents/GitHub

# XDG Base Directory Specification
# https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"

# History file locations (XDG-compliant)
export LESSHISTFILE="$XDG_CACHE_HOME/less_history"
export PYTHON_HISTORY="$XDG_DATA_HOME/python/history"

# === PATH Setup ===
# Add ~/.local/bin to PATH if it exists
[ -d "$HOME/.local/bin" ] && export PATH="$HOME/.local/bin:$PATH"

# === Pager Configuration ===
export MANPAGER="less -R --use-color -Dd+r -Du+b"
export LESS="R --use-color -Dd+r -Du+b"

# === FZF Configuration ===
export FZF_DEFAULT_OPTS="--style minimal --color 16 --layout=reverse --height 30% --preview='bat -p --color=always {}'"
export FZF_CTRL_R_OPTS="--style minimal --color 16 --info inline --no-sort --no-preview"

# === Aliases (POSIX-compatible) ===
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

# Git aliases
alias gs='git status'
alias ga='git add'
alias gb='git branch'
alias gc='git commit'
alias gd='git diff'
alias gl='git --no-pager log --oneline --decorate --all --graph'
alias gst='git status'
alias gpl='git pull'
alias gps='git push'
alias gcm='git commit -m'

# Git tools
alias lg='lazygit'

# Editor aliases
alias vim='nvim'
alias v.='nvim .'
alias practice='nvim +VimBeGood'

# Python virtual environment
alias venv_activate='source venv/bin/activate'
alias vde='deactivate'

# Obsidian/notetaking aliases
alias oo="cd '$HOME/Documents/00-Vault/00 - Inbox/'"
alias dn='nvim +ObsidianToday'

# Fun/Utility aliases
alias rot13="tr 'A-Za-z' 'N-ZA-Mn-za-m'"
alias dunnet="emacs -batch -l dunnet"

# === Functions ===

# Navigate to GitHub directory
dev() {
    TARGET_DIR=~/Documents/GitHub
    if [ ! -d "$TARGET_DIR" ]; then
        echo "$(date): GitHub directory not found. Creating..." >> ~/.shellrc_log
        mkdir -p "$TARGET_DIR"
    fi
    cd "$TARGET_DIR" || echo "$(date): Failed to navigate to $TARGET_DIR" >> ~/.shellrc_log
}

# Create and activate Python virtual environment
venv() {
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    echo "Activating virtual environment..."
    . venv/bin/activate
}

# File extraction helper
ee() {
    if [ -f "$1" ]; then
        case $1 in
            *.tar.bz2)   tar xvjf "$1"     ;;
            *.tar.gz)    tar xvzf "$1"     ;;
            *.bz2)       bunzip2 "$1"      ;;
            *.rar)       unrar x "$1"      ;;
            *.gz)        gunzip "$1"       ;;
            *.tar)       tar xvf "$1"      ;;
            *.tbz2)      tar xvjf "$1"     ;;
            *.tgz)       tar xvzf "$1"     ;;
            *.zip)       unzip "$1"        ;;
            *.Z)         uncompress "$1"   ;;
            *.7z)        7z x "$1"         ;;
            *)           echo "'$1' cannot be extracted via ee" ;;
        esac
    else
        echo "'$1' is not a valid file!"
    fi
}

# Archive creation helpers
mtar() {
    tar cvzf "${1%%/}.tar.gz"  "${1%%/}/";
}

mzip() {
    zip -r "${1%%/}.zip" "$1";
}

# File swap function
swap() {
    local TMPFILE=tmp.$$
    [ $# -ne 2 ] && echo "swap: 2 arguments needed" && return 1
    [ ! -e "$1" ] && echo "swap: $1 does not exist" && return 1
    [ ! -e "$2" ] && echo "swap: $2 does not exist" && return 1
    mv "$1" "$TMPFILE"
    mv "$2" "$1"
    mv "$TMPFILE" "$2"
}

# Make directory and cd into it
mc() {
    local dir="$1"
    if [ -z "$dir" ]; then
        echo "Usage: mc <directory>"
        return 1
    fi
    mkdir -p -- "$dir" && cd -- "$dir"
}

# New note helper function
nn() {
    if [ -z "$1" ]; then
        echo "Error: No filename provided."
        echo "Usage: nn <filename>"
        return 1
    fi
    local filename="$1.md"
    vim "$filename"
}

# === Conditional Tool Loading ===

# Initialize zoxide (smart cd) if available
if command -v zoxide >/dev/null 2>&1; then
    if [ -n "$ZSH_VERSION" ]; then
        eval "$(zoxide init zsh)"
    elif [ -n "$BASH_VERSION" ]; then
        eval "$(zoxide init bash)"
    fi
fi

# Load FZF if available (shell-specific files)
if [ -n "$ZSH_VERSION" ]; then
    [ -f "$XDG_CONFIG_HOME/fzf/.fzf.zsh" ] && . "$XDG_CONFIG_HOME/fzf/.fzf.zsh"
elif [ -n "$BASH_VERSION" ]; then
    [ -f "$XDG_CONFIG_HOME/fzf/.fzf.bash" ] && . "$XDG_CONFIG_HOME/fzf/.fzf.bash"
fi

# Load Cargo if available
[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"

# Load Deno if available
[ -f "$HOME/.deno/env" ] && . "$HOME/.deno/env"

# Load secrets if they exist
[ -f "$HOME/.secrets" ] && . "$HOME/.secrets"

# === Logging ===
LOGFILE=~/.shellrc_log
