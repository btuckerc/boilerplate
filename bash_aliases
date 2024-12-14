# Default aliases

# Colorful and convenient ls
alias ls='ls --color=auto'
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

# Shortcuts for system operations
alias update="sudo apt update && sudo apt upgrade -y"
alias clean="sudo apt autoremove -y && sudo apt autoclean"

# Git shortcuts
alias gst="git status"
alias gpl="git pull"
alias gps="git push"
alias gcm="git commit -m"

# Python environment
alias venv_activate="source venv/bin/activate"

# MySQL management
alias sql_start="sudo /etc/init.d/mysql start"
alias sql_stop="sudo /etc/init.d/mysql stop"
alias sql="mysql --user='root' --password=''"

# Random / etc.
# Add an "alert" alias for long running commands.  Use like so:
#   sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'
alias rot13="tr 'A-Za-z' 'N-ZA-Mn-za-m'"
alias dunnet="emacs -batch -l dunnet"

alias vim="nvim"
alias practice="nvim +VimBeGood"

alias vde="deactivate"
