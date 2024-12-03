# ~/.bashrc or ~/.zshrc

# Detect shell type
is_bash=false
is_zsh=false

if [ -n "$BASH_VERSION" ]; then
    is_bash=true
elif [ -n "$ZSH_VERSION" ]; then
    is_zsh=true
fi

# Prevent multiple sourcing
if [[ -n "$_SHELLRC_SOURCED" ]]; then
    return
fi
export _SHELLRC_SOURCED=true

# Load .bash_aliases or .zsh_aliases if it exists, or initialize with default aliases
ALIASES_FILE="$HOME/.bash_aliases"
if $is_zsh; then
    ALIASES_FILE="$HOME/.zsh_aliases"
fi

if [ -f "$ALIASES_FILE" ]; then
    source "$ALIASES_FILE"
else
    echo "Creating $ALIASES_FILE with default aliases..."
    cat <<'EOF' > "$ALIASES_FILE"
# Default aliases

# Colorful and convenient ls
alias ls='ls --color=auto'
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

# Git shortcuts
alias gst="git status"
alias gpl="git pull"
alias gps="git push"
alias gcm="git commit -m"

# Python environment
alias va="source venv/bin/activate"

# MySQL management
alias sql_start="sudo /etc/init.d/mysql start"
alias sql_stop="sudo /etc/init.d/mysql stop"
alias sql="mysql --user='root' --password=''"

# Miscellaneous
alias rot13="tr 'A-Za-z' 'N-ZA-Mn-za-m'"
alias dunnet="emacs -batch -l dunnet"
EOF
    source "$ALIASES_FILE"
fi

# Pyenv setup for managing Python versions
if command -v pyenv >/dev/null; then
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"

    # Initialize pyenv
    eval "$(pyenv init --path)"
    eval "$(pyenv init -)"

    # Initialize pyenv-virtualenv if available
    if pyenv commands | grep -q virtualenv-init; then
        eval "$(pyenv virtualenv-init -)"
    fi
fi

# GitHub directory setup
dev() {
    TARGET_DIR=~/Documents/GitHub
    if [ ! -d "$TARGET_DIR" ]; then
        echo "$(date): GitHub directory not found. Creating..." >> ~/.shellrc_log
        mkdir -p "$TARGET_DIR"
    fi
    cd "$TARGET_DIR" || echo "$(date): Failed to navigate to $TARGET_DIR" >> ~/.shellrc_log
}

# Python virtual environment helper
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

# Create an archive from a directory
mtar() { tar cvzf "${1%%/}.tar.gz"  "${1%%/}/"; }

# Create a ZIP archive from a file/directory
mzip() { zip -r "${1%%/}.zip" "$1" ; }

# Swap two filenames around
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

# Terminal resizing behavior
if $is_bash; then
    shopt -s checkwinsize
fi

# Enhanced history management
if $is_bash; then
    shopt -s histappend
    export PROMPT_COMMAND="history -a; history -c; history -r; $PROMPT_COMMAND"
elif $is_zsh; then
    setopt APPEND_HISTORY
    setopt INC_APPEND_HISTORY
    setopt SHARE_HISTORY
fi

export HISTFILESIZE=10000
export HISTSIZE=5000
export HISTCONTROL=ignoreboth
export HISTTIMEFORMAT="%F %T "

# Logging
LOGFILE=~/.shellrc_log
echo "$(date): Shell loaded by $SHELL" >> $LOGFILE