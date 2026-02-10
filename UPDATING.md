---
title: Update and Maintenance Procedures
description: How to update, upgrade, and maintain this boilerplate
target: AI agents and users
skills: [maintain]
type: guide
last_updated: 2025-02-09
---

# Update and Maintenance Procedures

This guide covers all aspects of keeping your dotfiles system up-to-date, secure, and functioning properly. Follow these procedures to maintain a healthy development environment without breaking your workflow.

---

## 1. Update Philosophy

### When to Update

Updates should be strategic, not reactive. Consider updating in these scenarios:

**Security Updates (Immediate)**
- Critical security patches for tools you use daily (SSH, Git, shell)
- Known CVEs in development tools or language runtimes
- chezmoi or mise security releases

**Feature Updates (Weekly/Monthly)**
- New tool features that improve your workflow
- Performance improvements in frequently-used tools
- Bug fixes that address issues you've encountered

**Routine Maintenance (Monthly/Quarterly)**
- Language runtime updates (Node, Python, Go) after testing
- Neovim plugin updates via lazy.nvim
- Homebrew package refreshes

### Testing Strategy

**Staged Updates for Critical Systems**

Before applying updates to your primary work machine:

```bash
# 1. Test on a VM or secondary machine
chezmoi update --dry-run  # See what would change
chezmoi diff              # Review all changes

# 2. Test specific components
chezmoi apply ~/.zshrc    # Test shell config first
exec zsh                  # Verify shell works
mise upgrade node         # Test Node upgrade
node --version            # Confirm new version works
```

**Safe Update Windows**

- Avoid major updates before deadlines or important presentations
- Schedule major migrations (Node 18→20, Python 3.12→3.13) for low-stress periods
- Keep a working backup before attempting risky updates

### Risk Assessment

Before any update, evaluate:

```
Low Risk (Safe to apply anytime):
├── chezmoi security patches
├── mise bug fixes
├── Shell alias additions
└── New tool installations

Medium Risk (Test first):
├── Language runtime minor updates (3.12.1→3.12.2)
├── Neovim plugin updates
├── mise tool version bumps
└── Homebrew package updates

High Risk (Plan carefully):
├── Language runtime major updates (3.12→3.13)
├── chezmoi template changes
├── Shell configuration restructuring
├── Breaking tool migrations
└── Template variable changes
```

### Backup Procedures

**Pre-Update Backup Checklist**

Always backup before major updates:

```bash
# 1. Backup dotfiles state
tar czf ~/dotfiles-backup-$(date +%Y%m%d-%H%M%S).tar.gz \
  ~/.zshrc ~/.bashrc ~/.gitconfig ~/.config ~/.local/share/chezmoi

# 2. Export current tool versions
mise list > ~/tool-versions-backup-$(date +%Y%m%d).txt

# 3. Export Homebrew state
brew bundle dump --file=~/Brewfile-backup-$(date +%Y%m%d) --force

# 4. Backup Neovim plugins
cp ~/.config/nvim/lazy-lock.json ~/lazy-lock-backup-$(date +%Y%m%d).json
```

**Backup Storage**

- Keep last 5 backups locally: `~/dotfiles-backup-*.tar.gz`
- Push critical backups to cloud storage (iCloud, Dropbox)
- Git commit your local chezmoi changes before updating from remote

### Update Frequency Recommendations

**Daily**: Nothing - the system should be stable

**Weekly**:
- Check `chezmoi status` for pending changes
- Review `mise outdated` output
- Update Neovim plugins: `:Lazy update` inside Neovim

**Monthly**:
- Run `mise upgrade` for tool updates
- `brew update && brew upgrade` for Homebrew packages
- Review and clean unused tools

**Quarterly**:
- Major language runtime reviews (Node LTS, Python releases)
- Audit tool usage with `mise list` - remove unused tools
- Update documentation and this guide
- Verify backup integrity

**Annually**:
- Full system review and cleanup
- Major migrations (deprecated tool replacements)
- Review and update optional tools selection

---

## 2. chezmoi Update Workflow

### Standard Update Procedure

The recommended workflow for updating dotfiles from the remote repository:

```bash
# Step 1: Check current state
chezmoi status
chezmoi diff

# Step 2: Pull and stage updates
chezmoi update

# Step 3: Review what changed
chezmoi diff

# Step 4: Test one file first (recommended)
chezmoi apply ~/.zshrc
source ~/.zshrc
# Verify shell still works, aliases load, no errors

# Step 5: Apply remaining changes
chezmoi apply

# Step 6: Verify everything works
exec zsh  # or exec bash
echo $SHELL
which starship fzf bat  # Verify tools still found
mise doctor            # Verify mise health
```

### Understanding Update Output

**What `chezmoi update` does:**

1. `git pull` in the source directory (`~/.local/share/chezmoi`)
2. Runs `chezmoi apply` to sync changes to target files
3. Executes any `run_after_` hook scripts

**Output interpretation:**

```bash
$ chezmoi update
Already up to date.
# No changes from remote - you're current

$ chezmoi update
Updating dotfiles...
M home/dot_zshrc.tmpl
M home/dot_config/mise/config.toml
# Modified files - review with chezmoi diff
```

### Handling Conflicts

**Scenario 1: Upstream Changes vs Local Modifications**

When the remote repository has updated a file you've also modified locally:

```bash
# Check what's different
chezmoi diff ~/.zshrc

# Option A: Keep your changes (discard upstream)
chezmoi apply --force ~/.zshrc  # Warning: loses upstream changes

# Option B: Accept upstream (lose your changes)
cd $(chezmoi source-path)
git checkout -- home/dot_zshrc.tmpl
chezmoi apply

# Option C: Manual merge (recommended)
cd $(chezmoi source-path)
git stash  # Stash your local changes
chezmoi update
git stash pop  # Re-apply your changes, resolve conflicts manually
chezmoi apply
```

**Scenario 2: Template Variable Changes**

If `.chezmoi.toml.tmpl` adds new required variables:

```bash
# chezmoi will prompt for new values on next apply
chezmoi apply
# You'll see: "What is your Git name? [current value]:"
# Press Enter to keep current, or type new value
```

**Scenario 3: Hook Script Failures**

If a `run_after_` script fails during update:

```bash
# Check which script failed
chezmoi apply --debug 2>&1 | grep -A 5 "run_after"

# Run the script manually to see the error
bash $(chezmoi source-path)/run_once_after_02-setup-packages.sh.tmpl

# Fix the issue, then re-run
chezmoi apply
```

### Using --force Flag (When Safe)

The `--force` flag overwrites target files without prompting. Use only when:

**Safe to use --force:**
- You've reviewed `chezmoi diff` and approve all changes
- You're restoring to a known good state from backup
- You're in a fresh environment (CI/CD, new machine)

**Never use --force when:**
- You have uncommitted local changes you want to keep
- You're not sure what changed in the remote
- You're on a production/critical workstation without backup

```bash
# Example safe usage:
chezmoi diff          # Review changes - all look good
chezmoi apply --force # Apply without individual prompts
```

### Remote Repository Updates

**Updating from GitHub (Main Repository)**

```bash
# Standard update (pull + apply)
chezmoi update

# Pull only, don't apply yet
cd $(chezmoi source-path)
git pull origin main
chezmoi diff  # Review before applying
```

**Forks and Custom Remotes**

If you've forked the boilerplate repository:

```bash
# Check your remotes
cd $(chezmoi source-path)
git remote -v

# Add upstream (original repo) if not present
git remote add upstream https://github.com/btuckerc/boilerplate.git

# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main
chezmoi apply
```

**Branch Management**

```bash
# Work on experimental changes
cd $(chezmoi source-path)
git checkout -b feature/new-tool
chezmoi edit ~/.config/mise/config.toml
# ... make changes ...
chezmoi apply
git add .
git commit -m "Add new development tool"

# Switch back to main
git checkout main
chezmoi apply --force  # Reset to main branch state
```

### Preserving Customizations

**Pattern 1: Local Overrides (Recommended)**

For machine-specific customizations, use `.local` files that aren't tracked:

```bash
# ~/.zshrc.local - loaded at end of main .zshrc
# Add to chezmoi source as executable template that sources .local

# In dot_zshrc.tmpl:
[ -f ~/.zshrc.local ] && source ~/.zshrc.local
```

**Pattern 2: chezmoiignore**

Add to `home/.chezmoiignore`:

```gitignore
# Machine-specific files
.local/share/mise/mise.local.toml
.zshrc.local
```

**Pattern 3: Template Conditionals**

Use Go templates for OS or machine-specific logic:

```go
{{- if eq .chezmoi.hostname "work-laptop" -}}
# Work-specific configuration
export CORPORATE_PROXY=http://proxy.company.com:8080
{{- end -}}
```

---

## 3. mise Tool Updates

### Checking for Updates

**View outdated tools:**

```bash
# List all outdated tools
mise outdated

# Example output:
# Tool    Current   Requested   Latest
# node    20.9.0    20          20.11.0
# python  3.12.1    3.12        3.12.2

# Check specific tool
mise outdated node

# List all installed tools with versions
mise list

# Check tool status
mise status
```

### Update Strategies

**Strategy 1: Upgrade All Tools**

```bash
# Upgrade all tools to their latest allowed versions
mise upgrade

# This upgrades:
# - node 20.9.0 → 20.11.0 (stays on 20.x major version)
# - python 3.12.1 → 3.12.2 (stays on 3.12.x)
# - Tools with "latest" move to newest version
```

**Strategy 2: Upgrade Specific Tool**

```bash
# Upgrade just Node.js
mise upgrade node

# Upgrade with specific version
mise install node@20.11.0
mise use --global node@20.11.0
```

**Strategy 3: Pin to New Version**

Edit `~/.config/mise/config.toml` via chezmoi:

```bash
chezmoi edit ~/.config/mise/config.toml
```

Change version constraints:

```toml
[tools]
# Change from:
node = "lts"
# To specific version:
node = "20.11.0"

# Or change major version:
python = "3.12"
# To:
python = "3.13"
```

Then apply:

```bash
chezmoi apply ~/.config/mise/config.toml
mise install
```

### Handling Breaking Changes

**When Tools Change CLI Arguments**

If a tool update breaks your aliases or scripts:

```bash
# 1. Check tool version
fzf --version

# 2. Check for breaking changes in release notes
curl -s https://api.github.com/repos/junegunn/fzf/releases/latest | grep body

# 3. Update your configuration
chezmoi edit ~/.config/shell/common.sh
# Fix any changed flags or options

# 4. Test
chezmoi apply
source ~/.config/shell/common.sh
```

**When LSP Configs Need Updates**

If Neovim language servers stop working after update:

```bash
# 1. Check LSP status in Neovim
# :LspInfo - shows which servers are running

# 2. Reinstall language servers
mise uninstall "npm:typescript-language-server"
mise install "npm:typescript-language-server"

# 3. Check for LSP configuration updates needed
# Review ~/.config/nvim/lua/plugins/lsp.lua if problems persist
```

**When Neovim Plugins Break**

After mise updates affecting Neovim tools:

```bash
# 1. Open Neovim and check for errors
nvim

# 2. Update plugins
# :Lazy update

# 3. Sync lazy-lock.json back to chezmoi
chezmoi add ~/.config/nvim/lazy-lock.json

# 4. If still broken, restore from backup
cp ~/lazy-lock-backup-*.json ~/.config/nvim/lazy-lock.json
chezmoi apply --force ~/.config/nvim
```

**Testing After Updates**

Create a test checklist:

```bash
# Shell tests
echo $SHELL
which zsh
alias | grep ll  # Check aliases work

# Tool tests
starship --version
fzf --version | head -1
bat --version | head -1

# Language tests
node --version
python --version
go version

# Editor tests
nvim --version | head -1
# Open nvim, verify LSP works, no plugin errors

# Dev workflow tests
git --version
git status  # Should use your aliases
cd /tmp && z  # Test zoxide
```

### Rollback Procedures

**Rolling Back a Single Tool**

```bash
# 1. Find previous version
mise list node
# Output: node 20.11.0 (current), 20.9.0

# 2. Install previous version
mise install node@20.9.0
mise use --global node@20.9.0

# 3. Update config to pin version
chezmoi edit ~/.config/mise/config.toml
# Change: node = "20.11.0" to node = "20.9.0"
chezmoi apply
```

**Complete Rollback**

If multiple updates break your system:

```bash
# 1. Stop and backup current state
tar czf ~/dotfiles-emergency-backup.tar.gz ~/.config ~/.local/share/chezmoi

# 2. Restore from version backup
cat ~/tool-versions-backup-20250201.txt
# Install each tool at backup version:
mise install node@20.9.0
mise install python@3.12.1
mise use --global node@20.9.0 python@3.12.1

# 3. Pin to working versions in config
chezmoi edit ~/.config/mise/config.toml
# Set explicit versions instead of "latest"
chezmoi apply
```

**Emergency Restoration**

For catastrophic failures:

```bash
# 1. Get basic shell working
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
bash --norc --noprofile

# 2. Remove chezmoi state
rm -rf ~/.local/share/chezmoi

# 3. Re-initialize from last known good commit
chezmoi init --apply https://github.com/btuckerc/boilerplate.git

# 4. Restore from dotfiles backup if needed
tar xzf ~/dotfiles-backup-20250201-120000.tar.gz -C ~
```

---

## 4. Brewfile Updates

### Homebrew Maintenance

**Standard Homebrew Workflow**

```bash
# Step 1: Update Homebrew itself
brew update

# Step 2: Check for outdated packages
brew outdated

# Step 3: Upgrade packages
brew upgrade

# Step 4: Clean up old versions
brew cleanup

# Step 5: Verify health
brew doctor
```

**Understanding brew Commands**

- `brew update` - Updates Homebrew's package database (formulae and casks)
- `brew upgrade` - Upgrades installed packages to latest versions
- `brew outdated` - Lists packages with available updates
- `brew cleanup` - Removes old package versions and clears cache
- `brew doctor` - Diagnoses potential issues

### Brewfile Synchronization

**When Brewfile Changes in Repository**

If `home/Brewfile` is updated upstream:

```bash
# 1. Pull updates
chezmoi update

# 2. Review Brewfile changes
chezmoi diff ~/Brewfile

# 3. Apply selectively (review first)
brew bundle --file=~/Brewfile --dry-run

# 4. Install new packages
brew bundle --file=~/Brewfile
```

**Adding New Packages**

To add a new Homebrew package:

```bash
# 1. Edit Brewfile via chezmoi
chezmoi edit ~/Brewfile

# 2. Add your package
# For CLI tools: brew "package-name"
# For apps: cask "app-name"

# 3. Apply changes
chezmoi apply ~/Brewfile
brew bundle --file=~/Brewfile

# 4. Test the new tool
which <new-package>
<new-package> --version
```

**Removing Unused Packages**

```bash
# 1. Remove from Brewfile
chezmoi edit ~/Brewfile
# Delete the line: brew "unused-package"

# 2. Apply Brewfile (removes from chezmoi tracking)
chezmoi apply ~/Brewfile

# 3. Uninstall from system
brew uninstall unused-package

# 4. Or use bundle cleanup (removes all unlisted)
brew bundle cleanup --file=~/Brewfile --force
```

**brew bundle Commands**

```bash
# Install all packages from Brewfile
brew bundle --file=~/Brewfile

# Check what would be installed (dry run)
brew bundle --file=~/Brewfile --dry-run

# Install AND upgrade to latest
brew bundle --file=~/Brewfile --upgrade

# Remove packages not in Brewfile
brew bundle cleanup --file=~/Brewfile

# Force cleanup without confirmation
brew bundle cleanup --file=~/Brewfile --force
```

### Cleanup Procedures

**Safe Cleanup Workflow**

```bash
# 1. Always backup first
cp ~/Brewfile ~/Brewfile-backup-$(date +%Y%m%d)

# 2. See what would be removed
brew bundle cleanup --file=~/Brewfile

# 3. Review carefully - make sure nothing critical is listed

# 4. Perform cleanup
brew bundle cleanup --file=~/Brewfile --force

# 5. Clean Homebrew cache
brew cleanup

# 6. Verify system still works
brew doctor
chezmoi doctor
```

**What's Safe to Clean**

- Old package versions: `brew cleanup`
- Download cache: `brew cleanup --prune=all`
- Unused dependencies: `brew autoremove`

**What to Keep**

- Don't remove packages you actively use
- Be cautious with `brew bundle cleanup --force` - review first
- Keep pinned packages (explicitly version-locked)

**Automated Cleanup Script**

```bash
#!/bin/bash
# ~/.local/bin/brew-cleanup-safe.sh

set -euo pipefail

echo "=== Homebrew Safe Cleanup ==="
echo ""

# Create backup
cp ~/Brewfile ~/Brewfile.backup.$(date +%Y%m%d)

# Show what would be cleaned
echo "Packages to be removed:"
brew bundle cleanup --file=~/Brewfile 2>&1 | grep "would uninstall" || echo "  None"
echo ""

# Ask for confirmation
read -p "Proceed with cleanup? [y/N] " -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    brew bundle cleanup --file=~/Brewfile --force
    brew cleanup
    echo "✓ Cleanup complete"
else
    echo "Cancelled"
fi
```

---

## 5. Configuration Updates

### Updating Dotfiles

**chezmoi Edit Workflow**

Always edit dotfiles through chezmoi to maintain source control:

```bash
# Edit through chezmoi
chezmoi edit ~/.config/shell/common.sh

# Preview changes
chezmoi diff

# Apply to target
chezmoi apply

# Test in new shell
exec zsh
alias | grep <your-new-alias>
```

**Template Modifications**

For `.tmpl` files, verify template syntax:

```bash
# Test template rendering
chezmoi execute-template < $(chezmoi source-path ~/.zshrc)

# With verbose output
chezmoi execute-template --verbose < $(chezmoi source-path ~/.zshrc)

# Check OS detection
chezmoi execute-template --init '{{ .chezmoi.os }} {{ .chezmoi.arch }}'
```

**Testing Before Committing**

```bash
# 1. Edit via chezmoi
chezmoi edit ~/.config/mise/config.toml

# 2. Apply changes
chezmoi apply

# 3. Test the change
mise install  # If new tools added
mise list     # Verify tools installed

# 4. Verify in source
cd $(chezmoi source-path)
git diff

# 5. Commit if satisfied
git add .
git commit -m "Add new development tool"
```

### Adding New Features

**Adding New Aliases**

```bash
# 1. Edit common.sh
chezmoi edit ~/.config/shell/common.sh

# 2. Add your alias in the aliases section:
alias gcm='git commit -m'
alias gs='git status'

# 3. Apply and test
chezmoi apply
source ~/.config/shell/common.sh
gs  # Test new alias

# 4. Commit
cd $(chezmoi source-path)
git add home/dot_config/shell/common.sh
git commit -m "Add git convenience aliases"
```

**Adding New Tools via mise**

```bash
# 1. Identify tool and backend
mise search ripgrep

# 2. Edit config
chezmoi edit ~/.config/mise/config.toml

# 3. Add to [tools] section:
"ubi:BurntSushi/ripgrep" = "latest"

# 4. Apply and install
chezmoi apply
mise install

# 5. Verify
which rg
rg --version

# 6. Commit
cd $(chezmoi source-path)
git add home/dot_config/mise/config.toml
git commit -m "Add ripgrep for fast file searching"
```

**Adding New Configurations**

For new application configs:

```bash
# 1. Create target file manually first
mkdir -p ~/.config/myapp
cat > ~/.config/myapp/config.yaml << 'EOF'
setting: value
EOF

# 2. Add to chezmoi
chezmoi add ~/.config/myapp/config.yaml

# 3. Verify source location
chezmoi source-path ~/.config/myapp/config.yaml
# Output: /path/to/boilerplate/home/dot_config/myapp/config.yaml

# 4. Make OS-specific if needed
cd $(chezmoi source-path)
mv dot_config/myapp/config.yaml dot_config/myapp/config.yaml.tmpl

# 5. Add conditionals
chezmoi edit ~/.config/myapp/config.yaml
# Add: {{- if eq .chezmoi.os "darwin" -}} ... {{- end -}}
```

### Version Control Workflow

**Git Workflow for Dotfiles**

```bash
# Navigate to chezmoi source
cd $(chezmoi source-path)

# Check status
git status

# Stage changes
git add home/dot_config/mise/config.toml
git add home/dot_config/shell/common.sh

# Commit with descriptive message
git commit -m "Add ripgrep and git aliases

- Add ripgrep for fast file searching
- Add gcm and gs git shortcuts
- Tested on macOS Sonoma"

# Push to remote
git push origin main
```

**Commit Message Conventions**

Use clear, descriptive commit messages:

```
Good:
- "Add fzf fuzzy finder integration"
- "Update Python to 3.13, test all LSPs"
- "Fix zsh completion for docker commands"
- "Remove deprecated tool: replaced with modern alternative"

Bad:
- "update"
- "fix stuff"
- "changes"
- "WIP"
```

**Pushing to Remote**

```bash
# Before pushing, verify
chezmoi doctor
mise doctor
exec zsh  # Test in new shell

# Push changes
cd $(chezmoi source-path)
git push origin main

# If you have a fork and want to sync upstream
git fetch upstream
git rebase upstream/main
git push origin main --force-with-lease
```

---

## 6. Migration Guides

### Major Version Migrations

**Node.js LTS Upgrades (e.g., 20→22)**

When upgrading Node.js major versions:

```bash
# 1. Check current version
node --version  # v20.11.0

# 2. Review breaking changes
# Visit: https://nodejs.org/en/blog/release/v22.0.0

# 3. Update mise config
chezmoi edit ~/.config/mise/config.toml
# Change: node = "20" to node = "22"

# 4. Install new version
mise install node@22

# 5. Test critical workflows
npm --version
npm list -g  # Check global packages
# Test your main projects: npm install, npm run build

# 6. Switch globally if tests pass
mise use --global node@22

# 7. Apply and commit
chezmoi apply
git add .
git commit -m "Upgrade Node.js from 20 to 22 LTS"

# 8. Cleanup old version (after a week of stability)
mise uninstall node@20.11.0
```

**Python Version Bumps (e.g., 3.12→3.13)**

```bash
# 1. Backup current environment
pip freeze > ~/requirements-backup-$(date +%Y%m%d).txt

# 2. Update config
chezmoi edit ~/.config/mise/config.toml
# Change: python = "3.12" to python = "3.13"

# 3. Install new Python
mise install python@3.13

# 4. Test pipx tools
pipx list
pipx reinstall-all  # Reinstall tools for new Python

# 5. Test LSP and tools
python --version
pyright --version

# 6. Switch if all tests pass
mise use --global python@3.13
chezmoi apply

# 7. Commit
git add .
git commit -m "Upgrade Python from 3.12 to 3.13"
```

**Go Version Updates**

```bash
# 1. Check current
go version  # go1.22.0

# 2. Update config
chezmoi edit ~/.config/mise/config.toml
# Change: go = "1.22" to go = "1.23"

# 3. Install and test
mise install go@1.23
go version
go env GOPATH

# 4. Test gopls
# Open Go project in Neovim, verify LSP works

# 5. Switch
chezmoi apply
mise use --global go@1.23

# 6. Commit
git add .
git commit -m "Upgrade Go from 1.22 to 1.23"
```

**Neovim Breaking Changes**

When Neovim has major updates:

```bash
# 1. Backup current setup
cp ~/.config/nvim/lazy-lock.json ~/lazy-lock-pre-nvim-update.json

# 2. Update Neovim via mise
mise upgrade neovim

# 3. Check for breaking changes
nvim --version
# Visit: https://neovim.io/doc/user/news.html

# 4. Update plugins
nvim --headless -c 'Lazy! sync' -c 'qa'

# 5. Test LSPs
nvim
# :LspInfo - verify all servers attach
# Test editing files in different languages

# 6. If issues, check plugin configs
# Review ~/.config/nvim/lua/plugins/ for deprecated APIs

# 7. Commit working state
chezmoi add ~/.config/nvim/lazy-lock.json
git add .
git commit -m "Update Neovim and plugins"
```

### Configuration Migrations

**Template Variable Changes**

If `.chezmoi.toml.tmpl` changes required variables:

```bash
# 1. Review the changes
cd $(chezmoi source-path)
git diff home/.chezmoi.toml.tmpl

# 2. Re-initialize with new prompts
chezmoi init --apply
# This will prompt for new variables

# 3. Verify templates work
chezmoi execute-template --init '{{ .new.variable }}'
```

**Hook Script Updates**

When `run_once_` or `run_after_` scripts change:

```bash
# 1. Review script changes
chezmoi diff

# 2. Check if script will re-run
# run_once_ scripts only run if the content changed

# 3. Force re-run if needed
chezmoi state delete-bucket scriptState  # Clears run-once tracking
chezmoi apply  # Scripts will run again

# 4. Monitor output
chezmoi apply --verbose 2>&1 | tee /tmp/chezmoi-run.log
```

**Migrating to New Repository Structure**

If the boilerplate reorganizes files:

```bash
# 1. Pull changes
chezmoi update

# 2. Check for moved files
chezmoi status

# 3. If files were moved, chezmoi handles this automatically
# It will update target locations based on new source structure

# 4. Verify everything still works
chezmoi doctor
chezmoi managed | head -20  # List managed files
```

### Tool Migrations

**Replacing Deprecated Tools**

Example: Replacing an old tool with a modern alternative:

```bash
# 1. Identify replacement
# Old: exa (deprecated) → New: eza

# 2. Update mise config
chezmoi edit ~/.config/mise/config.toml
# Remove: "ubi:ogham/exa" = "latest"
# Add: "ubi:eza-community/eza" = "latest"

# 3. Update aliases if needed
chezmoi edit ~/.config/shell/common.sh
# Change: alias ls='exa --icons'
# To: alias ls='eza --icons'

# 4. Apply changes
chezmoi apply
mise uninstall exa
mise install

# 5. Test
ls  # Should use new tool
which eza

# 6. Commit
git add .
git commit -m "Replace deprecated exa with eza"
```

**Switching Backends (brew to mise)**

If moving a tool from Homebrew to mise:

```bash
# 1. Remove from Brewfile
chezmoi edit ~/Brewfile
# Remove: brew "fzf"

# 2. Add to mise config
chezmoi edit ~/.config/mise/config.toml
# Add: "ubi:junegunn/fzf" = "latest"

# 3. Uninstall from Homebrew
brew uninstall fzf

# 4. Install via mise
chezmoi apply
mise install

# 5. Verify PATH order
which fzf
# Should show: ~/.local/share/mise/installs/fzf/...

# 6. Commit
git add .
git commit -m "Migrate fzf from Homebrew to mise"
```

**Consolidating Tools**

When removing redundant tools:

```bash
# 1. Identify duplicates
# Example: Using both fd and find

# 2. Update aliases to use preferred tool
chezmoi edit ~/.config/shell/common.sh
# Remove: alias find='fd'
# Update any scripts using old tool

# 3. Remove from mise config
chezmoi edit ~/.config/mise/config.toml
# Remove: "ubi:sharkdp/fd" = "latest"

# 4. Apply and cleanup
chezmoi apply
mise uninstall fd

# 5. Commit
git add .
git commit -m "Remove fd, use find for simplicity"
```

---

## 7. Automation Suggestions

### Git Hooks

**Pre-commit Hook**

Create `.git/hooks/pre-commit` in the chezmoi source directory:

```bash
#!/bin/bash
# ~/.local/share/chezmoi/.git/hooks/pre-commit

echo "Running pre-commit checks..."

# Check for template syntax errors
for tmpl in $(git diff --cached --name-only | grep '\.tmpl$'); do
    if ! chezmoi execute-template < "$tmpl" > /dev/null 2>&1; then
        echo "Error: Template syntax error in $tmpl"
        exit 1
    fi
done

# Check for secrets
git diff --cached --name-only | xargs grep -l "api_key\|password\|secret" 2>/dev/null && {
    echo "Warning: Potential secrets detected. Review before committing."
    exit 1
}

echo "Pre-commit checks passed"
```

**Post-merge Hook**

```bash
#!/bin/bash
# ~/.local/share/chezmoi/.git/hooks/post-merge

echo "Dotfiles repository updated from remote"

# Show what changed
CHANGED=$(git diff-tree -r --name-only --no-commit-id HEAD@{1} HEAD)

if echo "$CHANGED" | grep -q "mise/config.toml"; then
    echo "mise configuration changed - run: mise install"
fi

if echo "$CHANGED" | grep -q "Brewfile"; then
    echo "Brewfile changed - run: brew bundle --file=~/Brewfile"
fi

if echo "$CHANGED" | grep -q "nvim/"; then
    echo "Neovim config changed - restart nvim and run :Lazy sync"
fi
```

### Utility Scripts

**Health Check Script**

Create `~/.local/bin/dotfiles-health-check.sh`:

```bash
#!/bin/bash
# Health check for dotfiles system

set -euo pipefail

ERRORS=0

echo "=== Dotfiles Health Check ==="
echo ""

# Check chezmoi
echo -n "chezmoi: "
if chezmoi doctor > /dev/null 2>&1; then
    echo "OK"
else
    echo "FAILED"
    ((ERRORS++))
fi

# Check mise
echo -n "mise: "
if mise doctor > /dev/null 2>&1; then
    echo "OK"
else
    echo "FAILED"
    ((ERRORS++))
fi

# Check critical tools
echo -n "starship: "
command -v starship > /dev/null && echo "OK" || { echo "MISSING"; ((ERRORS++)); }

echo -n "fzf: "
command -v fzf > /dev/null && echo "OK" || { echo "MISSING"; ((ERRORS++)); }

echo -n "zoxide: "
command -v zoxide > /dev/null && echo "OK" || { echo "MISSING"; ((ERRORS++)); }

# Check shell config
echo -n "Shell config: "
if [ -f ~/.config/shell/common.sh ]; then
    echo "OK"
else
    echo "MISSING"
    ((ERRORS++))
fi

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "✓ All checks passed"
    exit 0
else
    echo "✗ $ERRORS check(s) failed"
    exit 1
fi
```

**Update Check Script**

Create `~/.local/bin/check-updates.sh`:

```bash
#!/bin/bash
# Check for available updates

echo "=== Available Updates ==="
echo ""

echo "chezmoi:"
cd $(chezmoi source-path)
git fetch origin > /dev/null 2>&1
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})
if [ $LOCAL != $REMOTE ]; then
    echo "  Updates available - run: chezmoi update"
    git log --oneline $LOCAL..$REMOTE | head -5
else
    echo "  Up to date"
fi
echo ""

echo "mise:"
mise outdated || echo "  All tools up to date"
echo ""

echo "Homebrew:"
brew update > /dev/null 2>&1
brew outdated || echo "  All packages up to date"
echo ""

echo "Neovim plugins:"
nvim --headless -c 'Lazy! check' -c 'qa' 2>&1 | grep -E '(update|outdated)' || echo "  Check manually with :Lazy in nvim"
```

**Update All Script**

Create `~/.local/bin/update-all.sh`:

```bash
#!/bin/bash
# Update everything with safety checks

set -euo pipefail

echo "=== Dotfiles Full Update ==="
echo ""

# Backup first
echo "Creating backup..."
tar czf ~/dotfiles-backup-$(date +%Y%m%d-%H%M%S).tar.gz ~/.config ~/.local/share/chezmoi 2>/dev/null || true
echo "✓ Backup created"
echo ""

# Update chezmoi
echo "Updating dotfiles..."
chezmoi update
echo "✓ Dotfiles updated"
echo ""

# Update mise
echo "Updating mise tools..."
mise upgrade
echo "✓ mise tools updated"
echo ""

# Update Homebrew
echo "Updating Homebrew..."
brew update
brew upgrade
echo "✓ Homebrew updated"
echo ""

# Cleanup
echo "Cleaning up..."
brew cleanup
mise prune
echo "✓ Cleanup complete"
echo ""

# Verify
echo "Running health check..."
~/.local/bin/dotfiles-health-check.sh || true
echo ""

echo "=== Update Complete ==="
echo "Restart your shell: exec zsh"
```

### CI/CD Integration

**GitHub Actions Workflow**

Create `.github/workflows/dotfiles-ci.yml` in your dotfiles repo:

```yaml
name: Dotfiles CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test-macos:
    runs-on: macos-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Install chezmoi
      run: |
        brew install chezmoi
    
    - name: Test chezmoi init
      run: |
        chezmoi init --source=$(pwd)/home --apply --promptString git_name="CI Test" --promptString git_email="ci@test.com"
    
    - name: Verify shell config
      run: |
        test -f ~/.zshrc
        test -f ~/.config/shell/common.sh
    
    - name: Test template syntax
      run: |
        find home -name "*.tmpl" -exec chezmoi execute-template < {} \;

  validate:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Check for secrets
      run: |
        ! grep -r "api_key\|password\|secret" home/ --include="*.toml" --include="*.sh" || exit 1
    
    - name: Validate TOML files
      run: |
        pip install toml
        python -c "import toml; toml.load('home/dot_config/mise/config.toml')"
    
    - name: Check documentation links
      uses: lycheeverse/lychee-action@v1
      with:
        args: --timeout 30 *.md
```

---

## 8. Maintenance Schedule

### Daily

**Nothing** - Your system should be stable for daily work.

### Weekly (Every Monday Morning)

```bash
# 5-minute weekly check

echo "=== Weekly Maintenance ==="

# Check for dotfile updates
cd $(chezmoi source-path)
git fetch origin > /dev/null 2>&1
if [ $(git rev-parse HEAD) != $(git rev-parse @{u}) ]; then
    echo "⚠ Dotfiles updates available"
    git log --oneline HEAD..@{u} | head -3
fi

# Check for tool updates
echo "Checking mise..."
mise outdated | head -5

echo "Checking Homebrew..."
brew update > /dev/null
brew outdated | head -5

echo "Weekly check complete"
```

### Monthly (First Weekend of Month)

```bash
# 30-minute monthly maintenance

echo "=== Monthly Maintenance ==="

# 1. Backup
tar czf ~/dotfiles-monthly-backup-$(date +%Y%m).tar.gz ~/.config ~/.local/share/chezmoi

# 2. Update mise tools
mise upgrade

# 3. Update Homebrew
brew update
brew upgrade
brew cleanup

# 4. Update Neovim plugins
nvim --headless -c 'Lazy! sync' -c 'qa'

# 5. Health check
chezmoi doctor
mise doctor

# 6. Review and clean
echo "Tools installed:"
mise list
echo ""
echo "Consider removing unused tools with: mise uninstall <tool>"

echo "Monthly maintenance complete"
```

### Quarterly (Every 3 Months)

**Major Version Review**

```bash
# Review language runtime major versions
echo "=== Quarterly Review ==="

# Node.js
current_node=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
echo "Node.js: $current_node (Check: https://nodejs.org for latest LTS)"

# Python
current_python=$(python --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python: $current_python (Check: https://python.org for latest)"

# Go
current_go=$(go version | cut -d' ' -f3 | tr -d 'go' | cut -d'.' -f1,2)
echo "Go: $current_go (Check: https://go.dev for latest)"

# Review optional tools
cat ~/.config/mise/config.optional.toml

# Audit unused
echo ""
echo "Review these tools - uninstall if unused:"
mise list | grep -v "latest"
```

**Documentation Updates**

- Review and update this UPDATING.md file
- Update README.md if new features added
- Check for broken links in documentation

**Backup Verification**

```bash
# Test restoring from backup
tar tzf ~/dotfiles-backup-*.tar.gz | head -20
# Ensure files are present and readable
```

### Annually (January)

**Full System Review**

```bash
# Comprehensive yearly maintenance

echo "=== Annual System Review ==="

# 1. Full backup to external/cloud
tar czf ~/Desktop/dotfiles-annual-backup-$(date +%Y).tar.gz \
  ~/.config ~/.local/share/chezmoi ~/.zshrc ~/.bashrc ~/.gitconfig

# 2. Review all tools
echo "=== Tool Inventory ==="
mise list
brew list

# 3. Check for deprecated tools
echo "Review deprecated tools at:"
echo "- https://github.com/ohmyzsh/ohmyzsh/wiki/Plugins"
echo "- https://formulae.brew.sh/analytics/"

# 4. Major migrations if needed
echo "Plan major migrations:"
echo "- Language runtime LTS upgrades"
echo "- Replace deprecated tools"
echo "- Update editor configurations"

# 5. Clean house
brew bundle cleanup --force
mise prune
rm -f ~/.cache/*

# 6. Update all documentation
cd $(chezmoi source-path)
git log --oneline --since="1 year ago" | wc -l
echo "commits this year"

echo "Annual review complete"
```

---

## Quick Reference

### Essential Commands

```bash
# Status and diagnostics
chezmoi doctor          # Full health check
chezmoi status          # Show file status
chezmoi diff            # Preview changes

# Updates
chezmoi update          # Pull and apply from remote
chezmoi apply           # Apply local changes
chezmoi apply --force   # Force apply (overwrite)

# Editing
chezmoi edit FILE       # Edit file through chezmoi
chezmoi add FILE        # Add new file to chezmoi
chezmoi source-path     # Get source location

# mise
chezmoi edit ~/.config/mise/config.toml  # Edit tool config
mise install                           # Install configured tools
mise upgrade                           # Upgrade all tools
mise outdated                          # Check for updates
mise list                              # List installed tools

# Homebrew
chezmoi edit ~/Brewfile               # Edit Brewfile
brew bundle --file=~/Brewfile         # Install from Brewfile
brew update && brew upgrade           # Update packages
brew outdated                          # Check for updates
```

### Emergency Contacts

If everything breaks:

1. **Get basic shell**: `bash --norc --noprofile`
2. **Reset chezmoi**: `rm -rf ~/.local/share/chezmoi && chezmoi init --apply https://github.com/btuckerc/boilerplate.git`
3. **Restore backup**: `tar xzf ~/dotfiles-backup-*.tar.gz -C ~`

---

## Cross-References

- **AGENTS.md** - Detailed maintain skill procedures
- **CHEZMOI.md** - Complete chezmoi reference guide
- **MISE.md** - Comprehensive mise documentation
- **TROUBLESHOOTING.md** - Problem-solving and recovery

---

## Document Information

**Purpose**: Comprehensive update and maintenance procedures
**Target audience**: Users and AI agents maintaining dotfiles
**Maintenance**: Update when adding new tools or changing workflows
**Version control**: Changes tracked in repository

Last updated: 2025-02-09
