#!/bin/zsh

# Prevent multiple sourcing
if [[ -n "$_SHELLRC_SOURCED" ]]; then
    return
fi
export _SHELLRC_SOURCED=true

# Load aliases
if [ -f "$HOME/.zsh_aliases" ]; then
    source "$HOME/.zsh_aliases"
fi

# Pyenv setup
if command -v pyenv >/dev/null; then
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init --path)"
    eval "$(pyenv init -)"
    
    if pyenv commands | grep -q virtualenv-init; then
        eval "$(pyenv virtualenv-init -)"
    fi
fi

# Functions
dev() {
    TARGET_DIR=~/Documents/GitHub
    if [ ! -d "$TARGET_DIR" ]; then
        echo "$(date): GitHub directory not found. Creating..." >> ~/.shellrc_log
        mkdir -p "$TARGET_DIR"
    fi
    cd "$TARGET_DIR" || echo "$(date): Failed to navigate to $TARGET_DIR" >> ~/.shellrc_log
}

venv() {
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    echo "Activating virtual environment..."
    source venv/bin/activate
}

# File extraction helper
ee() {
    if [ -f "$1" ]; then
        case $1 in
            *.tar.bz2)   tar xvjf $1     ;;
            *.tar.gz)    tar xvzf $1     ;;
            *.bz2)       bunzip2 $1      ;;
            *.rar)       unrar x $1      ;;
            *.gz)        gunzip $1       ;;
            *.tar)       tar xvf $1      ;;
            *.tbz2)      tar xvjf $1     ;;
            *.tgz)       tar xvzf $1     ;;
            *.zip)       unzip $1        ;;
            *.Z)         uncompress $1   ;;
            *.7z)        7z x $1         ;;
            *)           echo "'$1' cannot be extracted via >extract<" ;;
        esac
    else
        echo "'$1' is not a valid file!"
    fi
}

# Archive creation helpers
mtar() { tar cvzf "${1%%/}.tar.gz"  "${1%%/}/"; }
mzip() { zip -r "${1%%/}.zip" "$1" ; }

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

# Environment variables
export DEV_DIR=~/Documents/GitHub
export EDITOR="vim"
export PATH="$PATH:$HOME/.local/bin"

# History settings (Zsh-specific)
HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000
setopt SHARE_HISTORY
setopt HIST_IGNORE_DUPS
setopt HIST_IGNORE_SPACE
setopt EXTENDED_HISTORY
setopt INC_APPEND_HISTORY

# Zsh-specific settings
setopt AUTO_CD              # If command is a directory path, cd into it
setopt NO_CASE_GLOB        # Case insensitive globbing
setopt NUMERIC_GLOB_SORT   # Sort filenames numerically when relevant
setopt EXTENDED_GLOB       # Extended globbing capabilities

# Load Homebrew
eval "$(/opt/homebrew/bin/brew shellenv)"

# Load Starship prompt if installed
if command -v starship >/dev/null; then
    eval "$(starship init zsh)"
fi

# Load FZF
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# Load Cargo
[ -f "$HOME/.cargo/env" ] && source "$HOME/.cargo/env"

# Load Deno
[ -f "$HOME/.deno/env" ] && source "$HOME/.deno/env"

# Load secrets if they exist
[ -f ~/.secrets ] && source ~/.secrets

# Logging
LOGFILE=~/.shellrc_log
echo "$(date): Zsh shell loaded" >> $LOGFILE