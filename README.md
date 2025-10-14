# Cross-Platform Dotfiles

Modern, portable dotfiles managed with [chezmoi](https://chezmoi.io) and [mise](https://mise.jdx.dev), supporting macOS (zsh) and Linux (bash).

## Features

- **Cross-platform**: macOS (zsh) and Linux (bash) support with shared configuration
- **Tool management**: mise installs and manages all required tools automatically
- **Automated setup**: One command to bootstrap everything
- **Idempotent**: Safe to run repeatedly
- **OS-aware templates**: Platform-specific configurations where needed
- **No duplication**: Shared POSIX shell configuration sourced by all shells
- **Optional packages**: Brewfile available for additional tools (not required)

## Quick Start

### One-Line Setup

```bash
curl -fsSL https://raw.githubusercontent.com/btuckerc/boilerplate/main/setup | bash
```

Or clone and run:

```bash
git clone https://github.com/btuckerc/boilerplate.git
cd boilerplate
./setup
```

That's it! The setup script will:
1. Set zsh as your default shell (if available)
2. Install chezmoi (via mise, brew, or direct download)
3. Apply all dotfiles to your home directory
4. Install mise-managed tools automatically (chezmoi, starship, fzf, ripgrep, bat, eza, fd, yazi, node, python, go)
5. Set up shell configuration

### Manual Setup

```bash
# If you already have chezmoi and mise installed
chezmoi init --apply https://github.com/btuckerc/boilerplate.git

# Or if you cloned this repo locally
cd /path/to/boilerplate
chezmoi init --source="$(pwd)" --apply

# Install all mise-managed tools
mise install
```

### What Gets Installed Automatically

mise will automatically install these essential tools:
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
- **Neovim**: Full LSP setup with plugins (Treesitter, Telescope, Copilot, etc.)
- **VSCode**: Settings and custom snippets
- **tmux**: With TPM (Tmux Plugin Manager) and sensible defaults

### Optional: Additional Packages (Brewfile)

A `Brewfile` is included for additional applications you may want:
- GUI apps: Docker, Ghostty, Kitty
- System tools: btop, tmux, gh, jq
- Development: Additional language tools

To install Brewfile packages (optional):
```bash
brew bundle install --file=~/Brewfile
# Or from the repo
brew bundle install --file=~/.local/share/chezmoi/Brewfile
```

**Note**: Brewfile is NOT automatically installed. Essential CLI tools come from mise.

## Directory Structure

```
.
├── setup                           # Bootstrap script (main entry point)
├── .chezmoiroot                    # Points chezmoi to home/ directory
├── Brewfile                        # Optional Homebrew packages
├── home/                           # chezmoi source directory
│   ├── .chezmoiignore              # Files to exclude from home directory
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

### Managing Packages

**mise** (primary tool manager):
```bash
# Install all tools from mise config
mise install

# Add a new tool globally
mise use --global ripgrep@latest

# Update mise config
chezmoi edit ~/.config/mise/config.toml
chezmoi apply
```

**Brewfile** (optional supplementary packages):
```bash
# Install packages from Brewfile (optional)
brew bundle install --file=~/.local/share/chezmoi/Brewfile

# Update Brewfile with currently installed packages
cd ~/.local/share/chezmoi
brew bundle dump --force --file=Brewfile
chezmoi add Brewfile
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
- **LSP**: Language Server Protocol support via Mason
- **Treesitter**: Advanced syntax highlighting
- **Telescope**: Fuzzy finder for files, grep, buffers
- **Git**: fugitive, gitsigns integration
- **Copilot**: AI pair programming
- **Completion**: nvim-cmp with multiple sources
- **File navigation**: oil.nvim, harpoon
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
├── ai.lua           # Copilot
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

```bash
# Diagnose mise setup
mise doctor

# Reinstall tool
mise uninstall node@22
mise install node@22

# Clear cache
rm -rf ~/.cache/mise
```

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
