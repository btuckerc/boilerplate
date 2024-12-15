# Environment setup
export PKG_CONFIG_PATH="/usr/local/opt/opencv@4/lib/pkgconfig"
export PATH="/usr/local/opt/llvm/bin:$PATH"
export LDFLAGS="-L/usr/local/opt/llvm/lib"
export CPPFLAGS="-I/usr/local/opt/llvm/include"
export DYLD_LIBRARY_PATH="/usr/local/opt/llvm/lib"

# Python setup
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
export PATH="/usr/local/opt/python@3.13/bin:$PATH"

# Docker path
export PATH="$PATH:/Applications/Docker.app/Contents/Resources/bin/"

# Initialize Homebrew
eval "$(/opt/homebrew/bin/brew shellenv)"

# Load additional configurations if they exist
[ -f "$HOME/.cargo/env" ] && source "$HOME/.cargo/env"
[ -f "$HOME/.deno/env" ] && source "$HOME/.deno/env"
[ -f "$HOME/.secrets" ] && source "$HOME/.secrets" 