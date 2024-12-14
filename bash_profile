parse_git_branch() {
    git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/ (\1)/'
}
#export PS1="\[\033[01;32m\]\u@\h \[\033[01;34m\]\w\[\033[31m\]\`parse_git_branch\`\[\033[00m\] $ "

export PKG_CONFIG_PATH="/usr/local/opt/opencv@4/lib/pkgconfig"
export PATH="/usr/local/opt/llvm/bin:$PATH"
export LDFLAGS="-L/usr/local/opt/llvm/lib"
export CPPFLAGS="-I/usr/local/opt/llvm/include"
export DYLD_LIBRARY_PATH="/usr/local/opt/llvm/lib"

export BASH_SILENCE_DEPRECATION_WARNING=1
eval "$(/opt/homebrew/bin/brew shellenv)"
eval "$(starship init bash)"

alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

alias gs='git status '
alias ga='git add '
alias gb='git branch '
alias gc='git commit'
alias gd='git diff'

if [ -f $(brew --prefix)/etc/bash_completion ]; then
  . $(brew --prefix)/etc/bash_completion
fi

if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi
. "$HOME/.cargo/env"
#export PATH="/opt/homebrew/opt/llvm/bin:$PATH"
export PATH="$PATH:/Applications/Docker.app/Contents/Resources/bin/"
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
export PATH="/usr/local/opt/python@3.13/bin:$PATH"
eval "$(pyenv init --path)"
