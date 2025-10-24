#!/usr/bin/env bash
# Fix common mise installation issues

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() {
    echo -e "\n${GREEN}==>${NC} $1"
}

print_error() {
    echo -e "${RED}Error:${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}Warning:${NC} $1"
}

print_info() {
    echo -e "${BLUE}Info:${NC} $1"
}

print_step "Mise Installation Fixer"

# Check if mise is installed
if ! command -v mise &>/dev/null; then
    print_error "mise is not installed. Please install it first:"
    echo "  curl https://mise.run | sh"
    exit 1
fi

# Fix 1: Ensure python symlink exists
print_step "Fixing Python symlink for Ruby builds..."
SHIM_DIR="${HOME}/.local/share/mise/shims"
mkdir -p "$SHIM_DIR"

if command -v python3 &>/dev/null; then
    if [ ! -f "$SHIM_DIR/python" ]; then
        ln -sf "$(command -v python3)" "$SHIM_DIR/python"
        print_info "Created python -> python3 symlink"
    else
        print_info "Python symlink already exists"
    fi
else
    print_warning "python3 not found. Ruby installation may fail."
fi

# Fix 2: Ensure Homebrew dependencies
print_step "Checking Homebrew dependencies..."
if command -v brew &>/dev/null; then
    DEPS=(openssl@3 libyaml gmp)
    MISSING=()
    
    for dep in "${DEPS[@]}"; do
        if ! brew list "$dep" &>/dev/null; then
            MISSING+=("$dep")
        fi
    done
    
    if [ ${#MISSING[@]} -gt 0 ]; then
        print_warning "Missing dependencies: ${MISSING[*]}"
        read -p "Install them now? [Y/n] " -r response
        if [[ ! "${response,,}" =~ ^n ]]; then
            brew install "${MISSING[@]}"
        fi
    else
        print_info "All dependencies installed"
    fi
else
    print_warning "Homebrew not found. Some tools may fail to build."
fi

# Fix 3: Test network connectivity
print_step "Testing network connectivity..."
if ping -c 1 nodejs.org &>/dev/null; then
    print_info "Network connectivity OK"
else
    print_warning "Cannot reach nodejs.org. Check your network/DNS."
    print_info "You may need to:"
    echo "  - Check your internet connection"
    echo "  - Try a different network"
    echo "  - Set DNS servers: networksetup -setdnsservers Wi-Fi 8.8.8.8 1.1.1.1"
fi

# Fix 4: Clear cache if requested
read -p "Clear mise cache? (helps with corrupted downloads) [y/N] " -r response
if [[ "${response,,}" =~ ^y ]]; then
    print_step "Clearing mise cache..."
    rm -rf ~/.cache/mise
    print_info "Cache cleared"
fi

# Fix 5: Suggest installation approach
echo ""
print_step "Recommended installation approach:"
echo "  1. Sequential installation (safer, slower):"
echo "     ${BLUE}MISE_JOBS=1 mise install${NC}"
echo ""
echo "  2. Install core tools first:"
echo "     ${BLUE}mise install python@3.13${NC}"
echo "     ${BLUE}mise install node@lts${NC}"
echo "     ${BLUE}mise install${NC}"
echo ""
echo "  3. Verbose logging for debugging:"
echo "     ${BLUE}MISE_VERBOSE=1 mise install 2>&1 | tee ~/mise-install.log${NC}"
echo ""

read -p "Run sequential installation now? [y/N] " -r response
if [[ "${response,,}" =~ ^y ]]; then
    print_step "Starting sequential installation..."
    export PATH="$SHIM_DIR:$PATH"
    MISE_JOBS=1 mise install
else
    print_info "Run 'mise install' when ready"
fi

print_step "Done!"
