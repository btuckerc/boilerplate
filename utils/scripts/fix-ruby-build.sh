#!/usr/bin/env bash

set -euo pipefail

echo "Ruby Build Fixer"
echo ""

# Check for problematic LDFLAGS
if [ -n "${LDFLAGS:-}" ]; then
    echo "Found LDFLAGS set to: $LDFLAGS"

    # Check if it points to Intel Mac path
    if [[ "$LDFLAGS" == *"/usr/local/opt/llvm"* ]]; then
        echo "ERROR: LDFLAGS points to Intel Mac path: $LDFLAGS"
        echo ""

        # Search common locations
        SEARCH_PATHS=(
            "$HOME/.zshrc"
            "$HOME/.zshenv"
            "$HOME/.zprofile"
            "$HOME/.bashrc"
            "$HOME/.bash_profile"
            "$HOME/.profile"
            "$HOME/.config/zsh/.zshrc"
            "$HOME/.config/zsh/.zshenv"
            "$HOME/.config/shell/common.sh"
        )

        FOUND=0
        for file in "${SEARCH_PATHS[@]}"; do
            if [ -f "$file" ] && grep -q "LDFLAGS" "$file"; then
                echo "  Found in: $file"
                grep -n "LDFLAGS" "$file"
                FOUND=1
            fi
        done

        if [ $FOUND -eq 0 ]; then
            echo "  Not found in common shell config files."
            echo "  It may be set by:"
            echo "    - Homebrew (check 'brew config')"
            echo "    - A tool's RC file (.rvmrc, .nvmrc, etc.)"
            echo "    - System-wide configs in /etc"
        fi

        echo ""
        echo "SOLUTION:"
        echo "  1. Find and remove/update the LDFLAGS export"
        echo "  2. Or run: unset LDFLAGS && mise install ruby@3"
        echo ""
        read -p "Try installing Ruby with LDFLAGS unset now? [Y/n] " -r
        if [[ ! "${REPLY,,}" =~ ^n ]]; then
            env -u LDFLAGS -u CPPFLAGS mise install ruby@3
        fi
        exit 0
    fi
fi

# Ensure dependencies
echo "Checking Homebrew dependencies..."
DEPS=(openssl@3 libyaml gmp)
MISSING=()

for dep in "${DEPS[@]}"; do
    if ! brew list "$dep" &>/dev/null; then
        MISSING+=("$dep")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo "Missing dependencies: ${MISSING[*]}"
    echo "Installing..."
    brew install "${MISSING[@]}"
else
    echo "All dependencies installed ✓"
fi

# Create python symlink
echo ""
echo "Creating python symlink for Ruby build..."
SHIM_DIR="$HOME/.local/share/mise/shims"
mkdir -p "$SHIM_DIR"

if [ ! -f "$SHIM_DIR/python" ]; then
    ln -sf "$(which python3)" "$SHIM_DIR/python"
    echo "Created: $SHIM_DIR/python -> $(which python3)"
else
    echo "Python symlink already exists ✓"
fi

# Try installing Ruby
echo ""
echo "Attempting to install Ruby..."
export PATH="$SHIM_DIR:$PATH"
env -u LDFLAGS -u CPPFLAGS mise install ruby@3

echo ""
echo "Ruby installation complete!"
