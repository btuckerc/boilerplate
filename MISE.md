---
title: mise Tool Management
description: Managing binaries, versions, and tool backends with mise
target: AI agents and users
skills: [apply, extend, debug]
type: reference
last_updated: 2025-02-09
---

# mise Tool Management

Complete reference for managing tools, versions, and backends in this repository using mise.

---

## 1. mise Overview

**mise** is a polyglot tool manager that handles installation and versioning of programming languages, CLI tools, and language servers. It replaces multiple version managers (nvm, rbenv, pyenv, etc.) with a single unified tool.

### Why mise in This Repository

- **Unified tooling**: One tool manages Python, Node.js, Go, Ruby, and 100+ binaries
- **Fast installation**: Downloads pre-built binaries instead of compiling from source
- **Version pinning**: Exact version control for reproducible environments
- **Multiple backends**: Supports various installation sources (GitHub releases, npm, pipx, etc.)
- **Shell integration**: Automatic PATH management and activation

### Configuration Locations

```
~/.config/mise/
├── config.toml                 # Primary configuration (tracked)
├── config.optional.toml        # Optional tools (tracked)
├── mise.local.toml            # User preferences (gitignored)
└── hooks/
    └── executable_preinstall   # Pre-install hook for prompts
```

**Source locations** (in repository):
- `home/dot_config/mise/config.toml`
- `home/dot_config/mise/config.optional.toml`
- `home/dot_config/mise/hooks/executable_preinstall`

### Shell Integration

mise activates automatically in your shell through the activation script in `~/.zshrc` and `~/.bashrc`:

```bash
eval "$(mise activate zsh)"   # In ~/.zshrc
eval "$(mise activate bash)"  # In ~/.bashrc
```

This activation:
1. Sets up the shim directory in PATH (`~/.local/share/mise/shims/`)
2. Configures auto-switching based on project `.tool-versions` files
3. Enables command interception for managed tools

### PATH Management

mise manages tool availability through two mechanisms:

**1. Shims directory** (primary method):
```
~/.local/share/mise/shims/
├── python -> /Users/user/.local/share/mise/installs/python/3.13/bin/python
├── node -> /Users/user/.local/share/mise/installs/node/20.11.0/bin/node
├── fzf -> /Users/user/.local/share/mise/installs/fzf/latest/bin/fzf
└── ...
```

**2. Direct installation paths**:
```
~/.local/share/mise/installs/
├── python/3.13/
├── node/lts/
├── go/1.25/
└── ...
```

### Activation Methods

**Automatic activation** (default):
Occurs when shell starts via `eval "$(mise activate)"`

**Manual activation** (when needed):
```bash
# If tools not found, manually activate
eval "$(mise activate zsh)"

# Or use mise exec for one-off commands
mise exec python@3.13 -- python script.py
```

**Check activation status**:
```bash
mise status
mise doctor
```

---

## 2. Configuration Files

### config.toml (Primary Configuration)

**Location**: `~/.config/mise/config.toml`  
**Source**: `home/dot_config/mise/config.toml`  
**Status**: Tracked in git

Structure:
```toml
[tools]
# Core dependencies - must install first
python = "3.13"
uv = "latest"
bun = "latest"
node = "lts"
go = "1.25"

# CLI tools with backend prefixes
"ubi:starship/starship" = "latest"
"aqua:neovim/neovim" = "latest"
"npm:typescript-language-server" = "latest"

[settings]
experimental = true
legacy_version_file = true
always_keep_download = false
plugin_autoupdate_last_check_duration = "7d"
jobs = 2
verbose = false
asdf_compat = true
color = true
task_output = "prefix"
http_timeout = "120"
raw = false

[hooks]
preinstall = "bash ${XDG_CONFIG_HOME:-$HOME/.config}/mise/hooks/preinstall"

[env]
# PATH additions
_.path = [
  "{{ config_root }}/shims",
  "~/.local/share/mise/shims",
]

[settings.pipx]
uvx = true

[settings.npm]
bun = true
```

**Key sections**:
- `[tools]`: All managed tools and versions
- `[settings]`: mise behavior configuration
- `[hooks]`: Lifecycle scripts (preinstall, postinstall)
- `[env]`: Environment variables and PATH modifications

### config.optional.toml (Optional Tools)

**Location**: `~/.config/mise/config.optional.toml`  
**Source**: `home/dot_config/mise/config.optional.toml`  
**Status**: Tracked in git

Purpose: Stores tools that users may or may not want to install. Entries are commented out by default.

Structure:
```toml
[tools]
# claude = "latest"  # Anthropic's CLI coding assistant
# "aqua:anomalyco/opencode" = "latest"  # Moved to main config.toml
```

**How it works**:
1. Tools listed as comments with descriptions
2. Pre-install hook prompts user during first `mise install`
3. User selections saved to `mise.local.toml`
4. Subsequent runs skip already-selected tools

### mise.local.toml (User Preferences)

**Location**: `~/.config/mise/mise.local.toml`  
**Status**: Gitignored (not tracked)

Purpose: Stores user-specific tool selections and overrides.

Example content (auto-generated):
```toml
[tools]

claude = "latest"
"aqua:anomalyco/opencode" = "latest"
```

**Common uses**:
- Optional tool selections from prompt
- Version overrides (e.g., `python = "3.12"` instead of `3.13`)
- Environment-specific configurations
- Development overrides

**Never commit this file** - it contains personal preferences.

### hooks/executable_preinstall

**Location**: `~/.config/mise/hooks/executable_preinstall`  
**Source**: `home/dot_config/mise/hooks/executable_preinstall`  
**Status**: Tracked in git

Purpose: Bash script that runs before any tool installation.

**Functions**:
1. **Python symlink creation**: Creates `python` -> `python3` symlink for Ruby builds
2. **Optional tools prompt**: Interactive selection of optional tools
3. **PATH setup**: Ensures shim directory is in PATH

**Execution flow**:
```
mise install called
    ↓
preinstall hook runs
    ↓
Checks for python3 → python symlink
    ↓
Parses config.optional.toml
    ↓
Prompts user for selections (if first run)
    ↓
Writes selections to mise.local.toml
    ↓
Continues with installation
```

---

## 3. Tool Backends

mise supports multiple installation backends. Each backend has specific syntax and use cases.

### ubi: GitHub Binary Releases

**Syntax**: `"ubi:owner/repo" = "version"`  
**Full form**: `"ubi:owner/repo" = { version = "latest", exe = "binary-name" }`

**What it does**: Downloads pre-built binaries directly from GitHub releases.

**When to use**:
- CLI tools distributed as GitHub releases
- Single static binaries
- Fast installation (no compilation)
- Cross-platform tools

**Examples from config**:
```toml
"ubi:twpayne/chezmoi" = "latest"
"ubi:starship/starship" = "latest"
"ubi:junegunn/fzf" = "latest"
"ubi:sharkdp/bat" = "latest"
"ubi:BurntSushi/ripgrep" = "latest"
"ubi:eza-community/eza" = "latest"
"ubi:sharkdp/fd" = "latest"
"ubi:sxyazi/yazi" = "latest"
"ubi:carapace-sh/carapace-bin" = { version = "latest", exe = "carapace" }
```

**Best practices**:
- Always use `latest` for actively maintained tools
- Use `{ exe = "name" }` when binary name differs from repo name
- ubi automatically detects OS/architecture and downloads correct binary
- No compilation required - fastest installation method

**Troubleshooting**:
- If download fails, check GitHub releases page exists
- Some repos don't use standard naming (need `exe` parameter)
- Corporate proxies may block GitHub API requests

### aqua: Fast Declarative Registry

**Syntax**: `"aqua:owner/repo" = "version"`

**What it does**: Uses the aqua registry for fast, declarative tool installation. Aqua maintains a curated registry of tool definitions.

**When to use**:
- Tools in the aqua registry (check with `mise search`)
- Even faster than ubi (direct downloads)
- Cryptographically verified checksums
- Version constraints and dependencies

**Examples from config**:
```toml
"aqua:neovim/neovim" = "latest"
"aqua:cli/cli" = "latest"                    # GitHub CLI
"aqua:BurntSushi/ripgrep" = "latest"
"aqua:LuaLS/lua-language-server" = "latest"
"aqua:rust-lang/rust-analyzer" = "latest"
"aqua:hashicorp/terraform-ls" = "latest"
"aqua:JohnnyMorganz/StyLua" = "latest"
"aqua:mvdan/gofumpt" = "latest"
"aqua:mvdan/sh" = "latest"
"aqua:anomalyco/opencode" = "latest"
```

**Advantages over ubi**:
- Faster downloads (optimized CDN)
- Checksum verification
- Handles complex extraction (tar.gz, zip)
- Better version resolution
- Supports more complex tool configurations

**Search aqua registry**:
```bash
# Search for tools in aqua registry
mise search <tool-name>

# Example
mise search neovim
mise search terraform
```

### npm: Node Packages

**Syntax**: `"npm:package-name" = "version"`

**What it does**: Installs Node.js packages globally using npm (or bun when configured).

**When to use**:
- Language servers for editors
- Node-based CLI tools
- TypeScript/JavaScript tooling

**Configuration**:
```toml
[settings.npm]
bun = true  # Use bun instead of npm for faster installs
```

**Examples from config**:
```toml
"npm:typescript-language-server" = "latest"
"npm:typescript" = "latest"
"npm:pyright" = "latest"
"npm:yaml-language-server" = "latest"
"npm:vscode-langservers-extracted" = "latest"
"npm:bash-language-server" = "latest"
"npm:dockerfile-language-server-nodejs" = "latest"
"npm:prettier" = "latest"
"npm:@playwright/mcp" = "latest"
```

**Best practices**:
- Use `bun = true` for 10x faster installations
- Language servers should use `latest` (updated frequently)
- Some packages need `node` installed first (mise handles ordering)
- Scoped packages (`@org/name`) work fine

### go: Go Tools

**Syntax**: `"go:import/path" = "version"`

**What it does**: Installs Go packages using `go install`.

**When to use**:
- Go language tools
- Go-based CLI utilities
- LSPs written in Go

**Examples from config**:
```toml
"go:golang.org/x/tools/gopls" = "latest"           # Go language server
"go:golang.org/x/tools/cmd/goimports" = "latest"   # Go import formatter
"go:mvdan.cc/sh/v3/cmd/shfmt" = "latest"          # Shell script formatter
```

**Version handling**:
- `latest` - Most recent version
- `v1.2.3` - Specific tag
- `@branch` - Specific branch
- `@commit` - Specific commit hash

**Best practices**:
- Go tools install quickly (compiled locally)
- Ensure `go` is installed before Go tools (mise handles dependencies)
- Some tools need specific Go versions

### pipx: Python Applications

**Syntax**: `"pipx:package-name" = "version"`

**What it does**: Installs Python CLI applications in isolated virtual environments.

**When to use**:
- Python CLI tools (black, flake8, etc.)
- Tools that shouldn't affect system Python
- Applications with complex dependencies

**Configuration**:
```toml
[settings.pipx]
uvx = true  # Use uvx instead of pipx for faster installs
```

**Examples from config**:
```toml
"pipx:black" = "latest"              # Python code formatter
"pipx:yubikey-manager" = "latest"    # YubiKey management tool
```

**Isolation benefits**:
- Each tool in its own virtual environment
- No dependency conflicts between tools
- Clean uninstallation
- System Python remains untouched

**Best practices**:
- Use `uvx = true` for much faster installations
- pipx requires `python` to be installed first
- Some tools need compilation (depends on platform)

### gem: Ruby Gems

**Syntax**: `"gem:gem-name" = "version"`

**What it does**: Installs Ruby gems globally.

**When to use**:
- Ruby language tools
- Rails development tools
- Ruby LSPs

**Examples from config**:
```toml
"gem:solargraph" = "latest"    # Ruby language server
"gem:rails" = "latest"         # Rails framework
```

**Important notes**:
- Ruby gems require `ruby` to be installed first
- Some gems with native extensions need build tools
- The preinstall hook ensures `python` command exists for Ruby builds
- Installation can be slow for gems with C extensions

**Troubleshooting Ruby builds**:
If Ruby installation fails with "python command not found":
```bash
# The preinstall hook should handle this automatically
# If not, manually create symlink:
ln -sf $(which python3) ~/.local/share/mise/shims/python
```

### core: mise Built-ins

**Syntax**: `tool = "version"` (no prefix needed)

**What it does**: mise's built-in language version managers.

**Available core tools**:
- `python` - CPython with version management
- `node` - Node.js via nodenv
- `go` - Go language
- `ruby` - Ruby via ruby-build
- `bun` - Bun JavaScript runtime
- `uv` - Ultra-fast Python package manager

**Examples from config**:
```toml
python = "3.13"
node = "lts"
go = "1.25"
ruby = "3"
bun = "latest"
uv = "latest"
```

**Version specifications**:
- `"3.13"` - Exact version
- `"lts"` - Long-term support version (Node.js)
- `"latest"` - Most recent release
- `"3"` - Latest in major version series

**Advantages**:
- First-class support in mise
- Fast version switching
- Handles complex build dependencies
- Automatic PATH management

---

## 4. Tool Inventory

Complete list of all tools configured in `config.toml`, organized by category.

### Core Languages & Runtimes

**python = "3.13"**
- **Backend**: core
- **What**: CPython 3.13 interpreter
- **Used for**: Running Python scripts, pipx backend, Ruby build dependency
- **Notes**: Required for pipx and many language servers

**node = "lts"**
- **Backend**: core
- **What**: Node.js LTS version
- **Used for**: npm packages, JavaScript/TypeScript development
- **Notes**: Automatically installs npm; required for all npm:* tools

**go = "1.25"**
- **Backend**: core
- **What**: Go programming language
- **Used for**: Go development, installing Go-based tools
- **Notes**: Required for all go:* tools

**ruby = "3"**
- **Backend**: core
- **What**: Ruby 3.x interpreter
- **Used for**: Ruby development, Rails, gem installations
- **Notes**: Installed last due to build complexity; requires python

**bun = "latest"**
- **Backend**: core
- **What**: Bun JavaScript runtime and package manager
- **Used for**: Fast npm package installation (configured in settings.npm)
- **Notes**: 10x faster than npm for package installation

**uv = "latest"**
- **Backend**: core
- **What**: Ultra-fast Python package installer and resolver
- **Used for**: pipx backend (configured in settings.pipx)
- **Notes**: Replaces pipx for faster Python tool installation

### AI Coding Assistants

**"aqua:anomalyco/opencode" = "latest"**
- **Backend**: aqua
- **What**: AI-powered code assistant CLI
- **Used for**: AI-assisted development tasks
- **Notes**: Can be disabled in optional config if not needed

### CLI Productivity Tools

**"ubi:twpayne/chezmoi" = "latest"**
- **Backend**: ubi
- **What**: Dotfile manager
- **Used for**: Managing configuration files across machines
- **Notes**: Self-managing - chezmoi manages its own installation

**"ubi:starship/starship" = "latest"**
- **Backend**: ubi
- **What**: Cross-shell prompt customization
- **Used for**: Enhanced shell prompt with git info, timings, etc.
- **Notes**: Configured via `~/.config/starship.toml`

**"ubi:ajeetdsouza/zoxide" = "latest"**
- **Backend**: ubi
- **What**: Smarter cd command with learning
- **Used for**: Quick directory navigation
- **Notes**: Replaces `cd` with intelligent jumping

**"ubi:junegunn/fzf" = "latest"**
- **Backend**: ubi
- **What**: Command-line fuzzy finder
- **Used for**: Interactive filtering of lists, files, history
- **Notes**: Used in shell functions for file finding

**"ubi:sharkdp/bat" = "latest"**
- **Backend**: ubi
- **What**: Cat clone with syntax highlighting
- **Used for**: Viewing files with syntax highlighting
- **Notes**: Alias: `cat='bat --paging=never'`

**"ubi:sharkdp/fd" = "latest"**
- **Backend**: ubi
- **What**: Simple, fast alternative to find
- **Used for**: Finding files by name
- **Notes**: Better defaults than find, respects .gitignore

**"ubi:sxyazi/yazi" = "latest"**
- **Backend**: ubi
- **What**: Terminal file manager
- **Used for**: TUI-based file navigation and management
- **Notes**: vim-like keybindings, preview support

**"ubi:jqlang/jq" = "latest"**
- **Backend**: ubi
- **What**: JSON processor and query tool
- **Used for**: Parsing and transforming JSON data
- **Notes**: Essential for API work and automation

**"ubi:charmbracelet/gum" = "latest"**
- **Backend**: ubi
- **What**: Tool for glamorous shell scripts
- **Used for**: Creating interactive TUI prompts and menus
- **Notes**: Used in preinstall hook for optional tools

**"ubi:jesseduffield/lazygit" = "latest"**
- **Backend**: ubi
- **What**: Simple terminal UI for git commands
- **Used for**: Interactive git operations
- **Notes**: vim-like interface for staging, committing, rebasing

**"ubi:tree-sitter/tree-sitter" = "latest"**
- **Backend**: ubi
- **What**: Parser generator tool and incremental parsing library
- **Used for**: Building parsers for syntax highlighting
- **Notes**: Required by some editors and language tools

**"ubi:carapace-sh/carapace-bin" = { version = "latest", exe = "carapace" }**
- **Backend**: ubi
- **What**: Multi-shell completion engine
- **Used for**: Enhanced shell completions for CLI tools
- **Notes**: Configured in shell initialization; exe parameter needed because binary is "carapace" not "carapace-bin"

### Editor & Development Tools

**"aqua:neovim/neovim" = "latest"**
- **Backend**: aqua
- **What**: Hyperextensible Vim-based text editor
- **Used for**: Primary text editing and development
- **Notes**: Requires configuration in `~/.config/nvim/`

**"aqua:cli/cli" = "latest"**
- **Backend**: aqua
- **What**: GitHub CLI tool
- **Used for**: Interacting with GitHub from command line
- **Notes**: PRs, issues, releases, repo management

**"aqua:BurntSushi/ripgrep" = "latest"**
- **Backend**: aqua
- **What**: Line-oriented search tool
- **Used for**: Fast recursive text search
- **Notes**: Faster than grep, respects .gitignore

**"asdf:mise-plugins/mise-tmux" = "latest"**
- **Backend**: asdf
- **What**: Terminal multiplexer
- **Used for**: Managing multiple terminal sessions
- **Notes**: Only asdf plugin for tmux; provides latest version

### Language Servers (LSPs)

**"npm:typescript-language-server" = "latest"**
- **Backend**: npm
- **What**: TypeScript language server protocol implementation
- **Used for**: IDE features for TypeScript in editors
- **Notes**: Requires node; works with neovim, VSCode, etc.

**"npm:typescript" = "latest"**
- **Backend**: npm
- **What**: TypeScript compiler
- **Used for**: Compiling TypeScript to JavaScript
- **Notes**: Required by typescript-language-server

**"npm:pyright" = "latest"**
- **Backend**: npm
- **What**: Static type checker for Python
- **Used for**: Python type checking and LSP features
- **Notes**: Microsoft's Python language server

**"npm:yaml-language-server" = "latest"**
- **Backend**: npm
- **What**: Language server for YAML
- **Used for**: YAML validation, completion, hover info
- **Notes**: Essential for editing Kubernetes, GitHub Actions, etc.

**"npm:vscode-langservers-extracted" = "latest"**
- **Backend**: npm
- **What**: Language servers extracted from VSCode
- **Used for**: JSON, HTML, CSS, ESLint language features
- **Notes**: Bundle of multiple language servers

**"npm:bash-language-server" = "latest"**
- **Backend**: npm
- **What**: Language server for Bash
- **Used for**: Shell script IntelliSense, linting
- **Notes**: Requires node; provides completion and diagnostics

**"npm:dockerfile-language-server-nodejs" = "latest"**
- **Backend**: npm
- **What**: Language server for Dockerfiles
- **Used for**: Dockerfile editing support
- **Notes**: Syntax highlighting, linting, completion

**"npm:prettier" = "latest"**
- **Backend**: npm
- **What**: Opinionated code formatter
- **Used for**: Formatting JavaScript, TypeScript, JSON, YAML, etc.
- **Notes**: LSP-compatible formatter

**"npm:@playwright/mcp" = "latest"**
- **Backend**: npm
- **What**: Playwright Model Context Protocol
- **Used for**: Browser automation and testing
- **Notes**: Scoped package for Playwright integration

**"go:golang.org/x/tools/gopls" = "latest"**
- **Backend**: go
- **What**: Go language server (official)
- **Used for**: Go IDE features
- **Notes**: Google's official Go language server

**"go:golang.org/x/tools/cmd/goimports" = "latest"**
- **Backend**: go
- **What**: Tool to fix Go import statements
- **Used for**: Automatic Go import management
- **Notes**: Usually run on save in editors

**"pipx:black" = "latest"**
- **Backend**: pipx
- **What**: Opinionated Python code formatter
- **Used for**: Formatting Python code
- **Notes**: "The uncompromising code formatter"

**"pipx:yubikey-manager" = "latest"**
- **Backend**: pipx
- **What**: Tool for configuring YubiKeys
- **Used for**: YubiKey management and configuration
- **Notes**: CLI for YubiKey hardware tokens

**"aqua:LuaLS/lua-language-server" = "latest"**
- **Backend**: aqua
- **What**: Language server for Lua
- **Used for**: Lua development (Neovim configs, etc.)
- **Notes**: Essential for editing Neovim Lua configurations

**"aqua:rust-lang/rust-analyzer" = "latest"**
- **Backend**: aqua
- **What**: Language server for Rust
- **Used for**: Rust IDE features
- **Notes**: Official Rust language server

**"aqua:hashicorp/terraform-ls" = "latest"**
- **Backend**: aqua
- **What**: Terraform language server
- **Used for**: Terraform/HCL editing support
- **Notes**: Official HashiCorp language server

### Code Formatters & Linters

**"aqua:JohnnyMorganz/StyLua" = "latest"**
- **Backend**: aqua
- **What**: Opinionated Lua code formatter
- **Used for**: Formatting Lua code (Neovim configs)
- **Notes**: Similar to Black for Lua

**"aqua:mvdan/gofumpt" = "latest"**
- **Backend**: aqua
- **What**: Stricter gofmt
- **Used for**: Formatting Go code with stricter rules
- **Notes**: Drop-in replacement for gofmt

**"aqua:mvdan/sh" = "latest"**
- **Backend**: aqua
- **What**: Shell parser and formatter
- **Used for**: Formatting shell scripts
- **Notes**: Includes shfmt for formatting

**"gem:solargraph" = "latest"**
- **Backend**: gem
- **What**: Ruby language server
- **Used for**: Ruby IDE features
- **Notes**: Requires ruby; provides completion, diagnostics

**"gem:rails" = "latest"**
- **Backend**: gem
- **What**: Ruby on Rails framework
- **Used for**: Rails web development
- **Notes**: Installs Rails gem and dependencies

---

## 5. Optional Tools Workflow

This repository supports optional tools that users can choose to install or skip.

### How It Works

**1. Definition in config.optional.toml**:
```toml
[tools]
# claude = "latest"  # Anthropic's CLI coding assistant
# "aqua:anomalyco/opencode" = "latest"  # Moved to main config.toml
```

**2. Prompt mechanism**: During the first `mise install` run, the preinstall hook:
   - Parses commented entries from `config.optional.toml`
   - Presents an interactive menu with descriptions
   - Allows selection: all (a), select individually (s), or none (n)

**3. Selection storage**: User choices are saved to `mise.local.toml`:
```toml
[tools]
claude = "latest"
```

**4. Marker file**: `.optional-tools-prompted` prevents re-prompting

### The Prompt Menu

When running `mise install` for the first time:

```
Optional tools:
  1) claude                             Anthropic's CLI coding assistant

a) All  s) Select  n) None (Enter=None)
> 
```

**Options**:
- **a/all**: Install all optional tools
- **s/select**: Choose tools individually with y/N prompts
- **n/none** (or Enter): Skip all optional tools
- Already-enabled tools show ✓ and are skipped

### Adding New Optional Tools

To add a new optional tool:

1. **Edit config.optional.toml**:
```toml
[tools]
# claude = "latest"  # Anthropic's CLI coding assistant
# "npm:new-tool" = "latest"  # Description of the tool
```

2. **Clear marker** (for testing):
```bash
rm ~/.config/mise/.optional-tools-prompted
```

3. **Test the prompt**:
```bash
mise install
```

4. **Verify installation**:
```bash
which new-tool
new-tool --version
```

### Reconfiguring Optional Tools

To change optional tool selections later:

**Option 1: Edit mise.local.toml directly**:
```bash
chezmoi edit ~/.config/mise/mise.local.toml
# Add or remove entries
mise install
```

**Option 2: Clear marker and re-prompt**:
```bash
rm ~/.config/mise/.optional-tools-prompted
mise install
# Select new tools from menu
```

**Option 3: Comment out in config.optional.toml**:
```toml
[tools]
# claude = "latest"  # Disabled temporarily
```
Then remove from `mise.local.toml` if present.

### Examples of Optional Tools

**claude**: Anthropic's CLI coding assistant
- Provides AI assistance for coding tasks
- Requires API key configuration
- Large download (~100MB)

**opencode**: AI-powered code assistant
- Alternative AI assistant
- May be redundant if claude is installed

### Moving from Optional to Required

If a tool becomes essential, move it to `config.toml`:

1. Remove from `config.optional.toml`
2. Add to `config.toml`:
```toml
"backend:tool" = "latest"
```
3. Users with existing `mise.local.toml` will have duplicate entry (harmless)
4. New users get it automatically

---

## 6. Adding New Tools

Step-by-step workflow for adding new tools to the configuration.

### Step 1: Choose the Right Backend

**Decision tree**:

```
Tool type?
├── GitHub release (binary)
│   ├── In aqua registry? → aqua:owner/repo
│   └── Not in registry → ubi:owner/repo
├── Node package
│   └── npm:package-name
├── Go tool
│   └── go:import/path
├── Python CLI
│   └── pipx:package-name
├── Ruby gem
│   └── gem:gem-name
└── Language runtime
    └── core (python, node, go, ruby, bun, uv)
```

**Quick reference**:

| Backend | Use for | Example |
|---------|---------|---------|
| `aqua:` | Tools in aqua registry | `aqua:neovim/neovim` |
| `ubi:` | GitHub binary releases | `ubi:starship/starship` |
| `npm:` | Node packages | `npm:typescript` |
| `go:` | Go tools | `go:golang.org/x/tools/gopls` |
| `pipx:` | Python CLIs | `pipx:black` |
| `gem:` | Ruby gems | `gem:solargraph` |
| (none) | Core languages | `python`, `node` |

### Step 2: Find Tool Information

**For aqua tools**:
```bash
mise search <tool-name>
# Look for "aqua:owner/repo" in output
```

**For ubi tools** (GitHub releases):
```bash
# Check GitHub releases page
https://github.com/owner/repo/releases

# Verify naming
# If binary name differs from repo, use exe parameter
```

**For npm packages**:
```bash
npm search <package-name>
# Or check npmjs.com
```

**For Go tools**:
```bash
# Check go.dev or source repository
# Verify import path matches go install syntax
```

**For pipx packages**:
```bash
pipx search <package-name>
# Or check PyPI
```

### Step 3: Add to Configuration

**Edit through chezmoi**:
```bash
chezmoi edit ~/.config/mise/config.toml
```

**Add entry in [tools] section**:
```toml
[tools]
# Existing tools...

# Add new tool
"aqua:owner/repo" = "latest"
```

**Special cases**:

**ubi with different binary name**:
```toml
"ubi:carapace-sh/carapace-bin" = { version = "latest", exe = "carapace" }
```

**Specific version**:
```toml
"aqua:owner/repo" = "1.2.3"
```

**Version constraints**:
```toml
"npm:package" = ">=2.0.0"
```

### Step 4: Test Installation

**Preview changes**:
```bash
chezmoi diff ~/.config/mise/config.toml
```

**Apply and install**:
```bash
chezmoi apply ~/.config/mise/config.toml
mise install
```

**Watch for errors**:
- Backend not found → Wrong prefix or typo
- Version not found → Check available versions with `mise ls-remote <tool>`
- Permission denied → Check file permissions

### Step 5: Verify Activation

**Check tool availability**:
```bash
which <tool-name>
<tool-name> --version
```

**If not found**:
```bash
# Reload shell
hash -r  # Clear command hash
source ~/.zshrc  # or ~/.bashrc

# Or manually activate mise
eval "$(mise activate zsh)"

# Check if installed
mise list | grep <tool-name>

# Check PATH
echo $PATH | tr ':' '\n' | grep mise
```

### Step 6: Document the Tool

Add to this document:
1. Add to Tool Inventory section (Section 4)
2. Include backend, purpose, and notes
3. Update backend examples if applicable

**Example documentation entry**:
```markdown
**"aqua:newtool/newtool" = "latest"**
- **Backend**: aqua
- **What**: Brief description
- **Used for**: Primary use case
- **Notes**: Any important details
```

### Backend Selection Examples

**Example 1: New CLI tool from GitHub**

Tool: `extrawurst/tree-sitter-foo`

1. Check aqua registry: `mise search tree-sitter-foo`
   - Not found
2. Check GitHub releases: Has binary releases
3. Decision: Use ubi (not in aqua yet)
4. Add: `"ubi:extrawurst/tree-sitter-foo" = "latest"`

**Example 2: New Node LSP**

Tool: `graphql-language-service`

1. It's a Node package
2. Decision: Use npm
3. Add: `"npm:graphql-language-service" = "latest"`

**Example 3: New Go linter**

Tool: `golangci-lint`

1. Check aqua: `mise search golangci-lint`
   - Found: `aqua:golangci/golangci-lint`
2. Decision: Use aqua (faster than go install)
3. Add: `"aqua:golangci/golangci-lint" = "latest"`

---

## 7. Version Management

### Installing Specific Versions

**Exact version**:
```bash
mise install python@3.12
mise install node@20.11.0
```

**In config.toml**:
```toml
python = "3.12"
node = "20.11.0"
```

### Version Specifications

**latest**: Always newest version
```toml
"ubi:starship/starship" = "latest"
```

**lts**: Long-term support (Node.js only)
```toml
node = "lts"
```

**Major version**: Latest in series
```toml
python = "3"      # Latest Python 3.x
ruby = "3"        # Latest Ruby 3.x
go = "1.25"       # Latest Go 1.25.x
```

**Semver ranges**:
```toml
node = ">=20"           # 20.0.0 or higher
node = "^20.11"         # 20.11.0 or higher, < 21.0.0
node = ">=20 <21"       # 20.x only
```

### Pinning vs Floating

**Floating (recommended for most tools)**:
```toml
"ubi:starship/starship" = "latest"
```
- Updates to newest version on `mise upgrade`
- Good for: CLI tools, LSPs, formatters
- Risk: Occasional breaking changes

**Pinning (for stability)**:
```toml
python = "3.13.1"
node = "20.11.0"
```
- Stays on exact version until manually changed
- Good for: Language runtimes in production
- Requires manual updates

**Hybrid approach** (this repository):
- Languages pinned to major/minor: `python = "3.13"`
- Tools use `latest` for automatic updates

### Listing Tools and Versions

**Installed versions**:
```bash
mise list
# or
mise ls
```

Output:
```
Tool        Version          Source                       Installed
python      3.13             ~/.config/mise/config.toml   Yes
node        20.11.0 (lts)    ~/.config/mise/config.toml   Yes
starship    latest           ~/.config/mise/config.toml   Yes
```

**Available versions**:
```bash
mise ls-remote python
mise ls-remote node
```

Shows all installable versions from newest to oldest.

**Check specific tool**:
```bash
mise list starship
mise ls-remote ubi:starship/starship
```

### Upgrading Tools

**Upgrade all**:
```bash
mise upgrade
```

**Upgrade specific tool**:
```bash
mise upgrade starship
mise upgrade python
```

**After editing config.toml**:
```bash
# Install new/updated tools
mise install

# Or force reinstall
mise install --force
```

### Downgrading Tools

**Uninstall current**:
```bash
mise uninstall python@3.13
```

**Install older version**:
```bash
mise install python@3.12
```

**Update config**:
```toml
python = "3.12"  # Changed from "3.13"
```

**Reinstall all**:
```bash
mise install
```

### Cleaning Up

**Remove unused versions**:
```bash
mise prune
# Removes versions not referenced in config
```

**Remove specific version**:
```bash
mise uninstall node@18.19.0
```

---

## 8. PATH and Activation

### How mise Activates in Shell

**Shell initialization** (in `~/.zshrc` and `~/.bashrc`):
```bash
eval "$(mise activate zsh)"
```

**What this does**:
1. Adds `~/.local/share/mise/shims/` to PATH
2. Sets up shell hooks for auto-switching
3. Enables mise command interception

### Shim Directory

**Location**: `~/.local/share/mise/shims/`

**Contents**:
```
shims/
├── python -> /Users/user/.local/share/mise/installs/python/3.13/bin/python
├── node -> /Users/user/.local/share/mise/installs/node/20.11.0/bin/node
├── fzf -> /Users/user/.local/share/mise/installs/fzf/latest/fzf
└── ...
```

**How shims work**:
- When you run `python`, shell finds shim in PATH first
- Shim checks mise for which version to use
- Executes correct binary from installs directory

### PATH Order

**Resulting PATH** (simplified):
```
/Users/user/.local/share/mise/shims:/usr/local/bin:/usr/bin:/bin
```

**Priority**: mise shims come first, ensuring managed tools override system tools.

### Troubleshooting PATH Issues

**Symptom**: `command not found` for installed tool

**Diagnosis**:
```bash
# Check if shim exists
ls ~/.local/share/mise/shims/ | grep <tool>

# Check PATH
echo $PATH | tr ':' '\n'

# Check if mise activated
mise status
```

**Solutions**:

**1. Reset command hash**:
```bash
hash -r  # bash/zsh
rehash   # zsh only
```

**2. Source shell config**:
```bash
source ~/.zshrc  # or ~/.bashrc
```

**3. Manual activation**:
```bash
eval "$(mise activate zsh)"
```

**4. Check mise status**:
```bash
mise doctor
```

### Manual Activation

When automated activation fails:

**Current shell only**:
```bash
eval "$(mise activate zsh)"
```

**One-off command**:
```bash
mise exec python@3.13 -- python script.py
```

**Full PATH setup** (emergency):
```bash
export PATH="$HOME/.local/share/mise/shims:$PATH"
```

### Verifying Activation

**Check mise is active**:
```bash
mise status
```

**Check tool path**:
```bash
which python
# Should show: /Users/user/.local/share/mise/shims/python

# NOT: /usr/bin/python
```

**Check version**:
```bash
python --version
# Should match config.toml version
```

---

## 9. Troubleshooting mise

### Installation Failures

**Symptom**: `mise install` fails with download error

**Causes and solutions**:

**1. Network issues**:
```bash
# Test connectivity
curl -I https://github.com

# Try with verbose output
mise install --verbose
```

**2. Rate limiting (GitHub)**:
```bash
# Set GitHub token
export GITHUB_TOKEN=your_token_here
mise install

# Or add to ~/.zshrc
```

**3. Tool not found**:
```bash
# Check spelling
mise search <tool-name>

# Verify backend prefix
# Correct: "ubi:owner/repo"
# Wrong: "ub:owner/repo" or "owner/repo"
```

### Backend Errors

**ubi: "no asset found"**
- Tool doesn't have GitHub releases
- Wrong repository name
- Solution: Use different backend or check repo

**aqua: "checksum verification failed"**
- Corrupted download
- Solution: Retry installation or clear cache

**npm: "permission denied"**
- bun/npm not properly configured
- Solution: Check [settings.npm] section

**go: "no go.mod"**
- Tool doesn't support `go install`
- Solution: Use aqua or ubi instead

**pipx: "python not found"**
- Python not installed
- Solution: Ensure python is in config.toml before pipx tools

**gem: "ruby not found"**
- Ruby not installed
- Solution: Ensure ruby is in config.toml before gems

### PATH Not Found

**Symptom**: Tool installed but `command not found`

**Checklist**:
```bash
# 1. Verify installation
mise list | grep <tool>

# 2. Check shims
ls ~/.local/share/mise/shims/

# 3. Check PATH order
echo $PATH | tr ':' '\n' | head -5
# Should show mise shims first

# 4. Reset hash
hash -r

# 5. Reload shell
exec zsh  # or exec bash
```

**If still not found**:
```bash
# Manual activation
eval "$(mise activate zsh)"

# Or emergency PATH export
export PATH="$HOME/.local/share/mise/shims:$PATH"
```

### Version Conflicts

**Symptom**: Wrong version being used

**Example**: System Python used instead of mise Python

**Diagnosis**:
```bash
which python
# If /usr/bin/python instead of shim, PATH issue

which -a python
# Shows all python executables in PATH
```

**Solutions**:

**1. Ensure mise shims first in PATH**:
```bash
# Check
echo $PATH

# Should start with: ~/.local/share/mise/shims:
```

**2. Check shell config order**:
```bash
# mise activation should come after other PATH modifications
cat ~/.zshrc | grep -n "eval.*mise activate"
```

**3. Force specific version**:
```bash
mise use python@3.13
```

**4. Project-level override**:
```bash
# Create .tool-versions in project
echo "python 3.12" > .tool-versions
mise install
```

### Ruby Build Failures

**Symptom**: Ruby installation fails with "python: command not found"

**Cause**: Ruby build requires a `python` command, but only `python3` exists

**Solution** (handled automatically by preinstall hook):
```bash
# Manual fix if hook fails:
mkdir -p ~/.local/share/mise/shims
ln -sf $(which python3) ~/.local/share/mise/shims/python
export PATH="$HOME/.local/share/mise/shims:$PATH"
mise install ruby
```

**Prevention**: The preinstall hook in `hooks/executable_preinstall` creates this symlink automatically before any installation.

### Network Issues

**Symptom**: Timeouts, SSL errors, or connection refused

**Solutions**:

**1. Increase timeout**:
```toml
[settings]
http_timeout = "300"  # Increase from default 120
```

**2. Configure proxy**:
```bash
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
mise install
```

**3. Disable SSL verification** (not recommended):
```bash
export MISE_INSECURE=1
mise install
```

**4. Use mirrors**:
```toml
[settings]
# Some backends support mirrors
```

### Reset and Recovery

**Nuclear option** (complete reset):
```bash
# 1. Backup current config
cp ~/.config/mise/config.toml ~/mise-config-backup.toml

# 2. Remove all installations
rm -rf ~/.local/share/mise/installs/*
rm -rf ~/.local/share/mise/shims/*

# 3. Reinstall everything
mise install
```

**Safe reset** (keep config):
```bash
# Force reinstall all
mise install --force
```

**Clean up unused**:
```bash
mise prune
```

### Getting Help

**Built-in help**:
```bash
mise --help
mise install --help
mise <command> --help
```

**Diagnostics**:
```bash
mise doctor
mise status
```

**Documentation**:
- mise website: https://mise.jdx.dev
- GitHub issues: https://github.com/jdx/mise/issues

---

## Quick Reference

### Essential Commands

```bash
# Install all tools from config
mise install

# Install specific tool
mise install node@20

# Upgrade all
mise upgrade

# Upgrade specific tool
mise upgrade python

# List installed
mise list

# List available versions
mise ls-remote python

# Check status
mise status

# Doctor/diagnostics
mise doctor
```

### Configuration Files

| File | Purpose | Tracked |
|------|---------|---------|
| `~/.config/mise/config.toml` | Primary config | Yes |
| `~/.config/mise/config.optional.toml` | Optional tools | Yes |
| `~/.config/mise/mise.local.toml` | User overrides | No |
| `~/.local/share/mise/shims/` | Tool shims | Auto-generated |

### Backend Prefixes

| Prefix | Example |
|--------|---------|
| (none) | `python = "3.13"` |
| `ubi:` | `"ubi:starship/starship"` |
| `aqua:` | `"aqua:neovim/neovim"` |
| `npm:` | `"npm:typescript"` |
| `go:` | `"go:golang.org/x/tools/gopls"` |
| `pipx:` | `"pipx:black"` |
| `gem:` | `"gem:solargraph"` |
| `asdf:` | `"asdf:mise-plugins/mise-tmux"` |

---

## Cross-References

- **AGENTS.md** - Operational procedures for AI agents
  - Adding tools (SKILL: Extend)
  - Troubleshooting (SKILL: Debug)
  - Updating (SKILL: Maintain)

- **CHEZMOI.md** - Dotfile management
  - How config files are applied
  - Template syntax
  - Managing mise configs through chezmoi

- **TROUBLESHOOTING.md** - Problem-solving guide
  - Platform-specific issues
  - Integration problems
  - Recovery procedures

---

## Document Information

**Purpose**: Complete reference for mise tool management
**Target audience**: AI agents and users
**Maintenance**: Update when adding new tools or changing configurations
**Version control**: Changes tracked in repository

For the latest tool inventory, always check `home/dot_config/mise/config.toml` in the repository.
