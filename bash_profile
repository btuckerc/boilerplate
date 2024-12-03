# ~/.bash_profile

# Function to parse the current Git branch for the prompt
parse_git_branch() {
    git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/ (\1)/'
}

# Set up the environment
export PKG_CONFIG_PATH="/usr/local/opt/opencv@4/lib/pkgconfig"
export PATH="/usr/local/opt/llvm/bin:$PATH"
export LDFLAGS="-L/usr/local/opt/llvm/lib"
export CPPFLAGS="-I/usr/local/opt/llvm/include"
export DYLD_LIBRARY_PATH="/usr/local/opt/llvm/lib"

export BASH_SILENCE_DEPRECATION_WARNING=1
eval "$(/opt/homebrew/bin/brew shellenv)"
eval "$(pyenv init -)"
. "$HOME/.cargo/env"
export PATH="$PATH:/Applications/Docker.app/Contents/Resources/bin/"

# Load Bash completions if available
if [ -f $(brew --prefix)/etc/bash_completion ]; then
    . $(brew --prefix)/etc/bash_completion
fi

# Source ~/.bashrc for interactive shell settings
if [ -f ~/.bashrc ]; then
    . ~/.bashrc
fi

# Prompt configuration
eval "$(starship init bash)"

# Add Git aliases (keep these here for Git-focused environments)
alias gs='git status'
alias ga='git add'
alias gb='git branch'
alias gc='git commit'
alias gd='git diff'