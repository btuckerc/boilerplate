# Workspace Boilerplate

A comprehensive collection of scripts and configurations for setting up and managing development environments. Features project initialization, environment setup, and configuration management.

## Quick Start

Initialize your macOS development environment:
```bash
# Clone repository with submodules
git clone --recursive https://github.com/YOUR_USERNAME/boilerplate.git

# Or if already cloned, initialize submodules
git submodule update --init --recursive

# Run setup script
./utils/init-mac
```

Set up development tools:
```bash
./setup/setup-py
./init-project my-project
./utils/readme.sh
```

## Directory Structure

```
.
├── LICENSE                                    # MIT License
├── README.md                                  # This file
├── applications-list.md                       # List of recommended applications
├── bash_aliases                               # Bash aliases
├── bash_profile                               # Bash profile configuration
├── bashrc                                     # Bash shell configuration
├── zsh_aliases                                # Zsh aliases
├── zprofile                                   # Zsh profile configuration
├── zshrc                                      # Zsh shell configuration
├── config                                     # Configuration files
│   ├── .vscode/                               # VSCode configuration
│   │   ├── settings.json                      # Editor settings
│   │   └── snippets/                          # Code snippets
│   ├── kitty/                                 # Kitty configuration
│   │   └── kitty.conf                         # Kitty terminal config
│   ├── tmux/                                  # Tmux configuration
│   │   └── plugins/                           # Tmux plugins
│   │       └── tpm/                           # Tmux Plugin Manager (submodule)
│   ├── alacritty-config                       # Alacritty terminal config
│   ├── catppuccin-mocha.conf                  # Catppuccin theme for terminals
│   ├── catppuccin-mocha.toml                  # Catppuccin theme config
│   ├── nord.conf                              # Nord theme for terminals
│   └── starship.toml                          # Starship prompt config
├── init-project                               # Project initialization script
├── lexicon.md                                 # Command reference guide
├── nvim                                       # Neovim configuration
├── setup                                      # Environment setup scripts
│   ├── setup-go                               # Go environment setup
│   ├── setup-py                               # Python environment setup
│   ├── setup-git                              # Git configuration setup
│   ├── setup-kitty                            # Kitty terminal setup
│   ├── setup-supabase                         # Supabase environment setup
│   └── setup-tailwind                         # Tailwind CSS setup
├── templates                                  # Project templates
│   ├── go                                     # Go project template
│   └── python                                 # Python project template
├── utils                                      # Utility scripts
│   ├── common.sh                              # Common shell functions
│   ├── convert-kitty-theme-nvim.sh            # Theme converter
│   ├── fonts                                  # Custom font files
│   │   ├── MesloLGLNerdFont-Bold.ttf          # Meslo Nerd Font Bold
│   │   ├── MesloLGLNerdFont-BoldItalic.ttf    # Meslo Nerd Font Bold Italic
│   │   ├── MesloLGLNerdFont-Italic.ttf        # Meslo Nerd Font Italic
│   │   └── MesloLGLNerdFont-Regular.ttf       # Meslo Nerd Font Regular
│   ├── init-mac                               # macOS environment setup
│   ├── readme.sh                              # README generator
│   └── tree.sh                                # Directory tree generator
└── vscode-shortcuts.pdf                       # VSCode keyboard shortcuts
```

## Features

### macOS Environment Setup
```bash
# Complete environment setup
./utils/init-mac

# Setup with specific shell
./utils/init-mac -s zsh

# Skip Kitty terminal installation
./utils/init-mac -k

# Skip Homebrew installation
./utils/init-mac -b
```

The `init-mac` script sets up:
- Shell configuration (Bash or Zsh)
- Homebrew package manager
- Kitty terminal with themes
- Custom Meslo Nerd Fonts
- Neovim editor with configuration
- Tmux with configuration
- Development environment

### Shell Configuration
Support for both Bash and Zsh:
```bash
# Bash configuration
ln -s $(pwd)/bashrc ~/.bashrc
ln -s $(pwd)/bash_profile ~/.bash_profile
ln -s $(pwd)/bash_aliases ~/.bash_aliases

# Zsh configuration
ln -s $(pwd)/zshrc ~/.zshrc
ln -s $(pwd)/zprofile ~/.zprofile
ln -s $(pwd)/zsh_aliases ~/.zsh_aliases
```

### Project Initialization
```bash
# Create a new Python project
./init-project my-project

# Create a new Go project
./init-project -l go my-project

# Initialize in current directory
./init-project --lang python

# Specify Python version
./init-project my-project -v 3.11
```

### Environment Setup
```bash
# Set up Python environment
./setup/setup-py [--version 3.13]

# Set up Go environment
./setup/setup-go

# Set up Git configuration
./setup-git

# Set up Kitty terminal
./setup-kitty

# Set up Tailwind CSS
./setup-tailwind

# Set up Supabase
./setup-supabase
```

### Utility Scripts

#### Directory Tree Generation
```bash
./utils/tree.sh [-p] [-d DEPTH] [-e EXCLUDE]
```

#### README Generation
```bash
./utils/readme.sh [DIRECTORY] [-f]
```

#### Theme Conversion
```bash
./utils/convert-kitty-theme-nvim.sh input.conf output.lua
```

### Project Templates

#### Python Template
- Project structure
- Virtual environment setup
- Testing configuration
- README template
- Requirements management

#### Go Template
- Standard layout
- Go modules
- Basic main package
- Test setup
- Makefile

### Editor Configuration

#### Neovim Configuration
Modern setup with:
- LSP support (Mason)
- Treesitter
- Telescope
- Git integration
- Copilot
- Custom themes
- Completion (nvim-cmp)

#### VSCode Configuration
- Optimized settings
- Custom snippets
- Keyboard shortcuts
- Recommended extensions

### Terminal Configuration
- Kitty terminal setup
- Multiple themes
- Alacritty config
- Starship prompt
- Tmux configuration with TPM (Tmux Plugin Manager)
  - Automatic plugin installation
  - Sensible defaults
  - Session management (resurrect & continuum)
  - System clipboard integration (yank)

## Development

### Prerequisites
- macOS (primary support)
- Git
- Bash 3.2+ or Zsh

### Installation

1. Clone the repository with submodules:
```bash
git clone --recursive https://github.com/YOUR_USERNAME/boilerplate.git
```

2. If you've already cloned the repository, initialize submodules:
```bash
git submodule update --init --recursive
```

3. Run the setup script:
```bash
./utils/init-mac
```

### Submodules
This repository uses Git submodules for certain components:
- TPM (Tmux Plugin Manager) - `config/tmux/plugins/tpm`

To update submodules to their latest versions:
```bash
git submodule update --remote
```

### Contributing
1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Open Pull Request

### Adding New Scripts
1. Follow naming convention
2. Add license header
3. Include documentation
4. Update README
5. Update lexicon.md

## License

MIT License - See LICENSE file for details
