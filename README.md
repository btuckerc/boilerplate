# Workspace Boilerplate

A comprehensive collection of scripts and configurations for setting up and managing development environments. Features project initialization, environment setup, and configuration management.

## Quick Start

One-liner to get started (works even without git installed):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/btuckerc/boilerplate/main/utils/scripts/bootstrap.sh)"
```

Or if you already have git, you can clone and run directly:
```bash
git clone https://github.com/btuckerc/boilerplate.git && cd boilerplate && ./utils/init-mac
```

There are other setup tools you can explore as well:
```bash
./setup/setup-vscode
./utils/init-project my-project
./utils/scripts/readme.sh
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
│   ├── kitty/                                 # Kitty configuration
│   │   ├── kitty.conf                         # Kitty terminal config
│   │   └── current-theme.conf                 # Current Kitty theme
│   ├── vscode/                                # VSCode configuration
│   │   ├── settings.json                      # Editor settings
│   │   ├── snippets/                          # Code snippets
│   │   └── extensions/                        # VSCode extensions
│   │       └── current-theme/                 # Current theme extension
│   └── tmux/                                  # Tmux configuration
│       └── plugins/                           # Tmux plugins
│           └── tpm/                           # Tmux Plugin Manager (submodule)
├── nvim                                       # Neovim configuration
│   └── lua/                                   # Lua configuration files
│       └── tucker/                            # Personal configuration
│           └── core/                          # Core configuration
│           └── plugins/                       # Plugin configuration
│           └── themes/                        # Theme files
│               └── current-theme.lua          # Current theme
├── setup                                      # Environment setup scripts
│   ├── setup-go.sh                            # Go environment setup
│   ├── setup-py.sh                            # Python environment setup
│   ├── setup-git.sh                           # Git configuration setup
│   ├── setup-kitty.sh                         # Kitty terminal setup
│   ├── setup-vscode.sh                        # VSCode setup
│   ├── setup-supabase.sh                      # Supabase environment setup
│   └── setup-tailwind.sh                      # Tailwind CSS setup
├── templates                                  # Project templates
│   ├── go                                     # Go project template
│   └── python                                 # Python project template
└── utils                                      # Utility scripts
    ├── init-mac                               # macOS environment setup
    ├── init-project                           # Project initialization
    ├── fonts                                  # Custom font files
    │   ├── MesloLGLNerdFont-Bold.ttf          # Meslo Nerd Font Bold
    │   ├── MesloLGLNerdFont-BoldItalic.ttf    # Meslo Nerd Font Bold Italic
    │   ├── MesloLGLNerdFont-Italic.ttf        # Meslo Nerd Font Italic
    │   └── MesloLGLNerdFont-Regular.ttf       # Meslo Nerd Font Regular
    └── scripts                                # Shell script utilities
        ├── common.sh                          # Common shell functions
        ├── convert-kitty-theme-nvim.sh        # Theme converter for Neovim
        ├── convert-kitty-theme-vscode.sh      # Theme converter for VSCode
        ├── fix-nvim-symlink.sh                # Neovim symlink fixer
        ├── readme.sh                          # README generator
        ├── tree.sh                            # Directory tree generator
        └── bash-to-zsh.sh                     # Shell conversion utility
```

## TODO
- [ ] make sure brew install glow
- [ ] make sure starship can be installed

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
./utils/scripts/tree.sh [-p] [-d DEPTH] [-e EXCLUDE]
```

#### README Generation
```bash
./utils/scripts/readme.sh [DIRECTORY] [-f]
```

#### Theme Conversion
```bash
./utils/scripts/convert-kitty-theme-nvim.sh input.conf output.lua
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

#### VSCode Configuration
- Optimized settings
- Custom snippets
- Keyboard shortcuts
- Recommended extensions
- Automatic theme conversion from Kitty themes
- Integrated theme extension management
- Symlinked configuration for version control
- Automatic backup of existing configurations
- User-specific theme publisher ID

```bash
# Set up VSCode configuration
./setup/setup-vscode.sh

# Features:
- Symlinks settings.json to repository
- Sets up custom theme extension
- Preserves existing extensions
- Creates backups of existing configs
- Manages theme conversion and updates
```

#### Theme Management
```bash
# Convert Kitty theme to VSCode theme
./utils/scripts/convert-kitty-theme-vscode.sh

# Features:
- Extracts colors from Kitty themes
- Generates VSCode-compatible theme files
- Creates proper extension structure
- Uses current user as publisher ID
- Sets up bidirectional symlinks
- Preserves existing themes
- Creates automatic backups
```

The theme conversion scripts automatically:
- Extract colors from Kitty themes
- Generate compatible theme files
- Set up proper symlinks for version control
- Install as VSCode extension (for VSCode themes)
- Update tab bar colors (for Neovim themes)
- Create backups of existing configurations
- Use system username as publisher ID
- Enable bidirectional editing (changes reflect in both locations)

#### Neovim Configuration
Modern setup with:
- LSP support (Mason)
- Treesitter
- Telescope
- Git integration
- Copilot
- Custom themes with Kitty theme sync
- Completion (nvim-cmp)

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

### yazi Setup
1. Install yazi
```bash
brew install yazi ffmpegthumbnailer ffmpeg sevenzip jq poppler fd ripgrep fzf zoxide imagemagick font-symbols-only-nerd-font
```

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

Update TPM after installation:
```bash
git submodule update --init --recursive
```

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
