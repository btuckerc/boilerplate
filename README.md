# Cross-Platform Dotfiles

Modern, portable dotfiles managed with [chezmoi](https://chezmoi.io) and [mise](https://mise.jdx.dev), supporting macOS and Linux with machine-specific templates where needed.

## Features

- **Cross-platform**: macOS (zsh) and Linux (bash) support with shared configuration
- **Tool management**: mise installs and manages all required tools automatically
- **Agentic coding**: Oh My Pi (OMP) is the pinned, primary terminal harness across platforms
- **Automated setup**: One command to bootstrap everything
- **Idempotent**: Safe to run repeatedly
- **OS-aware templates**: Platform-specific configurations where needed
- **No duplication**: Shared POSIX shell configuration sourced by all shells
- **Optional packages**: Brewfile available for additional tools (not required)

## Quick Start

### Preferred Bootstrap

```bash
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply btuckerc/boilerplate
```

That uses chezmoi's official installer and applies this repo in one step.

If you already cloned the repo locally:

```bash
git clone https://github.com/btuckerc/boilerplate.git
cd boilerplate
./setup
```

That's it. The bootstrap path will:
1. Install `chezmoi` if needed
2. Apply dotfiles from this repo or your local checkout
3. Run the OS-specific one-time setup hooks
4. Install mise-managed tools automatically

It does not force a shell change.

### SuperGrok Login

OMP configuration is shared, but xAI OAuth credentials stay local to each machine. After bootstrap, authenticate the native SuperGrok provider once per workstation:

```bash
omp auth-broker login xai-oauth
omp models refresh
omp usage --provider xai-oauth --redact
```

The default model roles use `xai-oauth/grok-4.6`.

### Manual Setup

```bash
# Remote repo
chezmoi init --apply https://github.com/btuckerc/boilerplate.git

# Or if you cloned this repo locally
cd /path/to/boilerplate
chezmoi init --source="$(pwd)" --apply

# Install all mise-managed tools
mise install
```

## Documentation

This repository includes comprehensive documentation:

### For AI Agents and Advanced Users

The active terminal baseline is OMP-first. Its private native configuration and shared skills live under `home/private_dot_omp/private_agent/`.

- **[OMP Config](./home/private_dot_omp/private_agent/skills/omp-config/SKILL.md)** - Update the shared OMP baseline managed by chezmoi
- **[Platform Ops](./home/private_dot_omp/private_agent/skills/platform-ops/SKILL.md.tmpl)** - Inspect or change platform-local settings on Omarchy/Linux or macOS
- **[OPNsense](./home/private_dot_omp/private_agent/skills/opnsense/SKILL.md)** - Manage the home OPNsense router over its REST API

### For Users

- **[README.md](./README.md)** (this file) - Getting started and overview
- **[llms.txt](./llms.txt)** - LLM-friendly repository overview

### Reference (Optional)

- **[LICENSE](./LICENSE)** - MIT License

For most users, this README covers what you need. Legacy Claude/OpenCode files were archived to the `legacy/claude-opencode` branch, and the pre-OMP Pi/Codex CLI baseline remains available in Git history.

### What Gets Installed Automatically

mise will automatically install these essential tools:
- **omp** - Oh My Pi terminal coding harness
- **chezmoi** - Dotfile manager
- **starship** - Cross-shell prompt
- **fzf** - Fuzzy finder
- **ripgrep** - Fast search
- **bat** - Cat with syntax highlighting
- **eza** - Modern ls replacement
- **fd** - Fast find alternative
- **yazi** - Terminal file manager
- **node** - Node.js (LTS)
- **python** - Python 3.13
- **go** - Go 1.25

## Configuration Included

### Shell Configuration
- **Shared config**: `~/.config/shell/common.sh` - POSIX-compatible configuration
- **Zsh**: `~/.zshrc`, `~/.zprofile`, `~/.zshenv` with macOS-specific enhancements
- **Bash**: `~/.bashrc`, `~/.bash_profile` with Linux compatibility
- **Starship**: Modern, minimal prompt
- **Git**: `~/.gitconfig` with aliases and sensible defaults

### Editor Configurations
- **Neovim**: Neovim 0.12 with native LSP/completion, Treesitter, Telescope, Oil, and lazy.nvim
- **VSCode**: Settings and custom snippets
- **tmux**: With TPM (Tmux Plugin Manager) and sensible defaults

### Optional: Additional Packages (Brewfile)

A `Brewfile` is included for additional packages you may want:
- GUI apps: Ghostty
- CLI tools: btop, tmux, gh, jq, lazygit
- Fonts used by the shared macOS configs: BlexMono Nerd Font, Meslo LG Nerd Font, Source Code Pro, Symbols Nerd Font

To install Brewfile packages (optional):
```bash
brew bundle install --file=~/Brewfile
# Or from the repo
brew bundle install --file=~/.local/share/chezmoi/home/Brewfile
```

**Note**: Brewfile is NOT automatically installed. Essential CLI tools come from mise.

## Directory Structure

```
.
├── setup                           # Bootstrap script (main entry point)
├── .chezmoiroot                    # Points chezmoi to home/ directory
├── home/                           # chezmoi source directory
│   ├── .chezmoiignore              # Files to exclude from home directory
│   ├── Brewfile                    # Optional Homebrew packages → ~/Brewfile
│   ├── dot_gitconfig               # Git configuration
│   ├── dot_zshrc.tmpl              # Zsh configuration (OS-aware)
│   ├── dot_bashrc.tmpl             # Bash configuration (OS-aware)
│   ├── dot_bash_profile.tmpl       # Bash profile
│   ├── dot_zprofile.tmpl           # Zsh profile
│   ├── dot_zshenv                  # Zsh environment variables
│   ├── dot_config/                 # XDG config directory
│   │   ├── shell/
│   │   │   └── common.sh           # Shared POSIX shell configuration
│   │   ├── mise/
│   │   │   └── config.toml         # Tool management (primary)
│   │   ├── nvim/                   # Neovim configuration
│   │   ├── tmux/                   # Tmux configuration
│   │   ├── kitty/                  # Kitty terminal config
│   │   ├── ghostty/                # Ghostty terminal config
│   │   ├── starship/               # Starship prompt config
│   │   ├── yazi/                   # Yazi file manager config
│   │   ├── btop/                   # btop system monitor config
│   │   └── vscode/                 # VSCode settings & snippets
│   ├── dot_local/bin/              # Local executables
│   └── run_once_before_01-install-prereqs.sh.tmpl
├── templates/                      # Project templates
│   ├── go/                         # Go project template
│   └── python/                     # Python project template
└── utils/                          # Utility scripts
    ├── init-mac                    # Legacy macOS setup script
    ├── init-project                # Project initialization
    ├── fonts/                      # Nerd Fonts
    └── scripts/                    # Helper scripts
```

## Usage

### Managing Dotfiles

```bash
# Edit a dotfile (opens in $EDITOR)
chezmoi edit ~/.zshrc

# See what would change
chezmoi diff

# Apply changes
chezmoi apply

# Apply specific file
chezmoi apply ~/.zshrc

# Add new file to chezmoi
chezmoi add ~/.gitconfig

# Update from remote repository
chezmoi update
```

### macOS Performance Audit

On macOS hosts, the shared dotfiles also install a local audit helper:

```bash
macos-performance-audit
```

It summarizes storage pressure, large cache and media directories, Docker disk usage, simulator and Xcode support files, login items, launch agents, and Homebrew services without deleting anything.

### Managing Tool Versions

```bash
# Install all tools defined in mise config
mise install

# Install specific tool
mise install node@20

# See installed tools
mise list

# Add tool to global config
mise use --global node@lts python@3.12

# See available versions
mise ls-remote node
```

### Optional Tools

Some tools are not installed by default. On first `mise install`, you'll be prompted:

```bash
$ mise install

Optional tools:
  1) ubi:mikefarah/yq                  YAML processor
  2) aqua:hashicorp/packer             Image builder

a) All  s) Select  n) None [N]
>
```

- **a** = Install all optional tools
- **s** = Select specific tools interactively
- **n** or Enter = Skip (default)

Your choices are saved locally (gitignored). Edit `~/.config/mise/config.optional.toml` to add more optional tools.

### Managing Packages

**mise** (primary tool manager):
```bash
mise install
```

**Brewfile** (supplementary packages):
```bash
# Interactive install with optional packages prompt
brew-bundle-optional

# Or standard install (no optional packages)
brew bundle --file=~/Brewfile
```

## How It Works

### chezmoi Templates

Files ending in `.tmpl` are processed as Go templates, allowing OS-specific configuration:

```go
{{- if eq .chezmoi.os "darwin" -}}
# macOS-specific configuration
eval "$(/opt/homebrew/bin/brew shellenv)"
{{- else if eq .chezmoi.os "linux" -}}
# Linux-specific configuration
alias ls='ls --color=auto'
{{- end -}}
```

### Shared Shell Configuration

To avoid duplicating shell configuration between bash and zsh, common functionality lives in `~/.config/shell/common.sh`:

- Environment variables
- Aliases
- Functions
- Tool activation (mise, etc.)

Both `~/.zshrc` and `~/.bashrc` source this file, then add shell-specific features.

### Tool Installation

All essential tools are managed by **mise** and installed automatically when you run:
```bash
mise install
```

mise reads `~/.config/mise/config.toml` and installs all defined tools. Tools are installed to `~/.local/share/mise/installs/` and automatically added to your PATH.

No manual installation required!

## Cross-Platform Support

### macOS (zsh)
- Homebrew integration
- Kitty/Ghostty shell integration
- macOS-specific aliases and functions
- zsh-specific features (completion, history)

### Linux (bash)
- apt/yum package manager support (if needed)
- GNU coreutils aliases
- bash-specific features
- Works on Debian, Ubuntu, Fedora, etc.

## Customization

### Add Your Own Dotfiles

```bash
# Add existing dotfile
chezmoi add ~/.gitconfig

# Edit in chezmoi
chezmoi edit ~/.gitconfig

# Apply changes
chezmoi apply
```

### Modify Existing Configuration

```bash
# Edit shared shell config
chezmoi edit ~/.config/shell/common.sh

# Edit OS-specific shell config
chezmoi edit ~/.zshrc  # or ~/.bashrc

# Preview changes
chezmoi diff

# Apply
chezmoi apply
```

### Add Tools to mise

```bash
# Edit mise config
chezmoi edit ~/.config/mise/config.toml

# Add tool
mise use --global rust@latest

# Commit back to chezmoi
chezmoi add ~/.config/mise/config.toml
```

## Neovim Configuration

Full-featured Neovim setup with:
- **Neovim**: Pinned via `mise` to 0.12.x
- **LSP**: Native `vim.lsp.config()` / `vim.lsp.enable()` with mise-managed servers
- **Treesitter**: Advanced syntax highlighting
- **Completion**: Native `vim.lsp.completion`
- **Navigation**: Telescope + Oil
- **Git**: gitsigns + LazyGit integration
- **AI**: OMP-first workflow outside the editor; no Neovim AI plugin enabled by default
- **Theme**: Custom colorscheme synced with terminal

Configuration location: `~/.config/nvim/`

Plugin organization:
```
lua/plugins/
├── lsp.lua          # LSP and completion
├── editor.lua       # Core editing features
├── navigation.lua   # File/code navigation
├── ui.lua           # Visual elements
├── git.lua          # Git integration
└── integrations.lua # External tools
```

## Tmux Configuration

Modern tmux setup with:
- **TPM**: Tmux Plugin Manager (installed as git submodule)
- **Plugins**: sensible, resurrect, continuum, yank
- **Prefix**: `` ` `` (backtick)
- **Vim navigation**: C-h/j/k/l for pane switching
- **Theme**: Minimal, Nord-inspired colors
- **Mouse support**: Enabled

Configuration: `~/.config/tmux/tmux.conf`

## Project Templates

### Python Project

```bash
./utils/init-project my-python-project
```

Creates:
- Virtual environment setup
- `requirements.txt`
- Testing structure
- README template
- `.gitignore`

### Go Project

```bash
./utils/init-project -l go my-go-project
```

Creates:
- Go modules setup
- `main.go`
- Standard project layout
- Makefile
- README template

## Troubleshooting

For detailed troubleshooting steps and solutions to common errors, see **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)**.

Quick fixes for common issues:

### chezmoi Issues

```bash
# Verify chezmoi state
chezmoi doctor

# See what chezmoi would apply
chezmoi diff

# Force apply (overwrites local changes)
chezmoi apply --force

# Reset to repository state
chezmoi update --force
```

### mise Issues

**Quick fix**: Run the automated fixer:
```bash
./utils/scripts/fix-mise.sh
```

Common issues and manual fixes:

```bash
# Diagnose mise setup
mise doctor

# Ruby build failure (python not found)
mkdir -p ~/.local/share/mise/shims
ln -sf $(which python3) ~/.local/share/mise/shims/python
export PATH="$HOME/.local/share/mise/shims:$PATH"

# Network/timeout issues - install sequentially
MISE_JOBS=1 mise install

# Verbose logging for debugging
MISE_VERBOSE=1 mise install 2>&1 | tee ~/mise-install.log

# Clear cache and retry
rm -rf ~/.cache/mise
mise install

# Reinstall specific tool
mise uninstall node@22
mise install node@22
```

**See detailed troubleshooting**: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

### Shell Not Loading Configuration

```bash
# Check if shell sources the right files
echo $SHELL

# Reload shell configuration
source ~/.zshrc  # or ~/.bashrc

# Check for errors in shell config
zsh -x  # or bash -x
```

## Updating

For detailed update procedures and maintenance schedules, see **[UPDATING.md](./UPDATING.md)**.

Quick update commands:

```bash
# Update dotfiles from repository
chezmoi update

# Update Homebrew packages
brew update && brew upgrade

# Update mise tools
mise upgrade
```

## Migration from Old Setup

If you previously used manual symlinks or GNU Stow:

1. **Backup existing dotfiles**: `tar czf ~/dotfiles-backup.tar.gz ~/.*rc ~/.*profile`
2. **Remove old symlinks**: `rm ~/.zshrc ~/.bashrc` (etc.)
3. **Initialize chezmoi**: `chezmoi init --apply`
4. **Verify everything works**: Test shell, tmux, nvim
5. **Clean up**: Remove old dotfile repositories after confirming

## Resources

- [chezmoi Documentation](https://chezmoi.io/)
- [mise Documentation](https://mise.jdx.dev/)
- [Neovim Configuration](./home/dot_config/nvim/)
- [Tmux Plugin Manager](https://github.com/tmux-plugins/tpm)

## License

MIT License - See LICENSE file for details
