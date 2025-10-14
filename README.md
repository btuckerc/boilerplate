# Cross-Platform Dotfiles

Modern, portable dotfiles managed with [chezmoi](https://chezmoi.io) and [mise](https://mise.jdx.dev), supporting macOS (zsh) and Linux (bash).

## Features

- **Cross-platform**: macOS (zsh) and Linux (bash) support with shared configuration
- **Declarative package management**: Brewfile for reproducible Homebrew setups
- **Version management**: mise for language runtime versions (node, python, go)
- **Automated setup**: One command to apply all configurations
- **Idempotent**: Safe to run repeatedly
- **OS-aware templates**: Platform-specific configurations where needed
- **No duplication**: Shared POSIX shell configuration sourced by all shells

## Quick Start

### Prerequisites

```bash
# macOS
xcode-select --install

# Install chezmoi and mise
brew install chezmoi mise
```

### Install Dotfiles

```bash
# Initialize chezmoi with this repository
chezmoi init --apply https://github.com/btuckerc/boilerplate.git
```

That's it! This will:
1. Clone the repository to `~/.local/share/chezmoi`
2. Install Homebrew packages from Brewfile
3. Apply all dotfiles to your home directory
4. Install mise-managed tools (node, python, go)
5. Set up shell configuration

### Manual Setup (if you already have the repo)

```bash
# If you already cloned this repo locally
cd /path/to/boilerplate

# Initialize chezmoi pointing to this directory
chezmoi init --source="$(pwd)"

# Preview what would be applied (dry run)
chezmoi diff

# Apply dotfiles
chezmoi apply

# Install mise-managed tools
mise install
```

## What Gets Installed

### Shell Configuration
- **Shared config**: `~/.config/shell/common.sh` - POSIX-compatible configuration
- **Zsh**: `~/.zshrc`, `~/.zprofile`, `~/.zshenv` with macOS-specific enhancements
- **Bash**: `~/.bashrc`, `~/.bash_profile` with Linux compatibility
- **Starship**: Modern, minimal prompt configuration

### Tool Versions (via mise)
- **Node.js**: LTS version
- **Python**: 3.13
- **Go**: 1.25

### Applications (via Brewfile)
- Terminal: kitty, ghostty, tmux, starship
- Editors: neovim (with full configuration)
- CLI tools: yazi, btop, fzf, ripgrep, bat, eza, and more
- Development: git, gh, docker, mise, chezmoi

### Editor Configurations
- **Neovim**: Full LSP setup with plugins (Treesitter, Telescope, Copilot, etc.)
- **VSCode**: Settings and custom snippets
- **tmux**: With TPM (Tmux Plugin Manager) and sensible defaults

## Directory Structure

```
.
├── .chezmoiroot                    # Points chezmoi to home/ directory
├── Brewfile                        # Homebrew packages (also in home/)
├── home/                           # chezmoi source directory
│   ├── .chezmoiignore              # Files to exclude from home directory
│   ├── dot_zshrc.tmpl              # Zsh configuration (OS-aware)
│   ├── dot_bashrc.tmpl             # Bash configuration (OS-aware)
│   ├── dot_bash_profile.tmpl       # Bash profile
│   ├── dot_zprofile.tmpl           # Zsh profile
│   ├── dot_zshenv                  # Zsh environment variables
│   ├── dot_config/                 # XDG config directory
│   │   ├── shell/
│   │   │   └── common.sh           # Shared POSIX shell configuration
│   │   ├── mise/
│   │   │   └── config.toml         # Tool version management
│   │   ├── nvim/                   # Neovim configuration
│   │   ├── tmux/                   # Tmux configuration
│   │   ├── kitty/                  # Kitty terminal config
│   │   ├── ghostty/                # Ghostty terminal config
│   │   ├── starship/               # Starship prompt config
│   │   ├── yazi/                   # Yazi file manager config
│   │   ├── btop/                   # btop system monitor config
│   │   └── vscode/                 # VSCode settings & snippets
│   ├── dot_local/bin/              # Local executables
│   ├── run_once_before_01-install-prereqs.sh.tmpl
│   ├── run_onchange_before_02-install-packages-darwin.sh.tmpl
│   └── run_onchange_before_03-install-packages-linux.sh.tmpl
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

```bash
# Install/update packages from Brewfile
brew bundle install --file=~/Brewfile

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

### Automated Scripts

- **run_once**: Executes once (tracked by chezmoi state)
- **run_onchange**: Executes when file content changes
- **before**: Runs before applying dotfiles

Example: `run_onchange_before_02-install-packages-darwin.sh.tmpl` runs when Brewfile changes, ensuring packages stay up-to-date.

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
