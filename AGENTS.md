---
title: AI Agent Operations Manual
description: How to complete tasks in this boilerplate repository
target: AI agents and LLMs
skills: [apply, modify, extend, debug, maintain]
type: playbook
last_updated: 2025-02-09
---

# AI Agent Operations Manual

This document provides operational procedures for AI agents working with the boilerplate dotfiles repository. Use this as your primary reference for all tasks.

---

## Repository Context

**Technologies**: chezmoi (dotfile manager), mise (tool manager), git, Homebrew (macOS), apt/dnf/pacman (Linux)
**Platforms**: macOS (zsh), Linux (bash)
**Source directory**: `/home` (configured via `.chezmoiroot`)
**Config location**: `~/.config/` (XDG-compliant)
**Shared shell config**: `~/.config/shell/common.sh` (sourced by both bash and zsh)

**Key paths**:
- `home/dot_config/` → `~/.config/`
- `home/dot_local/bin/` → `~/.local/bin/`
- `home/dot_gitconfig.tmpl` → `~/.gitconfig`
- `home/dot_zshrc.tmpl` → `~/.zshrc`
- `home/dot_bashrc.tmpl` → `~/.bashrc`
- `home/Brewfile` → Homebrew bundle file

**Template files** (`.tmpl` extension): Processed as Go templates with OS-aware conditionals:
```go
{{- if eq .chezmoi.os "darwin" -}}
# macOS specific
{{- else if eq .chezmoi.os "linux" -}}
# Linux specific
{{- end -}}
```

**Operating modes**:
- **Apply mode**: Apply existing dotfiles to the system
- **Modify mode**: Edit existing configuration through chezmoi
- **Extend mode**: Add new files or tools
- **Debug mode**: Troubleshoot issues
- **Maintain mode**: Update from remote and refresh state

---

## SKILL: Apply Dotfiles

Apply dotfiles to a fresh or existing system. This skill covers initial setup and re-applying changes.

### Prerequisites

Verify these are installed before proceeding:

```bash
# Check chezmoi
chezmoi --version

# Check git
git --version

# Check mise (will be installed during process)
mise --version
```

If chezmoi is missing, install it:
```bash
# macOS
brew install chezmoi

# Linux
curl -fsSL https://chezmoi.io/get | sh
```

### Initial Setup

**One-line install (fresh system)**:
```bash
curl -fsSL https://raw.githubusercontent.com/btuckerc/boilerplate/main/setup | bash
```

**Local repository setup (if already cloned)**:
```bash
cd /path/to/boilerplate
chezmoi init --source="$(pwd)/home" --apply
```

**Expected output**:
```
What is your Git name? [your name]: 
What is your Git email? [your email]: 
Installed chezmoi to ~/.local/bin/chezmoi
Applied dotfiles successfully
```

### Apply Commands

**Apply all changes**:
```bash
chezmoi apply
```

**Apply specific file only**:
```bash
chezmoi apply ~/.zshrc
chezmoi apply ~/.config/shell/common.sh
```

**Force apply (overwrite local changes)**:
```bash
chezmoi apply --force
```

### Preview Changes

**See what would change**:
```bash
chezmoi diff
```

**Diff specific file**:
```bash
chezmoi diff ~/.zshrc
```

**Verbose diff with template output**:
```bash
chezmoi diff --verbose
```

### Verification Steps

After applying, verify the setup:

```bash
# Check shell configuration loaded
source ~/.zshrc  # or ~/.bashrc
echo $SHELL

# Verify tools are available
which chezmoi
which starship
which fzf

# Check mise tools installed
mise list

# Verify shared config loaded
alias | grep ll  # Should show: ll='ls -alF'

# Test git configuration
git config user.name
git config user.email
```

### Decision Tree: Common Failures

```
┌─────────────────────────────────────────────────────────────┐
│ chezmoi apply fails                                         │
└──────────────────┬──────────────────────────────────────────┘
                   │
         ┌─────────▼──────────┐
         │ Error type?        │
         └─────────┬──────────┘
                   │
      ┌────────────┼────────────┐
      ▼            ▼            ▼
 Permission    Template      Tool not
   denied       error        installed
      │            │            │
      ▼            ▼            ▼
 Run with      Check        Run mise
 --force      template       install
              syntax         first
```

**Permission denied**:
```bash
chezmoi apply --force
```

**Template parse error**:
```bash
# Check template syntax
chezmoi execute-template < ~/.local/share/chezmoi/home/dot_zshrc.tmpl
```

**Tools not available**:
```bash
# Install mise tools
mise install

# Verify
chezmoi doctor
```

**Git config missing**:
```bash
# Re-initialize chezmoi to trigger prompts
chezmoi init --promptString git_name="Your Name" --promptString git_email="you@example.com"
```

---

## SKILL: Modify Configuration

Edit existing dotfiles safely through chezmoi. Never edit target files directly.

### Pattern: Edit via chezmoi (Preferred)

Edit through chezmoi to maintain source control:

```bash
# Edit shared shell configuration
chezmoi edit ~/.config/shell/common.sh

# Edit zsh configuration
chezmoi edit ~/.zshrc

# Edit mise configuration
chezmoi edit ~/.config/mise/config.toml

# Edit git configuration
chezmoi edit ~/.gitconfig
```

This opens the file in `$EDITOR`. After editing:

```bash
# Preview changes
chezmoi diff

# Apply changes
chezmoi apply

# Verify
chezmoi managed ~/.config/shell/common.sh  # Should return source path
```

### Pattern: Direct Edit + Add (Recovery)

If you accidentally edited the target file directly:

```bash
# 1. Copy your changes elsewhere (optional)
cp ~/.zshrc ~/.zshrc.backup.manual

# 2. Add the changes back to chezmoi source
chezmoi add ~/.zshrc

# 3. Verify the source was updated
chezmoi source-path ~/.zshrc
# Output: /path/to/boilerplate/home/dot_zshrc.tmpl

# 4. Apply to ensure consistency
chezmoi apply
```

**Warning**: `chezmoi add` overwrites the source with the target. Only use when target has desired changes.

### Testing Workflow

Always follow this workflow for modifications:

```bash
# 1. Edit through chezmoi
chezmoi edit ~/.config/shell/common.sh

# 2. Preview changes
chezmoi diff

# 3. Check for template errors (if .tmpl file)
chezmoi execute-template < $(chezmoi source-path ~/.zshrc)

# 4. Apply changes
chezmoi apply

# 5. Verify in new shell
exec zsh  # or exec bash
alias ll  # Should show updated alias

# 6. Commit changes
cd $(chezmoi source-path)
git add .
git commit -m "Update shell aliases"
```

### Template Modifications

For `.tmpl` files, verify template syntax:

```bash
# Check template rendering without applying
chezmoi execute-template < ~/.local/share/chezmoi/home/dot_zshrc.tmpl

# With verbose output
chezmoi execute-template --verbose < ~/.local/share/chezmoi/home/dot_zshrc.tmpl

# Check specific template function
chezmoi execute-template --init '{{ .chezmoi.os }}'
# Output: darwin or linux
```

### Common Modification Examples

**Add an alias**:
```bash
chezmoi edit ~/.config/shell/common.sh
# Add to aliases section:
alias grep='grep --color=auto'
```

**Modify git configuration**:
```bash
chezmoi edit ~/.gitconfig
# Add:
[alias]
    co = checkout
    br = branch
```

**Update mise tool version**:
```bash
chezmoi edit ~/.config/mise/config.toml
# Change: python = "3.13" to python = "3.12"

# Then apply
mise install
chezmoi apply
```

**Add shell function**:
```bash
chezmoi edit ~/.config/shell/common.sh
# Add to functions section:
myfunction() {
    echo "Hello $1"
}
```

### Decision Tree: Issues

```
┌─────────────────────────────────────────────────────────────┐
│ Changes not appearing after apply                           │
└──────────────────┬──────────────────────────────────────────┘
                   │
         ┌─────────▼──────────┐
         │ Shell reloaded?    │
         └─────────┬──────────┘
                   │
         ┌─────────┴─────────┐
         Yes                 No
         │                   │
         ▼                   ▼
    Check file          Source the
    contents            config file
         │                   │
         ▼                   ▼
    Wrong file?        source ~/.zshrc
         │
         ▼
    Use chezmoi
    source-path
```

**Issue: Edits lost after apply**
Cause: Edited target file instead of source
Fix: `chezmoi add ~/.filename` then edit source properly

**Issue: Template syntax error**
Cause: Invalid Go template syntax
Fix: Check with `chezmoi execute-template`

**Issue: OS-specific code not working**
Cause: Wrong OS detected or conditional syntax error
Fix: Verify with `chezmoi execute-template --init '{{ .chezmoi.os }}'`

---

## SKILL: Extend the System

Add new dotfiles, tools, or hooks to the system.

### Pattern: Add New Dotfile

**Step-by-step for adding a new configuration file**:

```bash
# 1. Create or locate the target file
# Example: ~/.config/myapp/config.ini

# 2. Add to chezmoi
chezmoi add ~/.config/myapp/config.ini

# 3. Verify it was added
chezmoi source-path ~/.config/myapp/config.ini
# Output: /path/to/boilerplate/home/dot_config/myapp/config.ini

# 4. Edit in chezmoi if needed
chezmoi edit ~/.config/myapp/config.ini

# 5. Test apply
chezmoi apply ~/.config/myapp/config.ini
```

**OS-specific example** (add `.tmpl` extension):

```bash
# 1. Add the file
chezmoi add ~/.config/myapp/config

# 2. Rename to add .tmpl extension
cd $(chezmoi source-path)
mv dot_config/myapp/config dot_config/myapp/config.tmpl

# 3. Add OS-specific conditionals
chezmoi edit ~/.config/myapp/config

# 4. Template content example:
{{- if eq .chezmoi.os "darwin" -}}
font_size = 14
path = /Users/{{ .chezmoi.username }}/Documents
{{- else if eq .chezmoi.os "linux" -}}
font_size = 12
path = /home/{{ .chezmoi.username }}/Documents
{{- end -}}
```

**Common locations**:
- Application configs: `home/dot_config/<app>/`
- Local scripts: `home/dot_local/bin/`
- Shell configs: `home/dot_config/shell/`
- Home dotfiles: `home/dot_<filename>`

### Pattern: Add New Tool via mise

**Identify the backend**:

```bash
# Check available backends for a tool
mise search node
# Shows: node, core:node, asdf:...

# Common backends:
# - ubi: Binary releases from GitHub (fastest)
# - aqua: Declarative CLI version manager
# - npm: Node packages
# - pipx: Python packages
# - go: Go packages
# - gem: Ruby gems
```

**Add to mise config**:

```bash
# 1. Edit mise configuration
chezmoi edit ~/.config/mise/config.toml

# 2. Add tool in [tools] section
[tools]
# Add this line:
"ubi:owner/repo" = "latest"      # GitHub binary release
"aqua:owner/repo" = "latest"     # Aqua registry
"npm:package-name" = "latest"    # NPM package
"pipx:package-name" = "latest"   # Python package

# Example additions:
"ubi:cli/cli" = "latest"                    # GitHub CLI
"npm:@anthropic-ai/claude-code" = "latest"  # Claude Code
```

**Test and document**:

```bash
# 1. Install the new tool
mise install

# 2. Verify it's available
which <tool-name>
<tool-name> --version

# 3. Add to chezmoi
mise list  # Note the exact tool name
chezmoi add ~/.config/mise/config.toml

# 4. Update documentation
# Add to relevant section in README.md or skill docs
```

### Pattern: Add Optional Tool

Optional tools use the prompt mechanism via `config.optional.toml`:

```bash
# 1. Edit optional config
chezmoi edit ~/.config/mise/config.optional.toml

# 2. Add tool with description comment
[tools]
# Anthropic CLI tool
# "npm:@anthropic-ai/claude-code" = "latest"

# 3. Save and apply
chezmoi apply

# 4. Test the prompt
mise install
# Should show: "Optional tools: 1) @anthropic-ai/claude-code  Anthropic CLI"
```

**How it works**:
- Tools in `config.optional.toml` are commented out by default
- The preinstall hook reads this file and prompts user
- User selections are saved to `~/.config/mise/mise.local.toml` (gitignored)
- On subsequent runs, only unselected tools are prompted

### Pattern: Add Hook Script

Hook scripts run during chezmoi apply at specific lifecycle points:

**Naming convention**:
- `run_once_before_*.sh.tmpl` - Run once before first apply (prerequisites)
- `run_once_after_*.sh.tmpl` - Run once after first apply (setup)
- `run_after_*.sh.tmpl` - Run after every apply
- `run_before_*.sh.tmpl` - Run before every apply

**Template structure**:

```bash
# File: home/run_once_after_10-setup-myapp.sh.tmpl

{{- if eq .chezmoi.os "darwin" -}}
#!/usr/bin/env bash
# macOS-specific setup
set -euo pipefail

echo "Setting up MyApp for macOS..."
# macOS commands here

{{- else if eq .chezmoi.os "linux" -}}
#!/usr/bin/env bash
# Linux-specific setup
set -euo pipefail

echo "Setting up MyApp for Linux..."
# Linux commands here

{{- end -}}
```

**Placement**:
- Scripts go directly in `home/` directory (not in `dot_config/`)
- Use numeric prefixes for ordering: `01-`, `02-`, etc.
- Template files need `.tmpl` extension for OS conditionals
- Non-template scripts use `executable_` prefix for permissions

**Example workflow**:

```bash
# 1. Create the script file
cat > run_once_after_10-install-myapp.sh.tmpl << 'EOF'
{{- if eq .chezmoi.os "darwin" -}}
#!/usr/bin/env bash
brew install myapp
{{- else if eq .chezmoi.os "linux" -}}
#!/usr/bin/env bash
curl -fsSL https://myapp.dev/install.sh | bash
{{- end -}}
EOF

# 2. Move to chezmoi source
cp run_once_after_10-install-myapp.sh.tmpl $(chezmoi source-path)/

# 3. Add to chezmoi
cd $(chezmoi source-path)
chezmoi add run_once_after_10-install-myapp.sh.tmpl

# 4. Apply
chezmoi apply
```

### Safety Rules

**Auto-approved (no human review needed)**:
- Adding new aliases to `common.sh`
- Adding new tools to mise config (existing backends)
- Adding new dotfiles for existing applications
- Modifying template conditionals (syntax verified)

**Requires confirmation (ask user)**:
- Adding new hook scripts
- Adding tools from unknown/unverified sources
- Modifying package manager commands (brew, apt, etc.)
- Changes to shell initialization order
- Removing existing tools or configurations

**Requires review + approval**:
- Changes to authentication or credential handling
- Network-related configurations (proxies, certificates)
- Security tool configurations (firewall, ssh)
- System-level modifications (sysctl, kernel params)

**Never do**:
- Commit secrets, API keys, or passwords
- Modify system files outside home directory
- Install software from unverified sources
- Bypass security prompts or warnings
- Make changes that break existing workflows without testing

---

## SKILL: Debug Issues

Diagnose and fix problems with dotfiles, tools, or configuration.

### Diagnostic Commands

**chezmoi health check**:
```bash
chezmoi doctor
```
Expected output shows all checks PASS. Note any WARN or FAIL.

**mise health check**:
```bash
mise doctor
```
Shows tool status, environment variables, and potential issues.

**Environment checks**:
```bash
# Check shell
echo $SHELL
echo $0

# Check XDG directories
echo $XDG_CONFIG_HOME  # Should be: $HOME/.config
echo $XDG_DATA_HOME    # Should be: $HOME/.local/share

# Check PATH
echo $PATH | tr ':' '\n'

# Check mise activation
which mise
mise status

# Check chezmoi status
chezmoi status
```

### chezmoi State Inspection

**View chezmoi data**:
```bash
chezmoi data
# Shows: git.name, git.email, chezmoi.os, chezmoi.arch, etc.
```

**Check managed files**:
```bash
# List all managed files
chezmoi managed

# Check if specific file is managed
chezmoi managed ~/.zshrc
# Returns: /path/to/source/dot_zshrc.tmpl

# Check status of all files
chezmoi status
```

**Path inspection**:
```bash
# Get source path for a target file
chezmoi source-path ~/.zshrc
# Output: /path/to/boilerplate/home/dot_zshrc.tmpl

# Get target path for a source file
chezmoi target-path /path/to/boilerplate/home/dot_zshrc.tmpl
# Output: /Users/username/.zshrc
```

### Template Debugging

**Test template rendering**:
```bash
# Basic template execution
chezmoi execute-template --init '{{ .chezmoi.os }}'

# Test with file
chezmoi execute-template < ~/.local/share/chezmoi/home/dot_zshrc.tmpl

# Verbose output
chezmoi execute-template --verbose < ~/.local/share/chezmoi/home/dot_zshrc.tmpl

# Debug mode
chezmoi apply --debug 2>&1 | tee /tmp/chezmoi-debug.log
```

**Common template debugging**:
```bash
# Check OS detection
chezmoi execute-template --init '{{ .chezmoi.os }} {{ .chezmoi.arch }}'

# Check git data
chezmoi execute-template --init '{{ .git.name }} {{ .git.email }}'

# Test conditionals
chezmoi execute-template --init '{{ if eq .chezmoi.os "darwin" }}macOS{{ else }}Linux{{ end }}'
```

### Common Issues and Solutions

**Issue: chezmoi apply template error**

```bash
# Symptom: template: dot_zshrc.tmpl:15: unexpected "}" in command

# Diagnosis
chezmoi execute-template < $(chezmoi source-path ~/.zshrc)

# Common fixes:
# 1. Missing end tag
#    Add: {{- end -}}

# 2. Incorrect syntax
#    Change: {{ if .chezmoi.os == "darwin" }}
#    To: {{ if eq .chezmoi.os "darwin" }}

# 3. Trim whitespace issues
#    Use {{- and -}} to control whitespace
```

**Issue: Tool not found after mise install**

```bash
# Symptom: command not found: starship

# Diagnosis
mise doctor
mise list
which mise

# Solutions:
# 1. Reload shell
source ~/.zshrc

# 2. Check mise activation
echo 'eval "$(mise activate zsh)"' >> ~/.zshrc
chezmoi edit ~/.zshrc  # Or edit properly through chezmoi

# 3. Manual activation for current session
eval "$(mise activate zsh)"

# 4. Verify tool installed
mise list | grep <tool-name>
mise install <tool-name>
```

**Issue: Hook script fails**

```bash
# Symptom: run_once_after_*.sh.tmpl fails during apply

# Diagnosis
chezmoi apply --debug 2>&1 | grep -A 10 "run_once"

# Run script manually to see error
bash $(chezmoi source-path)/run_once_after_02-setup-packages.sh.tmpl

# Solutions:
# 1. Check OS conditional syntax
# 2. Verify all commands exist in the OS
# 3. Add error handling: set -euo pipefail
# 4. Check for missing dependencies
```

**Issue: Changes not appearing**

```bash
# Symptom: Applied changes but not reflected in shell

# Diagnosis
chezmoi diff ~/.zshrc
cat ~/.zshrc | head -20
chezmoi source-path ~/.zshrc

# Solutions:
# 1. Ensure you're editing source, not target
chezmoi edit ~/.zshrc

# 2. Force apply
chezmoi apply --force

# 3. Reload shell completely
exec zsh

# 4. Check for syntax errors in config
chezmoi execute-template < $(chezmoi source-path ~/.zshrc)
```

**Issue: Shell not loading config**

```bash
# Symptom: Aliases and functions not available

# Diagnosis
# Check what shell is running
echo $0

# Check if common.sh is sourced
grep "common.sh" ~/.zshrc

# Check for errors in shell config
zsh -x 2>&1 | head -50  # Verbose mode

# Solutions:
# 1. Source the config manually
source ~/.config/shell/common.sh

# 2. Check shell config order
cat ~/.zshrc | grep -n "source"

# 3. Fix broken sourcing line
chezmoi edit ~/.zshrc
# Ensure: source "$XDG_CONFIG_HOME/shell/common.sh"

# 4. Start fresh shell
exec zsh -l
```

### Decision Tree Flowchart

```
┌──────────────────────────────────────────────────────────────┐
│ Something is not working                                     │
└──────────────────┬───────────────────────────────────────────┘
                   │
         ┌─────────▼─────────────┐
         │ Run diagnostics       │
         │ chezmoi doctor        │
         │ mise doctor           │
         └─────────┬─────────────┘
                   │
         ┌─────────▼─────────────┐
         │ Errors found?         │
         └─────────┬─────────────┘
                   │
      ┌────────────┼─────────────┐
      Yes                        No
      │                          │
      ▼                          ▼
 Fix specific               Check state
 errors                     │
                            ▼
                   ┌─────────▼─────────────┐
                   │ Check chezmoi status  │
                   └─────────┬─────────────┘
                             │
                   ┌──────────┴──────────┐
              Modified            Up to date
                   │                     │
                   ▼                     ▼
              chezmoi diff          Check shell
                   │                     │
                   ▼                     ▼
              Unexpected?         Config loaded?
                   │                     │
           ┌───────┴───────┐      ┌──────┴──────┐
           Yes             No     Yes           No
           │               │      │             │
           ▼               ▼      ▼             ▼
      chezmoi apply   No action  Working   Source config
      --force                           or check PATH
```

### Recovery Procedures

**Nuclear option** (complete reset):

```bash
# 1. Backup current dotfiles
tar czf ~/dotfiles-backup-$(date +%Y%m%d).tar.gz ~/.zshrc ~/.bashrc ~/.config ~/.gitconfig

# 2. Remove chezmoi source directory
rm -rf ~/.local/share/chezmoi

# 3. Re-initialize
chezmoi init --apply https://github.com/btuckerc/boilerplate.git

# 4. Restore from backup if needed
tar xzf ~/dotfiles-backup-*.tar.gz -C ~
```

**Safe rollback**:

```bash
# 1. Check git history in source
cd $(chezmoi source-path)
git log --oneline -10

# 2. Revert to previous commit
git revert HEAD
git revert HEAD~1  # Or specific commit

# 3. Apply reverted state
chezmoi apply --force

# 4. If that fails, reset specific file
chezmoi cat ~/.zshrc > /tmp/zshrc-backup
chezmoi apply --force ~/.zshrc
```

**Emergency shell access**:

```bash
# If shell is broken, use this to get basic functionality
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
export HOME=/Users/$USER  # or /home/$USER
bash --norc --noprofile  # Start clean bash
# or
zsh -f  # Start clean zsh
```

---

## SKILL: Maintain and Update

Keep the dotfiles and tools up to date.

### Update from Remote

**Standard update workflow**:

```bash
# 1. Fetch and apply updates
chezmoi update

# 2. Check for changes
chezmoi diff

# 3. Apply if changes look good
chezmoi apply

# 4. Verify shell config still works
source ~/.zshrc
```

**Update with local changes**:

```bash
# 1. Check status
chezmoi status

# 2. If you have local modifications, handle them first
chezmoi diff

# 3. Option A: Stash local changes
cd $(chezmoi source-path)
git stash

# 4. Option B: Commit your changes first
cd $(chezmoi source-path)
git add .
git commit -m "Local changes before update"

# 5. Now update
chezmoi update

# 6. If conflicts, resolve
cd $(chezmoi source-path)
git status
# Resolve conflicts, then:
git add .
git rebase --continue  # or git merge --continue
```

### Update mise Tools

**Check for outdated tools**:
```bash
mise outdated
```

**Upgrade all tools**:
```bash
mise upgrade
```

**Upgrade specific tool**:
```bash
mise upgrade node
mise install node@latest
```

**Update mise itself**:
```bash
# Via mise
mise self-update

# Via Homebrew (macOS)
brew upgrade mise
```

### Update Brewfile Packages

**Update Homebrew**:
```bash
brew update
```

**Upgrade packages**:
```bash
brew upgrade
```

**Bundle update** (if Brewfile changed):
```bash
brew bundle install --file=~/Brewfile
```

**Check outdated packages**:
```bash
brew outdated
```

### Testing Updates

**Dry-run approach**:

```bash
# 1. Check what would change
chezmoi update --dry-run

# 2. Update but don't apply
chezmoi update
chezmoi diff

# 3. Selective apply - test one file first
chezmoi apply ~/.zshrc
source ~/.zshrc

# 4. If good, apply rest
chezmoi apply
```

**Selective apply**:

```bash
# Apply only specific files after update
chezmoi apply ~/.config/mise/config.toml
mise install

chezmoi apply ~/.config/shell/common.sh
source ~/.config/shell/common.sh
```

### Scheduled Maintenance Commands

**Weekly maintenance**:
```bash
# Update dotfiles
chezmoi update

# Update mise tools
mise upgrade

# Update Brewfile packages
brew update && brew upgrade

# Clean up
brew cleanup
mise prune
```

**Monthly maintenance**:
```bash
# Full system check
chezmoi doctor
mise doctor

# Check for unused tools
mise list  # Review and uninstall if needed

# Update optional tools
# Edit ~/.config/mise/config.optional.toml
chezmoi edit ~/.config/mise/config.optional.toml

# Verify everything works
source ~/.zshrc
which starship fzf bat eza
```

---

## Quick Command Reference

### Status Commands

```bash
chezmoi doctor          # Health check
chezmoi status          # Show file status
chezmoi managed         # List managed files
chezmoi data            # Show template data
mise doctor             # Mise health check
mise list               # List installed tools
mise status             # Show mise status
```

### Apply Commands

```bash
chezmoi apply           # Apply all changes
chezmoi apply FILE      # Apply specific file
chezmoi apply --force   # Force overwrite
chezmoi diff            # Preview changes
chezmoi update          # Pull and apply
```

### Edit Commands

```bash
chezmoi edit FILE       # Edit through chezmoi
chezmoi add FILE        # Add file to chezmoi
chezmoi source-path     # Get source location
chezmoi target-path     # Get target location
```

### Debug Commands

```bash
chezmoi doctor          # Diagnostic info
chezmoi diff            # See changes
chezmoi execute-template # Test templates
chezmoi apply --debug   # Debug mode
mise doctor             # Mise diagnostics
```

### Update Commands

```bash
chezmoi update          # Update from remote
mise upgrade            # Upgrade tools
mise outdated           # Check outdated
brew upgrade            # Upgrade Homebrew
```

---

## Safety Boundaries

### Auto-approved Actions

AI agents can perform without confirmation:
- Apply dotfiles with `chezmoi apply`
- Edit existing dotfiles via `chezmoi edit`
- Preview changes with `chezmoi diff`
- Add new dotfiles for standard applications
- Add tools to mise using known backends (ubi, aqua, npm, pipx, go, gem)
- Run diagnostic commands (doctor, status, list)
- Update from remote with `chezmoi update`
- Modify aliases and functions in `common.sh`

### Requires Confirmation

Ask the user before proceeding:
- Adding new hook scripts (run_once_*, run_after_*)
- Installing tools from unknown sources
- Running scripts that modify system state
- Force apply with `--force` flag
- Adding or removing Brewfile packages
- Changes to git configuration
- Modifying shell initialization files

### Requires Review and Approval

Get explicit user review before committing:
- Changes to security-related configuration
- Modifications to credential handling
- Network configuration changes
- System-level modifications
- Breaking changes to existing workflows
- Removal of existing tools or configurations

### Never Perform

AI agents must never:
- Commit files containing secrets, API keys, or passwords
- Modify system files outside the home directory
- Install software from unverified or untrusted sources
- Bypass security prompts, warnings, or confirmations
- Delete dotfile backups without confirmation
- Run destructive commands without explicit user direction
- Make changes that could lock the user out of their system

---

## Cross-References

**Related documentation**:

- **CHEZMOI.md** - Detailed chezmoi usage guide
  - Advanced template techniques
  - chezmoi configuration options
  - Script execution order

- **MISE.md** - Complete mise reference
  - Backend-specific installation methods
  - Environment variable configuration
  - Hook script development

- **TROUBLESHOOTING.md** - Problem-solving guide
  - Platform-specific issues
  - Known conflicts and solutions
  - Recovery procedures

- **UPDATING.md** - Update procedures
  - Version migration guides
  - Breaking change notices
  - Changelog summaries

- **README.md** - Project overview
  - Feature descriptions
  - Quick start guide
  - Architecture overview

---

## Document Information

**Purpose**: Operational procedures for AI agents managing dotfiles
**Target audience**: AI agents and LLMs
**Maintenance**: Update when adding new patterns or encountering new issues
**Version control**: Changes tracked in repository

For questions or clarifications, refer to the repository README.md or the cross-referenced documentation files listed above.
