---
title: chezmoi Configuration Management
description: Complete reference for chezmoi templates, hooks, and workflows
target: AI agents and users
skills: [apply, modify, extend, debug]
type: reference
last_updated: 2025-02-09
---

# chezmoi Configuration Management

Complete reference for chezmoi in the boilerplate dotfiles repository. This guide covers template syntax, hook execution, file mappings, and advanced patterns specific to this repository.

---

## 1. chezmoi Architecture

### How chezmoi Works in This Repo

chezmoi manages dotfiles by maintaining a source directory (version-controlled templates) and applying them to target locations in `$HOME`. When you run `chezmoi apply`, it:

1. Reads source files from the repository
2. Processes templates (`.tmpl` files) with variable substitution
3. Executes hook scripts in order
4. Writes final files to target locations
5. Tracks state to avoid redundant operations

### Source Directory Structure

```
boilerplate/
├── home/                          # Source directory (chezmoiroot points here)
│   ├── dot_zshrc.tmpl            # Template → ~/.zshrc
│   ├── dot_bashrc.tmpl           # Template → ~/.bashrc
│   ├── dot_gitconfig.tmpl        # Template → ~/.gitconfig
│   ├── dot_bash_profile.tmpl     # Template → ~/.bash_profile
│   ├── dot_zshenv                # Plain file → ~/.zshenv
│   ├── Brewfile                  # Plain file → ~/Brewfile
│   ├── Brewfile.optional         # Plain file → ~/Brewfile.optional
│   ├── dot_config/               # XDG config directory
│   │   ├── zsh/
│   │   │   ├── dot_zshrc.tmpl    # Template → ~/.config/zsh/.zshrc
│   │   │   └── dot_zprofile.tmpl # Template → ~/.config/zsh/.zprofile
│   │   ├── shell/
│   │   │   └── common.sh         # Plain file → ~/.config/shell/common.sh
│   │   ├── mise/
│   │   │   ├── config.toml       # Plain file → ~/.config/mise/config.toml
│   │   │   └── config.optional.toml
│   │   ├── nvim/                 # Neovim config directory
│   │   ├── tmux/                 # Tmux config directory
│   │   ├── starship/
│   │   ├── yazi/
│   │   ├── kitty/
│   │   ├── ghostty/
│   │   ├── btop/
│   │   └── opencode/
│   ├── run_once_before_01-install-prereqs.sh.tmpl
│   ├── run_once_after_02-setup-packages.sh.tmpl
│   └── run_once_after_03-setup-tools.sh.tmpl
├── .chezmoiroot                  # Points to "home" subdirectory
├── .chezmoiignore               # Global ignore patterns
└── .chezmoi.toml.tmpl           # Configuration template
```

### Target Mapping (dot_* → ~/.)

chezmoi uses a naming convention to map source files to targets:

| Source Pattern | Target Pattern | Example |
|---------------|----------------|---------|
| `dot_<name>` | `.<name>` | `dot_zshrc` → `.zshrc` |
| `dot_<name>.tmpl` | `.<name>` (processed) | `dot_zshrc.tmpl` → `.zshrc` |
| `dot_config/<path>` | `.config/<path>` | `dot_config/nvim/` → `.config/nvim/` |
| `dot_local/<path>` | `.local/<path>` | `dot_local/bin/` → `.local/bin/` |
| `private_<name>` | `<name>` (chmod 600) | `private_ssh_key` → `ssh_key` |
| `executable_<name>` | `<name>` (chmod 755) | `executable_script.sh` → `script.sh` |

### State Management

chezmoi tracks state in `~/.local/share/chezmoi/`:

- **Source state**: The actual files in this repository
- **Target state**: What's currently in your home directory
- **Actual state**: What chezmoi thinks is applied (tracked via hashes)

Key state commands:
```bash
# View current state
chezmoi state dump

# Check for differences
chezmoi diff

# See managed files
chezmoi managed

# View source paths
chezmoi source-path ~/.zshrc
```

### Configuration Files Overview

**`.chezmoiroot`** (root of repo):
```
home
```
Tells chezmoi that source files are in the `home/` subdirectory, not at repository root.

**`.chezmoi.toml.tmpl`** (in `home/`):
Template that generates `~/.config/chezmoi/chezmoi.toml` on first run. Prompts for git name/email and stores them as template data.

**`.chezmoiignore`** (in `home/`):
Patterns for files to exclude from management. See Section 5 for details.

---

## 2. Template Variables Reference

### Core chezmoi Variables

#### `.chezmoi.os`
Operating system identifier.

**Values:**
- `"darwin"` - macOS
- `"linux"` - Linux

**Usage:**
```go
{{- if eq .chezmoi.os "darwin" -}}
# macOS-specific code
{{- else if eq .chezmoi.os "linux" -}}
# Linux-specific code
{{- end -}}
```

#### `.chezmoi.arch`
CPU architecture.

**Values:**
- `"amd64"` - x86_64
- `"arm64"` - Apple Silicon / ARM64

**Usage:**
```go
{{- if eq .chezmoi.arch "arm64" -}}
eval "$(/opt/homebrew/bin/brew shellenv)"
{{- else -}}
eval "$(/usr/local/bin/brew shellenv)"
{{- end -}}
```

#### `.chezmoi.sourceDir`
Absolute path to the source directory.

**Usage:**
```go
sourceDir = {{ .chezmoi.sourceDir | quote }}
```

**Example from `.chezmoi.toml.tmpl`:**
```go
sourceDir = {{ .chezmoi.sourceDir | quote }}
```

#### `.chezmoi.destDir`
Absolute path to the destination directory (usually `$HOME`).

**Usage:**
```go
BREWFILE="{{ .chezmoi.destDir }}/Brewfile"
```

#### `.chezmoi.username`
Current username.

**Usage:**
```go
export PATH="/Users/{{ .chezmoi.username }}/.local/bin:$PATH"
```

#### `.chezmoi.hostname`
Machine hostname.

**Usage:**
```go
{{- if eq .chezmoi.hostname "work-laptop" -}}
# Work-specific configuration
{{- end -}}
```

### Git Configuration Variables

Set via `.chezmoi.toml.tmpl` prompts and stored in `chezmoi.toml`.

#### `.git.name`
Git user name (from prompt).

**Usage:**
```go
[user]
    name = {{ .git.name }}
```

**Example from `dot_gitconfig.tmpl`:**
```gitconfig
[user]
    name = {{ .git.name }}
    email = {{ .git.email }}
```

#### `.git.email`
Git user email (from prompt).

**Usage:**
```go
[user]
    email = {{ .git.email }}
```

### Accessing Template Data

Test what data is available:
```bash
# View all template data
chezmoi data

# Output example:
# {
#   "chezmoi": {
#     "arch": "arm64",
#     "fqdn_hostname": "macbook.local",
#     "group": "staff",
#     "hostname": "macbook",
#     "os": "darwin",
#     "username": "tucker"
#   },
#   "git": {
#     "email": "tucker@example.com",
#     "name": "Tucker"
#   }
# }
```

### Custom Data Variables

Add custom data in `.chezmoi.toml.tmpl`:
```go
{{- $gitName := promptStringOnce . "git_name" "What is your Git name" -}}
{{- $gitEmail := promptStringOnce . "git_email" "What is your Git email" -}}
{{- $workMode := promptBoolOnce . "work_mode" "Is this a work machine" -}}

[data.git]
    name = {{ $gitName | quote }}
    email = {{ $gitEmail | quote }}

[data.machine]
    is_work = {{ $workMode }}
```

Access in templates:
```go
{{- if .machine.is_work -}}
# Work-specific SSH config
{{- end -}}
```

---

## 3. Template Syntax

### Basic Syntax

#### Variable Interpolation
```go
{{ .variable }}
```

Example:
```go
[user]
    name = {{ .git.name }}
```

**Output:**
```gitconfig
[user]
    name = Tucker
```

#### Pipes
Chain functions with `|`:
```go
{{ .chezmoi.sourceDir | quote }}
{{ .git.name | upper }}
{{ .git.email | lower }}
```

### Conditionals

#### If/Else If/Else
```go
{{- if eq .chezmoi.os "darwin" -}}
# macOS
{{- else if eq .chezmoi.os "linux" -}}
# Linux
{{- else -}}
# Other
{{- end -}}
```

**Real example from `dot_bashrc.tmpl`:**
```bash
{{- if eq .chezmoi.os "darwin" }}
# === macOS-specific Configuration ===

# Silence bash deprecation warning (macOS prefers zsh)
export BASH_SILENCE_DEPRECATION_WARNING=1

# Load Homebrew
eval "$(/opt/homebrew/bin/brew shellenv)"
{{- else if eq .chezmoi.os "linux" }}
# === Linux-specific Configuration ===

# Enable color support for ls
alias ls='ls --color=auto'

# Add Ruby gems to PATH
export PATH="$PATH:$HOME/.local/share/gem/ruby/3.4.0/bin"
{{- end }}
```

#### Comparison Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal | `{{ if eq .chezmoi.os "darwin" }}` |
| `ne` | Not equal | `{{ if ne .chezmoi.arch "arm64" }}` |
| `lt` | Less than | `{{ if lt .count 10 }}` |
| `le` | Less than or equal | `{{ if le .version 3 }}` |
| `gt` | Greater than | `{{ if gt .size 1024 }}` |
| `ge` | Greater than or equal | `{{ if ge .cores 8 }}` |

#### Logical Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `and` | Both conditions true | `{{ if and (eq .os "darwin") (eq .arch "arm64") }}` |
| `or` | At least one true | `{{ if or (eq .os "darwin") (eq .os "linux") }}` |
| `not` | Negation | `{{ if not .is_work }}` |

**Combined example:**
```go
{{- if and (eq .chezmoi.os "darwin") (eq .chezmoi.arch "arm64") -}}
# Apple Silicon Mac specific
{{- end -}}
```

### Loops

#### Range
Iterate over slices or maps:
```go
{{- range .items -}}
{{ . }}
{{- end -}}
```

With index:
```go
{{- range $index, $value := .items -}}
{{ $index }}: {{ $value }}
{{- end -}}
```

### Whitespace Control

chezmoi uses Go templates which preserve whitespace by default. Control it with `-`:

| Syntax | Effect |
|--------|--------|
| `{{-` | Trim whitespace before |
| `-}}` | Trim whitespace after |
| `{{- -}}` | Trim both sides |

**Without trimming:**
```go
{{ if eq .chezmoi.os "darwin" }}
macOS
{{ end }}
```
Output includes blank lines.

**With trimming:**
```go
{{- if eq .chezmoi.os "darwin" -}}
macOS
{{- end -}}
```
Output has no extra blank lines.

**Best practice:** Use trimming on all control structures in shell scripts to avoid blank lines:
```bash
{{- if eq .chezmoi.os "darwin" -}}
#!/usr/bin/env bash
# macOS script
{{- else if eq .chezmoi.os "linux" -}}
#!/usr/bin/env bash
# Linux script
{{- end -}}
```

### Built-in Functions

#### String Functions
```go
{{ upper "hello" }}           # HELLO
{{ lower "HELLO" }}           # hello
{{ title "hello world" }}     # Hello World
{{ trim "  hello  " }}         # hello
{{ replace "hello" "l" "L" }} # heLLo
```

#### Environment Variables
```go
{{ env "HOME" }}              # /Users/username
{{ env "SHELL" }}             # /bin/zsh
```

#### Path Functions
```go
{{ joinPath "/home" "user" ".config" }}  # /home/user/.config
{{ lookPath "git" }}          # /usr/bin/git
{{ stat "/etc/passwd" }}      # File info object
```

#### Conditional Functions
```go
{{ hasKey . "git" }}          # true if .git exists
{{ hasPrefix "hello" "he" }}  # true
{{ hasSuffix "hello" "lo" }}  # true
```

#### Mathematical Functions
```go
{{ add 1 2 }}                 # 3
{{ sub 5 3 }}                 # 2
{{ mul 4 5 }}                 # 20
{{ div 10 2 }}                # 5
```

### Template Examples from This Repo

**OS-conditional Homebrew setup:**
```bash
{{- if eq .chezmoi.os "darwin" -}}
#!/usr/bin/env bash
# Install Homebrew and essential tools (macOS)

set -euo pipefail

# Install Homebrew if not present
if ! command -v brew >/dev/null 2>&1; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Set up Homebrew in PATH for Apple Silicon
    if [[ $(uname -m) == "arm64" ]]; then
        echo "Setting up Homebrew for Apple Silicon..."
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        echo "Setting up Homebrew for Intel Mac..."
        eval "$(/usr/local/bin/brew shellenv)"
    fi
fi
```

**Git configuration with variables:**
```gitconfig
[user]
    name = {{ .git.name }}
    email = {{ .git.email }}

[core]
    editor = nvim
    autocrlf = input
```

**OS-specific package manager detection:**
```bash
{{- if eq .chezmoi.os "linux" -}}
if command -v apt >/dev/null 2>&1; then
    echo "Detected apt (Debian/Ubuntu)"
    sudo apt update
    sudo apt install -y curl git build-essential
elif command -v dnf >/dev/null 2>&1; then
    echo "Detected dnf (Fedora/RHEL)"
    sudo dnf install -y curl git gcc gcc-c++
elif command -v pacman >/dev/null 2>&1; then
    echo "Detected pacman (Arch Linux)"
    sudo pacman -Sy --noconfirm curl git base-devel
fi
{{- end -}}
```

---

## 4. Hooks and Scripts

### Hook Execution System

Hook scripts run during `chezmoi apply` at specific lifecycle points. They enable automated setup like installing package managers, tools, or configuring the system.

### Naming Convention

```
run_<when>_<order>_<description>.sh.tmpl
```

#### When
| Value | Runs |
|-------|------|
| `once` | Only on first run (tracked by state) |
| `always` | Every time `chezmoi apply` runs |

#### Order
Numeric prefix controlling execution order:
```
01 - First
02 - Second
03 - Third
...
```

#### Prefixes
| Prefix | Timing |
|--------|--------|
| `before_` | Before applying dotfiles |
| `after_` | After applying dotfiles |

#### Full Pattern Examples
```
run_once_before_01-install-prereqs.sh.tmpl    # Once, before, first
run_once_after_02-setup-packages.sh.tmpl     # Once, after, second
run_once_after_03-setup-tools.sh.tmpl        # Once, after, third
run_always_after_10-update-checks.sh.tmpl    # Always, after, tenth
```

### Current Hooks in This Repo

#### `run_once_before_01-install-prereqs.sh.tmpl`
**Purpose:** Install prerequisites before applying dotfiles
**When:** Once, before apply
**What it does:**
- On macOS: Installs Homebrew, git, eza, btop, mise
- On Linux: Installs build tools via apt/dnf/pacman
- Installs Ruby build dependencies

**Key pattern - OS branching:**
```bash
{{- if eq .chezmoi.os "darwin" -}}
#!/usr/bin/env bash
# macOS-specific setup
brew install git eza btop mise
{{- else if eq .chezmoi.os "linux" -}}
#!/usr/bin/env bash
# Linux-specific setup
if command -v apt >/dev/null 2>&1; then
    sudo apt install -y curl git build-essential
fi
{{- end -}}
```

#### `run_once_after_02-setup-packages.sh.tmpl`
**Purpose:** Install Homebrew packages
**When:** Once, after apply
**What it does:**
- macOS only: Installs packages from Brewfile
- Prompts user for confirmation
- Supports optional package installation

**Key features:**
```bash
if [ -t 0 ]; then
    read -p "Install Homebrew packages now? [Y/n] " -r resp
    if [[ "$resp" =~ ^n ]]; then
        echo "Skipped. Run 'brew-bundle-optional' later."
        exit 0
    fi
fi
```

#### `run_once_after_03-setup-tools.sh.tmpl`
**Purpose:** Install development tools via mise
**When:** Once, after apply
**What it does:**
- Installs mise if not present
- Prompts for confirmation
- Runs `mise install` to install all configured tools

### Adding New Hooks

#### Step 1: Create the script
```bash
cat > run_once_after_10-install-myapp.sh.tmpl << 'EOF'
{{- if eq .chezmoi.os "darwin" -}}
#!/usr/bin/env bash
set -euo pipefail

echo "Installing MyApp for macOS..."
brew install myapp

{{- else if eq .chezmoi.os "linux" -}}
#!/usr/bin/env bash
set -euo pipefail

echo "Installing MyApp for Linux..."
if command -v apt >/dev/null 2>&1; then
    sudo apt install -y myapp
elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y myapp
fi
{{- end -}}
EOF
```

#### Step 2: Move to source directory
```bash
mv run_once_after_10-install-myapp.sh.tmpl $(chezmoi source-path)/
cd $(chezmoi source-path)
chezmoi add run_once_after_10-install-myapp.sh.tmpl
```

#### Step 3: Test the hook
```bash
# Test template rendering
chezmoi execute-template < $(chezmoi source-path)/run_once_after_10-install-myapp.sh.tmpl

# Dry run
chezmoi apply --dry-run

# Apply
chezmoi apply
```

### Hook Best Practices

1. **Always use `set -euo pipefail`** for error handling:
```bash
#!/usr/bin/env bash
set -euo pipefail
```

2. **Check if tools exist before installing:**
```bash
if ! command -v mytool >/dev/null 2>&1; then
    echo "Installing mytool..."
    # install commands
fi
```

3. **Make interactive scripts check for TTY:**
```bash
if [ -t 0 ]; then
    read -p "Continue? [Y/n] " -r resp
else
    echo "Non-interactive mode, skipping prompt"
    exit 0
fi
```

4. **Use OS conditionals for platform-specific code:**
```bash
{{- if eq .chezmoi.os "darwin" -}}
# macOS code
{{- else if eq .chezmoi.os "linux" -}}
# Linux code
{{- end -}}
```

5. **Provide skip messages:**
```bash
if [[ "$resp" =~ ^[nN] ]]; then
    echo "Skipped. Install manually later."
    exit 0
fi
```

---

## 5. Configuration Files

### `.chezmoi.toml.tmpl`

**Location:** `home/.chezmoi.toml.tmpl`
**Target:** `~/.config/chezmoi/chezmoi.toml`
**Purpose:** Template that generates chezmoi's own configuration on first run

**Current content:**
```go
{{- $gitName := promptStringOnce . "git_name" "What is your Git name" -}}
{{- $gitEmail := promptStringOnce . "git_email" "What is your Git email" -}}

sourceDir = {{ .chezmoi.sourceDir | quote }}

[data.git]
    name = {{ $gitName | quote }}
    email = {{ $gitEmail | quote }}
```

**How it works:**
1. On first `chezmoi init`, prompts user for git name and email
2. Stores values in `~/.config/chezmoi/chezmoi.toml`
3. Values become available as `.git.name` and `.git.email` in templates
4. Subsequent runs use cached values (no re-prompting)

**Extending with new prompts:**
```go
{{- $gitName := promptStringOnce . "git_name" "What is your Git name" -}}
{{- $gitEmail := promptStringOnce . "git_email" "What is your Git email" -}}
{{- $workMachine := promptBoolOnce . "work_machine" "Is this a work machine" -}}
{{- $editor := promptStringOnce . "editor" "Preferred editor" "nvim" -}}

sourceDir = {{ .chezmoi.sourceDir | quote }}

[data.git]
    name = {{ $gitName | quote }}
    email = {{ $gitEmail | quote }}

[data.machine]
    is_work = {{ $workMachine }}
    editor = {{ $editor | quote }}
```

**Prompt types:**
- `promptStringOnce` - Text input
- `promptBoolOnce` - Yes/no (true/false)
- `promptIntOnce` - Integer input
- `promptString` - Text input (always prompts)

### `.chezmoiroot`

**Location:** Repository root
**Content:**
```
home
```

**Purpose:** Points chezmoi to the source directory. Without this, chezmoi would look for dotfiles at repository root.

**To change:**
```bash
# Edit the file
echo "dotfiles" > .chezmoiroot

# Move existing files
mkdir -p dotfiles
git mv home/* dotfiles/
```

### `.chezmoiignore`

**Location:** `home/.chezmoiignore`
**Purpose:** Patterns for files chezmoi should ignore

**Current patterns:**
```gitignore
# Documentation and non-dotfile content
README.md
LICENSE
*.md

# Binary and media files
*.pdf
*.png
*.jpg
*.jpeg
*.gif

# Backup files
*.bak
*backup*
*.backup.*

# macOS system files
.DS_Store
.AppleDouble
.LSOverride

# Backup directories from nvim
nvim.backup.*

# Temporary files
*.tmp
*.temp
*~

# Local mise configuration (machine-specific)
.config/mise/mise.local.toml

# OpenCode runtime files
.config/opencode/.opencode-speckit/
.config/opencode/node_modules/
.config/opencode/bun.lock

# Neovim lazy-lock.json (plugin lockfile)
.config/nvim/lazy-lock.json
```

**Pattern syntax:**
- `*.md` - Ignore all markdown files
- `README.md` - Ignore specific file
- `.DS_Store` - Ignore by name
- `.config/mise/mise.local.toml` - Ignore specific path
- `dir/**` - Ignore directory contents

**Adding new ignores:**
```bash
chezmoi edit ~/.chezmoiignore
# Add patterns
chezmoi apply
```

### `.chezmoiexternal.toml`

**Location:** Can be in source directory
**Purpose:** Define external resources to fetch (URLs, archives, git repos)

**Example structure:**
```toml
[".local/share/nvim/site/pack/packer/start/packer.nvim"]
    type = "git-repo"
    url = "https://github.com/wbthomason/packer.nvim"
    refreshPeriod = "168h"

[".local/bin/lsd"]
    type = "archive"
    url = "https://github.com/lsd-rs/lsd/releases/latest/download/lsd-{{ .chezmoi.arch }}-apple-darwin.tar.gz"
    executable = "lsd-{{ .chezmoi.arch }}-apple-darwin/lsd"
```

**Usage in this repo:**
External resources are managed manually rather than through `.chezmoiexternal.toml` to have more control over versions and installation timing.

---

## 6. File Mappings

### Source to Target Reference Table

| Source | Target | Template? | Description |
|--------|--------|-----------|-------------|
| `home/dot_zshenv` | `~/.zshenv` | No | Zsh environment (simple) |
| `home/dot_bash_profile.tmpl` | `~/.bash_profile` | Yes | Bash login config |
| `home/dot_bashrc.tmpl` | `~/.bashrc` | Yes | Bash interactive config |
| `home/dot_gitconfig.tmpl` | `~/.gitconfig` | Yes | Git configuration |
| `home/Brewfile` | `~/Brewfile` | No | Homebrew packages |
| `home/Brewfile.optional` | `~/Brewfile.optional` | No | Optional Homebrew packages |
| `home/dot_config/zsh/dot_zshrc.tmpl` | `~/.config/zsh/.zshrc` | Yes | Zsh config |
| `home/dot_config/zsh/dot_zprofile.tmpl` | `~/.config/zsh/.zprofile` | Yes | Zsh profile |
| `home/dot_config/shell/common.sh` | `~/.config/shell/common.sh` | No | Shared shell functions |
| `home/dot_config/mise/config.toml` | `~/.config/mise/config.toml` | No | Mise tools config |
| `home/dot_config/mise/config.optional.toml` | `~/.config/mise/config.optional.toml` | No | Optional tools |
| `home/dot_config/nvim/` | `~/.config/nvim/` | No | Neovim configuration |
| `home/dot_config/tmux/tmux.conf` | `~/.config/tmux/tmux.conf` | No | Tmux configuration |
| `home/dot_config/starship/starship.toml` | `~/.config/starship/starship.toml` | No | Starship prompt config |
| `home/dot_config/yazi/` | `~/.config/yazi/` | No | Yazi file manager |
| `home/dot_config/kitty/` | `~/.config/kitty/` | No | Kitty terminal |
| `home/dot_config/ghostty/config` | `~/.config/ghostty/config` | No | Ghostty terminal |
| `home/dot_config/btop/btop.conf` | `~/.config/btop/btop.conf` | No | Btop system monitor |
| `home/dot_config/opencode/` | `~/.config/opencode/` | Yes (some) | OpenCode configuration |

### Adding New Mappings

#### Plain file (no template processing):
```bash
# 1. Create or locate the target file
touch ~/.config/myapp/config.ini

# 2. Add to chezmoi
chezmoi add ~/.config/myapp/config.ini

# 3. Verify
chezmoi source-path ~/.config/myapp/config.ini
# Output: /path/to/boilerplate/home/dot_config/myapp/config.ini
```

#### Template file (needs .tmpl extension):
```bash
# 1. Create target file with template content
cat > ~/.myconfig << 'EOF'
user = {{ .git.name }}
host = {{ .chezmoi.hostname }}
EOF

# 2. Add to chezmoi
chezmoi add ~/.myconfig

# 3. Rename to add .tmpl extension
cd $(chezmoi source-path)
mv dot_myconfig dot_myconfig.tmpl

# 4. Verify template works
chezmoi execute-template < dot_myconfig.tmpl
```

#### Directory with contents:
```bash
# 1. Ensure directory exists
mkdir -p ~/.config/myapp

# 2. Add entire directory
chezmoi add ~/.config/myapp

# 3. Verify
chezmoi source-path ~/.config/myapp
# Output: /path/to/boilerplate/home/dot_config/myapp
```

### Checking Current Mappings

```bash
# List all managed files
chezmoi managed

# Get source path for target
chezmoi source-path ~/.zshrc

# Get target path for source
chezmoi target-path home/dot_zshrc.tmpl

# Check if file is managed
chezmoi managed ~/.zshrc && echo "Managed" || echo "Not managed"
```

---

## 7. Testing and Validation

### Health Checks

#### chezmoi doctor
Comprehensive system check:
```bash
chezmoi doctor
```

**Expected output:**
```
RESULT    CHECK                MESSAGE
ok        version              v2.x.x, commit ..., date ...
ok        os-arch              darwin/arm64
ok        go-version           go1.21.x
ok        executable           /opt/homebrew/bin/chezmoi
ok        upgrade-method       brew
ok        config-file          ~/.config/chezmoi/chezmoi.toml
ok        source-dir           ~/Documents/GitHub/boilerplate/home
ok        suspicious-entries   no suspicious entries
ok        working-tree         ~/Documents/GitHub/boilerplate
ok        dest-dir             ~
ok        shell-command        /bin/zsh
ok        shell-args           -l
ok        cd-command           builtin cd
ok        cd-args              
ok        edit-command         $EDITOR
ok        edit-args            
ok        git-command          /opt/homebrew/bin/git
ok        merge-command        vimdiff
ok        age-command          age not found
ok        gpg-command          gpg not found in $PATH
ok        1password-command    op not found in $PATH
ok        bitwarden-command    bw not found in $PATH
ok        gopass-command       gopass not found in $PATH
ok        keepassxc-command    keepassxc-cli not found in $PATH
ok        keepassxc-db         not set
ok        lastpass-command     lpass not found in $PATH
ok        pass-command         pass not found in $PATH
ok        vault-command        vault not found in $PATH
ok        secret-command       not set
```

#### chezmoi status
Check which files have changes:
```bash
chezmoi status
```

**Status codes:**
- `A` - Added (new file)
- `D` - Deleted
- `M` - Modified
- ` ` - Unchanged

**Example:**
```
M  .zshrc                    # Modified in target
 M .config/nvim/init.lua     # Modified in source
MM .bashrc                   # Modified in both
```

### Preview Commands

#### chezmoi diff
See what would change without applying:
```bash
# All files
chezmoi diff

# Specific file
chezmoi diff ~/.zshrc

# Verbose (shows template output)
chezmoi diff --verbose
```

**Example output:**
```diff
diff --git a/.zshrc b/.zshrc
index abc123..def456 100644
--- a/.zshrc
+++ b/.zshrc
@@ -10,6 +10,9 @@
 # Load Starship prompt
 eval "$(starship init zsh)"
 
+# New alias
+alias ll='ls -alF'
+
 # === Zsh Modules ===
```

#### chezmoi apply --dry-run
Simulate apply without making changes:
```bash
chezmoi apply --dry-run
chezmoi apply --dry-run ~/.zshrc
```

### Template Testing

#### chezmoi execute-template
Test template syntax without applying:
```bash
# Test basic variable
chezmoi execute-template --init '{{ .chezmoi.os }}'

# Test conditional
chezmoi execute-template --init '{{ if eq .chezmoi.os "darwin" }}macOS{{ else }}Linux{{ end }}'

# Test with file
chezmoi execute-template < home/dot_zshrc.tmpl

# Test specific template
chezmoi execute-template --init '{{ .git.name }}'
# Output: Tucker
```

#### Verbose template execution
```bash
# See template processing step by step
chezmoi execute-template --verbose < home/dot_gitconfig.tmpl
```

#### Debug mode
```bash
# Full debug output
chezmoi apply --debug 2>&1 | tee /tmp/chezmoi-debug.log

# Debug specific file
chezmoi apply --debug ~/.zshrc 2>&1 | less
```

### Common Template Mistakes

#### Missing end tag
**Wrong:**
```go
{{ if eq .chezmoi.os "darwin" }}
# macOS code
```

**Right:**
```go
{{ if eq .chezmoi.os "darwin" }}
# macOS code
{{ end }}
```

#### Wrong comparison syntax
**Wrong:**
```go
{{ if .chezmoi.os == "darwin" }}
```

**Right:**
```go
{{ if eq .chezmoi.os "darwin" }}
```

#### Extra whitespace
**Problem:** Template leaves blank lines in output
```go
{{ if eq .chezmoi.os "darwin" }}
# macOS
{{ end }}
```

**Solution:** Use dash trimming
```go
{{- if eq .chezmoi.os "darwin" -}}
# macOS
{{- end -}}
```

#### Undefined variable
**Error:** `map has no entry for key "work_mode"`

**Fix:** Check `.chezmoi.toml.tmpl` defines the variable, or add default:
```go
{{ .work_mode | default false }}
```

### Validation Workflow

Before committing template changes:

```bash
# 1. Check template syntax
chezmoi execute-template < $(chezmoi source-path ~/.zshrc)

# 2. Check health
chezmoi doctor

# 3. Preview changes
chezmoi diff

# 4. Dry run
chezmoi apply --dry-run

# 5. Apply to test
chezmoi apply ~/.zshrc

# 6. Verify in new shell
exec zsh
```

---

## 8. Advanced Patterns

### External Resources

While this repo doesn't use `.chezmoiexternal.toml`, you can fetch remote resources:

**Example `.chezmoiexternal.toml`:**
```toml
# Download binary from GitHub releases
[".local/bin/lsd"]
    type = "archive-file"
    url = "https://github.com/lsd-rs/lsd/releases/download/v1.0.0/lsd-v1.0.0-{{ .chezmoi.arch }}-apple-darwin.tar.gz"
    path = "lsd"
    executable = true

# Clone git repository
[".config/nvim/pack/packer/start/packer.nvim"]
    type = "git-repo"
    url = "https://github.com/wbthomason/packer.nvim"
    refreshPeriod = "168h"  # Refresh weekly

# Download single file
[".local/bin/my-script"]
    type = "file"
    url = "https://example.com/my-script.sh"
    executable = true
```

**Manual alternative (used in this repo):**
Hook scripts download and install external resources with more control:
```bash
# In run_once_after_*.sh.tmpl
curl -fsSL https://example.com/install.sh | bash
```

### OS-Specific Blocks

**Basic OS detection:**
```bash
{{- if eq .chezmoi.os "darwin" -}}
#!/usr/bin/env bash
# macOS-specific code
echo "Running on macOS"
{{- else if eq .chezmoi.os "linux" -}}
#!/usr/bin/env bash
# Linux-specific code  
echo "Running on Linux"
{{- end -}}
```

**Architecture-specific:**
```bash
{{- if eq .chezmoi.arch "arm64" -}}
# Apple Silicon / ARM64
HOMEBREW_PREFIX="/opt/homebrew"
{{- else -}}
# Intel / x86_64
HOMEBREW_PREFIX="/usr/local"
{{- end -}}
eval "$(${HOMEBREW_PREFIX}/bin/brew shellenv)"
```

**Combined OS and architecture:**
```bash
{{- if and (eq .chezmoi.os "darwin") (eq .chezmoi.arch "arm64") -}}
# macOS on Apple Silicon
{{- else if and (eq .chezmoi.os "darwin") (eq .chezmoi.arch "amd64") -}}
# macOS on Intel
{{- else if eq .chezmoi.os "linux" -}}
# Any Linux
{{- end -}}
```

**Package manager detection (Linux):**
```bash
{{- if eq .chezmoi.os "linux" -}}
if command -v apt >/dev/null 2>&1; then
    sudo apt install -y package
elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y package
elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -Sy --noconfirm package
fi
{{- end -}}
```

### Conditional Includes

Include files only if they exist:
```bash
# In shell config
[ -f "$HOME/.config/shell/local.sh" ] && . "$HOME/.config/shell/local.sh"
```

Template-based conditional:
```go
{{- if stat (joinPath .chezmoi.homeDir ".work-config") -}}
# Include work-specific config
source ~/.work-config
{{- end -}}
```

### Multiple Machine Support

**Hostname-based configuration:**
```go
{{- if eq .chezmoi.hostname "work-laptop" -}}
# Work machine specific
export WORK_MODE=1
{{- else if eq .chezmoi.hostname "personal-mac" -}}
# Personal machine specific
export PERSONAL_MODE=1
{{- end -}}
```

**Using custom data:**
```go
# In .chezmoi.toml.tmpl
[data.machine]
    type = {{ promptStringOnce . "machine_type" "Machine type (work/personal)" | quote }}

# In templates
{{- if eq .machine.type "work" -}}
# Work configuration
{{- end -}}
```

### Secrets Management

This repo uses simple file-based secrets (not encrypted, for local-only use):

**Pattern:**
```bash
# In common.sh
[ -f "$HOME/.secrets" ] && . "$HOME/.secrets"
```

**User creates `~/.secrets`:**
```bash
export API_KEY="secret-value"
export PRIVATE_TOKEN="another-secret"
```

**For encrypted secrets, consider:**
- **age**: Simple encryption (chezmoi supports `age:` prefix)
- **1Password CLI**: `{{ onepassword "item" }}`
- **Bitwarden CLI**: `{{ bitwarden "item" }}`
- **gopass**: `{{ gopass "path/to/secret" }}`

**Example with age encryption:**
```bash
# Encrypt a file
chezmoi add --encrypt ~/.ssh/id_rsa

# Now stored as encrypted in repo
# Decrypted automatically on target machine
```

### Template Debugging Script

Create a test script for rapid template iteration:

```bash
#!/bin/bash
# test-template.sh

echo "=== Template Variables ==="
echo "OS: {{ .chezmoi.os }}"
echo "Arch: {{ .chezmoi.arch }}"
echo "Hostname: {{ .chezmoi.hostname }}"
echo "Username: {{ .chezmoi.username }}"
echo "Git name: {{ .git.name }}"
echo "Git email: {{ .git.email }}"

echo ""
echo "=== Conditional Test ==="
{{- if eq .chezmoi.os "darwin" -}}
echo "Running on macOS"
{{- else if eq .chezmoi.os "linux" -}}
echo "Running on Linux"
{{- end -}}
```

Run:
```bash
chezmoi execute-template < test-template.sh
```

---

## Cross-References

- **AGENTS.md** - Operational procedures for AI agents
  - Apply skill: Initial setup and re-applying
  - Modify skill: Editing existing files
  - Extend skill: Adding new files and tools
  - Debug skill: Troubleshooting issues

- **MISE.md** - mise tool manager reference
  - Tool installation patterns
  - Hook script integration
  - Backend configuration

- **TROUBLESHOOTING.md** - Problem-solving guide
  - Common errors
  - Recovery procedures
  - Platform-specific issues

---

## Quick Command Reference

| Command | Description |
|---------|-------------|
| `chezmoi doctor` | Health check |
| `chezmoi status` | Show file status |
| `chezmoi managed` | List managed files |
| `chezmoi diff` | Preview changes |
| `chezmoi apply` | Apply all changes |
| `chezmoi apply FILE` | Apply specific file |
| `chezmoi apply --dry-run` | Simulate apply |
| `chezmoi edit FILE` | Edit source file |
| `chezmoi add FILE` | Add file to source |
| `chezmoi source-path FILE` | Get source location |
| `chezmoi target-path FILE` | Get target location |
| `chezmoi data` | Show template data |
| `chezmoi execute-template` | Test templates |
| `chezmoi update` | Pull and apply updates |

---

## Document Information

**Purpose**: Reference for chezmoi configuration in the boilerplate repository  
**Target audience**: AI agents and users working with dotfiles  
**Maintenance**: Update when adding new templates, hooks, or patterns  
**Version control**: Changes tracked in repository

For questions or issues, refer to TROUBLESHOOTING.md or run `chezmoi doctor`.
