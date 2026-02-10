---
title: Troubleshooting Guide
description: Common error patterns, diagnostics, and solutions
target: AI agents and users
skills: [debug]
type: reference
last_updated: 2025-02-09
---

# Troubleshooting Guide

Quick reference for diagnosing and fixing common issues with this dotfiles repository.

## 1. Diagnostic Commands

### System Health Checks

```bash
# chezmoi health check
chezmoi doctor

# mise health check
mise doctor

# Check current shell
echo $SHELL

# Verify PATH
echo $PATH | tr ':' '\n'

# Check shell config file location
ls -la ~/.bashrc ~/.bash_profile ~/.zshrc ~/.zprofile ~/.zshenv ~/.zlogin 2>/dev/null

# Verify chezmoi source directory
chezmoi source-path

# List chezmoi managed files
chezmoi managed

# Check for unmanaged files in home
chezmoi unmanaged | head -20

# View chezmoi config
cat $(chezmoi source-path)/.chezmoi.toml.tmpl

# Check git status of dotfiles
chezmoi git status

# List recent chezmoi apply history
chezmoi git log --oneline -10
```

### Mise Diagnostics

```bash
# Check mise installation
which mise
mise --version

# Verify mise activation
type mise

# Check all installed tools
mise list

# Check tool versions
mise current

# Test shims
mise exec -- python --version
mise exec -- node --version
mise exec -- ruby --version

# Verify PATH includes mise shims
echo $PATH | grep -o 'mise' | head -1

# Check mise config
cat ~/.config/mise/config.toml

# Test backend availability
mise ls-remote node | head -5
```

### Shell Diagnostics

```bash
# Test shell startup with tracing
zsh -x -c 'exit' 2>&1 | head -50
bash -x -c 'exit' 2>&1 | head -50

# Check for shell syntax errors
zsh -n ~/.zshrc
bash -n ~/.bashrc

# Verify shell is interactive
[[ $- == *i* ]] && echo 'Interactive' || echo 'Not interactive'

# Check login shell status
shopt -q login_shell 2>/dev/null && echo 'Login shell' || echo 'Not login shell'

# List all shell startup files in order
for file in /etc/profile ~/.profile ~/.bash_profile ~/.bash_login ~/.bashrc ~/.zshenv ~/.zprofile ~/.zshrc ~/.zlogin; do
  [[ -f $file ]] && echo "$file exists"
done
```

## 2. Error Index

| Error | Section |
|-------|---------|
| `template: unexpected EOF` | [Template Errors](#chezmoi-template-errors) |
| `template: no template associated with template string` | [Template Errors](#chezmoi-template-errors) |
| `template: <variable>: undefined variable` | [Template Errors](#chezmoi-template-errors) |
| `chezmoi: <file>: permission denied` | [Permission Issues](#chezmoi-permission-issues) |
| `chezmoi: <file>: file exists` | [State Conflicts](#chezmoi-state-conflicts) |
| `pre-apply hook failed` | [Hook Failures](#chezmoi-hook-failures) |
| `post-apply hook failed` | [Hook Failures](#chezmoi-hook-failures) |
| `mise: command not found` | [PATH Issues](#mise-path-not-found) |
| `mise: no version is set for <tool>` | [Version Conflicts](#mise-version-conflicts) |
| `mise: error installing <tool>` | [Installation Failures](#mise-installation-failures) |
| `ruby-build: python not found` | [Ruby Build Issues](#mise-ruby-build-issues) |
| `ubi: failed to download` | [Backend Errors](#mise-backend-errors) |
| `aqua: <tool> not found` | [Backend Errors](#mise-backend-errors) |
| `zsh: command not found: <tool>` | [PATH Problems](#shell-path-problems) |
| `bash: <tool>: command not found` | [PATH Problems](#shell-path-problems) |
| `.zshrc: parse error` | [Shell Not Loading](#shell-not-loading-config) |
| `tmux: unknown key` | [Tmux Issues](#tmux-tpm-issues) |
| `nvim: E5113: Error while calling lua chunk` | [Neovim Plugin Failures](#neovim-plugin-failures) |
| `starship: command not found` | [Starship Prompt Problems](#starship-prompt-problems) |
| `git: merge conflict in .chezmoi` | [Git Merge Conflicts](#git-configuration-errors) |
| `chezmoi: <file>: not in source state` | [State Conflicts](#chezmoi-state-conflicts) |
| `mise: timeout waiting for <tool>` | [Installation Failures](#mise-installation-failures) |

## 3. chezmoi Errors

### Error: `template: unexpected EOF`

**Symptom:** chezmoi apply fails with a template parsing error about unexpected end of file.

**Cause:** Missing closing tags (end, endif, etc.) in template files.

**Fix:**

```bash
# Find the problematic template
chezmoi apply --verbose 2>&1 | grep -A 5 "unexpected EOF"

# Edit the file directly
chezmoi edit ~/.path/to/file

# Check for common missing closures:
# - Missing {{ end }} after if statements
# - Missing {{ end }} after range loops
# - Missing {{ end }} after with blocks
# - Missing closing }} on variable expressions

# Validate template syntax
chezmoi execute-template < $(chezmoi source-path)/dot_file.tmpl

# Re-apply after fixing
chezmoi apply
```

**Verification:**

```bash
chezmoi apply --dry-run
echo $?
```

### Error: `template: <variable>: undefined variable`

**Symptom:** Template references a variable that doesn't exist in the data context.

**Cause:** Variable name typo, or missing data from `.chezmoi.toml.tmpl`.

**Fix:**

```bash
# Check available template data
chezmoi data

# List all template variables
chezmoi data | jq -r 'paths | join(".")'

# Check specific variable
chezmoi data | jq '.chezmoi.os'

# Fix: Add missing variable to .chezmoi.toml.tmpl
chezmoi edit $(chezmoi source-path)/.chezmoi.toml.tmpl

# Or provide a default in template
echo '{{ .MyVar | default "fallback" }}'

# Or check if variable exists first
echo '{{ if hasKey . "MyVar" }}{{ .MyVar }}{{ end }}'
```

**Verification:**

```bash
chezmoi apply --dry-run --verbose 2>&1 | grep -i "template"
```

### Error: `template: wrong number of args for <function>`

**Symptom:** Template function called with incorrect number of arguments.

**Cause:** Sprig or built-in function usage error.

**Fix:**

```bash
# Common fixes for wrong arg count:

# Wrong: {{ contains "foo" }}
# Right: {{ contains "foo" .bar }}

# Wrong: {{ hasKey .MyMap }}
# Right: {{ hasKey .MyMap "key" }}

# Wrong: {{ eq .a .b .c }}
# Right: {{ and (eq .a .b) (eq .b .c) }}

# Test template function
chezmoi execute-template '{{ contains "test" "testing" }}'
```

### Error: `pre-apply hook failed`

**Symptom:** chezmoi apply fails before applying any files.

**Cause:** Hook script has errors, missing dependencies, or wrong permissions.

**Fix:**

```bash
# Find hook location
chezmoi source-path
cd $(chezmoi source-path)
find . -name "*.sh" -path "*/.chezmoiscripts/*"

# Check hook permissions
ls -la $(chezmoi source-path)/.chezmoiscripts/*

# Run hook manually to see error
chezmoi state get-bucket scriptState
bash $(chezmoi source-path)/.chezmoiscripts/run_once_before_*.sh

# Make hook executable if needed
chmod +x $(chezmoi source-path)/.chezmoiscripts/run_*.sh

# Debug with tracing
bash -x $(chezmoi source-path)/.chezmoiscripts/run_once_before_*.sh

# Check for missing commands in hook
head -20 $(chezmoi source-path)/.chezmoiscripts/run_once_before_*.sh | grep -E "(mise|brew|apt)"
```

**Verification:**

```bash
chezmoi apply --debug 2>&1 | grep -A 10 "hook"
```

### Error: `post-apply hook failed`

**Symptom:** Files apply successfully but post-apply hook fails.

**Cause:** Hook depends on files that weren't applied, or tool installation fails.

**Fix:**

```bash
# Run post-apply hook manually
bash $(chezmoi source-path)/.chezmoiscripts/run_onchange_after_*.sh

# Check if mise is available in hook
which mise || echo "mise not in PATH during hook execution"

# Add mise to PATH in hook if missing
export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:$PATH"

# Check for specific tool failures
bash -x $(chezmoi source-path)/.chezmoiscripts/run_onchange_after_*.sh 2>&1 | tail -50
```

### Error: `chezmoi: <file>: permission denied`

**Symptom:** Cannot apply changes due to file permission issues.

**Cause:** File owned by root, or no write permission to directory.

**Fix:**

```bash
# Check file ownership
ls -la ~/.path/to/file

# Check directory permissions
ls -ld $(dirname ~/.path/to/file)

# Fix ownership (macOS/Linux)
sudo chown $USER:$USER ~/.path/to/file

# Fix directory permissions
chmod 755 $(dirname ~/.path/to/file)

# If sudo owned file, apply with sudo
chezmoi apply --verbose 2>&1 | grep "permission denied"

# For sudo-managed files, use chezmoi's sudo support
# Add to .chezmoi.toml.tmpl:
# [sudo]
#   enabled = true
```

**Verification:**

```bash
test -w ~/.path/to/file && echo "Writable" || echo "Not writable"
```

### Error: `chezmoi: <file>: file exists`

**Symptom:** chezmoi won't overwrite existing file that's not managed.

**Cause:** File exists but isn't tracked by chezmoi.

**Fix:**

```bash
# Check if file is managed
chezmoi managed | grep ~/.path/to/file

# Add existing file to chezmoi
chezmoi add ~/.path/to/file

# Or force overwrite (destructive)
chezmoi apply --force

# Or backup and apply
mv ~/.path/to/file ~/.path/to/file.backup.$(date +%Y%m%d)
chezmoi apply

# Check for unmanaged files
chezmoi unmanaged | head -20
```

**Verification:**

```bash
chezmoi managed | grep ~/.path/to/file
chezmoi apply --dry-run
```

### Error: `chezmoi: <file>: not in source state`

**Symptom:** Trying to add or manage a file that chezmoi can't track.

**Cause:** File path outside chezmoi's scope or source state corrupted.

**Fix:**

```bash
# Verify source directory exists
ls -la $(chezmoi source-path)

# Re-add the file explicitly
chezmoi add --exact ~/.path/to/file

# Check if file is in git
chezmoi git ls-files | grep "path/to/file"

# Reset source state for this file
chezmoi forget ~/.path/to/file
chezmoi add ~/.path/to/file
```

### Error: Managed vs unmanaged file conflicts

**Symptom:** File appears in both managed and unmanaged lists, or chezmoi tracks wrong file.

**Cause:** Symlinks, hard links, or path resolution issues.

**Fix:**

```bash
# Check if file is symlink
ls -la ~/.path/to/file

# Find what chezmoi thinks it is managing
chezmoi source-path ~/.path/to/file

# Re-add with exact path
chezmoi forget ~/.path/to/file
chezmoi add --exact ~/.path/to/file

# For symlinked configs, add the target
chezmoi add $(readlink ~/.path/to/file)
```

### Error: `chezmoi: destination already exists and is not a regular file`

**Symptom:** Target is a directory when chezmoi expects a file.

**Cause:** Previously applied directory now should be a file, or vice versa.

**Fix:**

```bash
# Check what exists
ls -la ~/.path/to/target

# Backup and remove directory
mv ~/.path/to/target ~/.path/to/target.backup.$(date +%Y%m%d)

# Re-apply
chezmoi apply ~/.path/to/target
```

### Error: Local override conflicts with chezmoi

**Symptom:** Local edits to managed files causing apply failures.

**Cause:** File modified locally after chezmoi managed it.

**Fix:**

```bash
# See local changes
chezmoi diff ~/.path/to/file

# Apply chezmoi version (loses local changes)
chezmoi apply --force ~/.path/to/file

# Or re-add local changes to source
chezmoi re-add ~/.path/to/file

# See all diffs
chezmoi diff
```

**Verification:**

```bash
chezmoi verify
echo $?
```

## 4. mise Errors

### Error: `mise: command not found`

**Symptom:** mise binary not found after installation.

**Cause:** mise not in PATH, or installation incomplete.

**Fix:**

```bash
# Check common mise locations
ls -la ~/.local/bin/mise
ls -la /usr/local/bin/mise
ls -la /opt/homebrew/bin/mise

# Add to PATH manually
export PATH="$HOME/.local/bin:$PATH"

# Or reinstall mise
curl https://mise.run | sh

# Add mise to shell config if missing
echo 'eval "$(~/.local/bin/mise activate zsh)"' >> ~/.zshrc
```

**Verification:**

```bash
which mise
mise --version
```

### Error: `mise: no version is set for <tool>`

**Symptom:** Tool installed but mise doesn't know which version to use.

**Cause:** Missing `.tool-versions` or `mise.toml` configuration.

**Fix:**

```bash
# Check current versions
mise current

# List installed versions
mise list node

# Set global version
mise use -g node@lts

# Set local version in current directory
mise use node@20

# Pin version in mise.toml
cat ~/.config/mise/config.toml

# Check for .tool-versions file
ls -la ~/.tool-versions
```

**Verification:**

```bash
mise current node
node --version
```

### Error: `mise: error installing <tool>: timeout`

**Symptom:** Tool installation times out, often during download.

**Cause:** Slow network, large download, or backend issues.

**Fix:**

```bash
# Increase timeout
MISE_FETCH_REMOTE_VERSIONS_TIMEOUT=300 mise install

# Or install with retries
for i in 1 2 3; do
  mise install && break
  echo "Retry $i..."
  sleep 5
done

# Install specific tool with verbose output
mise install node@20 --verbose

# Check network connectivity
ping -c 3 github.com
```

### Error: `ubi: failed to download`

**Symptom:** ubi backend fails to download release binary.

**Cause:** GitHub API rate limit, wrong repository name, or release not found.

**Fix:**

```bash
# Check rate limit
curl -s https://api.github.com/rate_limit | jq '.resources.core'

# Set GitHub token to avoid rate limits
export GITHUB_TOKEN=your_token_here

# Check if release exists
curl -s https://api.github.com/repos/owner/repo/releases/latest | jq -r '.tag_name'

# Try installing with aqua backend instead
mise settings set experimental true
# Edit mise.toml to use aqua instead of ubi for specific tool
```

### Error: `aqua: <tool> not found`

**Symptom:** aqua backend can't find tool in registry.

**Cause:** Tool not in aqua-registry, or wrong package name.

**Fix:**

```bash
# Search aqua registry
mise search <tool>

# Check available backends
mise backends

# Force specific backend
mise use node@20 --backend core:node

# Install without aqua
# In mise.toml, set backend = "ubi" or "asdf"
```

### Error: Ruby build fails with `python not found`

**Symptom:** Installing Ruby versions fails because python3 not found.

**Cause:** macOS removed python2, ruby-build needs python for some operations.

**Fix:**

```bash
# macOS: Install python and create symlink
brew install python@3.11

# Create python symlink for ruby-build
sudo ln -s /opt/homebrew/bin/python3 /usr/local/bin/python

# Or set PYTHON environment variable
export PYTHON=/opt/homebrew/bin/python3
mise install ruby@3.2

# Or use system Ruby temporarily
export PATH="/usr/bin:$PATH"
mise install ruby@3.2
```

**Verification:**

```bash
which python
python --version
mise list ruby
```

### Error: `npm: permission denied`

**Symptom:** npm backend fails with permission errors.

**Cause:** npm trying to write to system directories.

**Fix:**

```bash
# Configure npm prefix
npm config set prefix ~/.local/share/npm

# Add npm bin to PATH
export PATH="$HOME/.local/share/npm/bin:$PATH"

# Or use mise to manage npm packages
mise use -g npm:typescript
```

### Error: `go: command not found` when installing go tools

**Symptom:** Go backend fails because go not in PATH.

**Cause:** Go not activated in current shell session.

**Fix:**

```bash
# Ensure go is activated
eval "$(mise activate bash)"

# Or use mise exec
mise exec -- go version

# Install go first, then other tools
mise use -g go@latest
# Then reload shell
exec $SHELL -l
```

### Error: `pipx: not installed`

**Symptom:** pipx backend unavailable.

**Cause:** pipx not installed as a mise tool.

**Fix:**

```bash
# Install pipx first
mise use -g pipx@latest

# Then install pipx packages
mise use -g pipx:black
```

### Error: `gem: not installed`

**Symptom:** Gem backend fails because no Ruby available.

**Cause:** Ruby not installed or activated.

**Fix:**

```bash
# Install Ruby first
mise use -g ruby@3.2

# Then install gems
mise use -g gem:neovim
```

### Error: Version conflict between global and local

**Symptom:** Different versions in different directories, causing confusion.

**Cause:** Local `.tool-versions` or `mise.toml` overrides global.

**Fix:**

```bash
# Check which version is active
mise which node

# Check all version files
ls -la ~/.tool-versions ./.tool-versions ./mise.toml ~/.config/mise/config.toml 2>/dev/null

# Remove local override
rm .tool-versions

# Or trust local version
mise trust ./mise.toml
```

### Error: `mise: shims not found in PATH`

**Symptom:** Tools installed but commands not found.

**Cause:** mise shims directory not in PATH.

**Fix:**

```bash
# Check shims location
ls -la ~/.local/share/mise/shims/

# Add to PATH
echo 'export PATH="$HOME/.local/share/mise/shims:$PATH"' >> ~/.bashrc

# Or use mise activate
eval "$(mise activate bash)"

# Verify shims work
~/.local/share/mise/shims/node --version
```

## 5. Shell Configuration Issues

### Shell Not Loading Config

**Symptom:** Aliases, functions, or PATH changes not available in new shells.

**Cause:** Wrong config file, syntax error, or shell not loading expected file.

**Fix:**

```bash
# Check which config files exist and load order
echo "bash startup order:"
# Login shell: /etc/profile → ~/.bash_profile → ~/.bash_login → ~/.profile
# Interactive: ~/.bashrc

echo "zsh startup order:"
# Login shell: /etc/zshenv → ~/.zshenv → /etc/zprofile → ~/.zprofile → /etc/zshrc → ~/.zshrc → /etc/zlogin → ~/.zlogin

# Test config loading
zsh -l -c 'echo "Login shell loaded"'
bash -l -c 'echo "Login shell loaded"'

# Check for syntax errors
zsh -n ~/.zshrc
bash -n ~/.bashrc

# Debug with trace
zsh -x -c 'source ~/.zshrc' 2>&1 | head -100

# Find where shell stops
for file in ~/.zshenv ~/.zprofile ~/.zshrc ~/.zlogin; do
  if [[ -f $file ]]; then
    echo "Testing $file"
    zsh -c "source $file" 2>&1 | head -5
  fi
done
```

**Verification:**

```bash
# Reload config
source ~/.zshrc

# Test specific alias
alias | grep myalias
```

### PATH Problems

**Symptom:** Commands not found despite being installed, or wrong version used.

**Cause:** PATH order, missing directories, or duplicate entries.

**Fix:**

```bash
# View current PATH
echo $PATH | tr ':' '\n' | nl

# Check for duplicates
echo $PATH | tr ':' '\n' | sort | uniq -d

# Add to PATH (prefer local over system)
export PATH="$HOME/.local/bin:$PATH"

# Add mise shims early
export PATH="$HOME/.local/share/mise/shims:$PATH"

# Remove duplicates
export PATH=$(echo $PATH | tr ':' '\n' | awk '!a[$0]++' | tr '\n' ':')

# Check which binary is used
which -a node
```

**Verification:**

```bash
which node
node --version
```

### Alias Conflicts

**Symptom:** Command behaving unexpectedly, or alias overriding binary.

**Cause:** Alias with same name as system command.

**Fix:**

```bash
# List all aliases
alias

# Check if command is aliased
type ls

# Bypass alias
command ls
\ls

# Remove problematic alias
unalias ls

# Or use full path
/usr/bin/ls
```

### Cross-Shell Compatibility

**Symptom:** Config works in bash but not zsh, or vice versa.

**Cause:** Syntax differences between shells.

**Fix:**

```bash
# bash-specific syntax that breaks zsh:
# ${var:0:1} - substring (zsh uses ${var:1:1} differently)
# [[ $var == pattern ]] - pattern matching differs

# zsh-specific syntax that breaks bash:
# ${(s:/:)var} - parameter expansion
# autoload functions

# Check shell in config
if [[ -n $BASH_VERSION ]]; then
  # bash-specific code
elif [[ -n $ZSH_VERSION ]]; then
  # zsh-specific code
fi

# Or use POSIX syntax
var="${var:-default}"
```

### Debugging Shell Startup

**Symptom:** Shell takes too long to start, or hangs.

**Cause:** Slow commands in startup files.

**Fix:**

```bash
# Time shell startup
time zsh -i -c exit
time bash -i -c exit

# Profile zsh startup
zsh -xv -c exit 2>&1 | ts -i '%.s' | head -100

# Find slow commands in zshrc
for cmd in $(grep -E "^(eval|source|\. " ~/.zshrc | head -20); do
  echo "Timing: $cmd"
  time eval "$cmd" 2>&1 | tail -1
done

# Common slow commands:
# - `brew shellenv` (can be slow)
# - `mise activate` (usually fast)
# - `eval $(thefuck --alias)`
# - Complex prompt builders
```

## 6. Tool-Specific Issues

### Neovim Plugin Failures

**Symptom:** lazy.nvim not loading plugins, or plugins error on startup.

**Cause:** Network issues, plugin conflicts, or missing dependencies.

**Fix:**

```bash
# Clear lazy.nvim cache
rm -rf ~/.local/share/nvim/lazy

# Reinstall plugins
nvim --headless '+Lazy! sync' +qa

# Check for plugin errors
nvim 2>&1 | head -20

# Update lazy.nvim itself
rm -rf ~/.local/share/nvim/lazy/lazy.nvim
git clone --filter=blob:none https://github.com/folke/lazy.nvim.git --branch=stable ~/.local/share/nvim/lazy/lazy.nvim

# Check LSP installation
nvim --headless '+Mason' +qa 2>&1 | head -20

# Reinstall Mason packages
rm -rf ~/.local/share/nvim/mason
nvim --headless '+MasonToolsInstallSync' +qa
```

**Verification:**

```bash
# Check plugins loaded
nvim --headless '+lua print(vim.fn.len(vim.fn.globpath("~/.local/share/nvim/lazy", "*", 0, 1)))' +qa 2>&1
```

### Tmux TPM Issues

**Symptom:** Tmux plugins not loading, TPM not found.

**Cause:** TPM not cloned, or submodule not initialized.

**Fix:**

```bash
# Install TPM
rm -rf ~/.tmux/plugins/tpm
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm

# Reload tmux config
tmux source-file ~/.tmux.conf

# Install plugins manually
# Press prefix + I (capital i) in tmux

# Or from shell
tmux run-shell ~/.tmux/plugins/tpm/bindings/install_plugins

# Check for submodule issues
cd ~/.config/tmux
git submodule update --init --recursive

# Verify plugin installation
ls -la ~/.tmux/plugins/
```

**Verification:**

```bash
tmux list-plugins 2>/dev/null || echo "Check tmux.conf for plugin loading"
```

### Starship Prompt Problems

**Symptom:** Prompt not showing, or showing garbled characters.

**Cause:** Starship not installed, font issues, or shell integration missing.

**Fix:**

```bash
# Check starship installed
which starship
starship --version

# Reinstall if needed
curl -sS https://starship.rs/install.sh | sh

# Check shell integration
grep "starship init" ~/.zshrc ~/.bashrc

# Add manually
echo 'eval "$(starship init zsh)"' >> ~/.zshrc

# Test prompt
starship prompt

# Check font (nerd font required for icons)
echo -e '\ue0b0 \ue0a0 \ue0b2'

# Fix garbled output
echo 'export LANG=en_US.UTF-8' >> ~/.zshrc
echo 'export LC_ALL=en_US.UTF-8' >> ~/.zshrc
```

**Verification:**

```bash
starship prompt --terminal-width=80
```

### Git Configuration Errors

**Symptom:** Git commands fail, or wrong user/email used.

**Cause:** Missing or incorrect git config, or merge conflicts in chezmoi.

**Fix:**

```bash
# Check git config
git config --list --show-origin

# Set user info
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Fix merge conflicts in chezmoi
chezmoi git status
chezmoi git diff

# Resolve conflicts
chezmoi edit <conflicted-file>
# Or
chezmoi git mergetool

# After resolving
chezmoi git add .
chezmoi git commit -m "Resolve merge conflicts"
```

### Terminal Integration

**Symptom:** Colors not working, cursor keys not recognized, or terminal features missing.

**Cause:** Terminal not declaring correct TERM value, or missing terminfo.

**Fix:**

```bash
# Check TERM
echo $TERM

# Set appropriate TERM
export TERM=xterm-256color

# For tmux
export TERM=screen-256color
# or
export TERM=tmux-256color

# Install terminfo for tmux
tic -x ~/.config/tmux/tmux.terminfo 2>/dev/null || true

# Test colors
echo -e '\e[38;5;208mOrange\e[0m'
```

## 7. Platform-Specific Issues

### macOS Issues

**Error: `xcrun: error: invalid active developer path`**

**Cause:** Xcode command line tools not installed or updated.

**Fix:**

```bash
# Install command line tools
xcode-select --install

# Or reset path
sudo xcode-select --reset

# Accept license
sudo xcodebuild -license accept
```

**Error: `brew: command not found` on Apple Silicon**

**Cause:** Homebrew installed in /opt/homebrew but not in PATH.

**Fix:**

```bash
# Add to shell config
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

**Error: Rosetta issues on Apple Silicon**

**Cause:** Some tools need x86_64 architecture.

**Fix:**

```bash
# Install Rosetta
softwareupdate --install-rosetta --agree-to-license

# Run x86 shell
arch -x86_64 zsh

# Install x86 homebrew
arch -x86_64 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Error: `operation not permitted` errors**

**Cause:** macOS security restrictions.

**Fix:**

```bash
# Grant full disk access to terminal
# System Preferences → Security & Privacy → Full Disk Access → Add Terminal

# Or use sudo for protected directories
sudo chezmoi apply
```

### Linux Issues

**Error: Package manager conflicts**

**Fix:**

```bash
# Fix apt locks
sudo rm /var/lib/apt/lists/lock /var/cache/apt/archives/lock /var/lib/dpkg/lock*
sudo dpkg --configure -a

# Update package lists
sudo apt update

# Fix broken packages
sudo apt --fix-broken install
```

**Error: Permission denied on /usr/local**

**Fix:**

```bash
# Change ownership
sudo chown -R $USER:$USER /usr/local

# Or use local install
mkdir -p ~/.local/bin
export PATH="$HOME/.local/bin:$PATH"
```

### Cross-Platform Differences

**Issue: Config paths differ between macOS and Linux**

**Fix:**

```bash
# In templates, use chezmoi.os
{{ if eq .chezmoi.os "darwin" }}
  # macOS specific
{{ else if eq .chezmoi.os "linux" }}
  # Linux specific
{{ end }}

# Common differences to handle:
# - Homebrew prefix: /opt/homebrew vs /usr/local
# - Config paths: ~/Library vs ~/.config
# - Shell paths: /bin/bash vs /usr/bin/bash
```

## 8. Recovery Procedures

### Resetting chezmoi State

**When to use:** Corrupted state, stuck in bad state, or need to start fresh.

```bash
# Backup current state
cp -r $(chezmoi source-path) ~/chezmoi-backup-$(date +%Y%m%d)

# Reset chezmoi state
chezmoi state delete-bucket --bucket=entryState
chezmoi state delete-bucket --bucket=scriptState

# Re-apply everything
chezmoi apply --verbose

# If still broken, remove and re-init
rm -rf $(chezmoi source-path)
chezmoi init <your-repo>
chezmoi apply
```

### Reinstalling From Scratch

**Nuclear option when everything is broken:**

```bash
# 1. Backup important files
mkdir -p ~/dotfiles-backup-$(date +%Y%m%d)
cp ~/.ssh ~/dotfiles-backup-*/ 2>/dev/null || true
cp ~/.gnupg ~/dotfiles-backup-*/ 2>/dev/null || true

# 2. Remove chezmoi
chezmoi destroy
rm -rf $(chezmoi source-path)
rm -rf ~/.config/chezmoi
rm -rf ~/.local/share/chezmoi

# 3. Remove mise tools (optional)
rm -rf ~/.local/share/mise
rm -rf ~/.config/mise

# 4. Reinstall from repo
chezmoi init --apply <your-github-username>/<your-repo>

# 5. Reload shell
exec $SHELL -l
```

### Rollback Strategies

**Quick rollback of recent changes:**

```bash
# See recent changes
chezmoi git log --oneline -10

# Revert specific file
chezmoi git checkout HEAD~1 -- path/to/file
chezmoi apply

# Rollback to previous state
chezmoi git reset --hard HEAD~1
chezmoi apply --force

# Use git tags for known good states
chezmoi git tag working-config
chezmoi git push origin working-config

# Rollback to tag
chezmoi git checkout working-config
chezmoi apply --force
```

### Emergency Fixes

**When you can't open a shell:**

```bash
# Use sh (most basic shell)
sh

# Bypass all configs
bash --noprofile --norc
zsh -f

# Fix broken zshrc
/bin/cat > ~/.zshrc << 'EOF'
export PATH=/usr/bin:/bin:/usr/local/bin:$HOME/.local/bin
EOF

# Emergency chezmoi from live system
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply <your-repo>
```

### When to Use Nuclear Options

**Try standard fixes first:**
1. Run diagnostic commands (Section 1)
2. Check error index (Section 2)
3. Apply specific fix for your error

**Use recovery procedures when:**
- Multiple unrelated errors appearing
- State corruption suspected
- chezmoi doctor shows critical errors
- Shell completely unusable
- Git history is corrupted
- You've spent >30min on incremental fixes

**Before nuclear option:**
- Export/backup SSH keys
- Export/backup GPG keys
- Note currently installed tools/versions
- Check if you have working config on another machine

---

## Quick Reference Card

```bash
# Emergency diagnostics
chezmoi doctor && mise doctor

# Reset and re-apply
chezmoi destroy && chezmoi apply

# Full reset
chezmoi destroy && rm -rf ~/.local/share/chezmoi && chezmoi init --apply <repo>

# Test shell config
zsh -n ~/.zshrc && bash -n ~/.bashrc

# Check tool availability
chezmoi --version && mise --version && which git

# Verify PATH
echo $PATH | grep -E "(mise|local)"
```

---

*Last updated: 2025-02-09*
*For issues not covered here, check: chezmoi.io/docs, mise.jdx.dev, or open an issue in this repository.*
