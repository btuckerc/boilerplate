#!/usr/bin/env bash
# Update spec-kit configuration to latest version
# Usage: ./update-speckit.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Updating spec-kit configuration for opencode..."
echo ""

# Update specify CLI to latest
echo "Updating specify CLI tool..."
uv tool install specify-cli --force --from git+https://github.com/github/spec-kit.git

echo ""
echo "Regenerating opencode configuration..."
cd "$SCRIPT_DIR"
specify init --here --ai opencode --force

echo ""
echo "Spec-kit configuration updated successfully"
echo ""
echo "Note: Your AGENTS.md customizations have been preserved"
echo ""
echo "To check version:"
echo "  uv tool list | grep specify-cli"
