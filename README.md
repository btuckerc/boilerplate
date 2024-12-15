# Workspace Boilerplate

A comprehensive collection of scripts and configurations for setting up and managing development environments. Features project initialization, environment setup, and configuration management.

## Quick Start

```bash
# Set up Python environment
./setup/setup-py

# Create a new Python project
./init-project my-project

# Generate a README
./utils/readme.sh
```

## Directory Structure

```
.
├── LICENSE                                    # MIT License
├── README.md                                  # This file
├── applications-list.md                       # 
├── bash_aliases                               # Bash aliases
├── bash_profile                               # Shell profile
├── bashrc                                     # Shell config
├── config                                     # Config files
│   ├── .vscode/                               # 
│   │   ├── settings.json                      # 
│   │   └── snippets/                          # 
│   ├── alacritty-config                       # 
│   ├── catppuccin-mocha.conf                  # 
│   ├── catppuccin-mocha.toml                  # 
│   ├── kitty.conf                             # 
│   ├── nord.conf                              # 
│   └── starship.toml                          # 
├── init-project                               # Project init script
├── lexicon.md                                 # Command reference
├── nvim                                       # nvim config
│   ├── init.lua                               # 
│   ├── lazy-lock.json                         # 
│   └── lua                                    # 
│       └── tucker                             # 
│           ├── core                           # 
│           │   ├── init.lua                   # 
│           │   ├── keymaps.lua                # 
│           │   └── options.lua                # 
│           ├── lazy.lua                       # 
│           ├── plugins                        # 
│           │   ├── colorscheme.lua            # 
│           │   ├── init.lua                   # 
│           │   ├── lazygit.lua                # 
│           │   ├── linting.lua                # 
│           │   ├── lsp                        # 
│           │   │   ├── copilot.lua            # 
│           │   │   ├── lspconfig.lua          # 
│           │   │   ├── mason.lua              # 
│           │   │   └── undotree.lua           # 
│           │   ├── lualine.lua                # 
│           │   ├── mason-tool-installer.lua   # 
│           │   ├── nvim-cmp.lua               # 
│           │   ├── telescope.lua              # 
│           │   ├── treesitter.lua             # 
│           │   ├── trouble.lua                # 
│           │   ├── vimbegood.lua              # 
│           │   └── which-key.lua              # 
│           └── themes                         # 
│               └── adwaita_dark.lua           # 
├── setup                                      # env setups
│   ├── setup-go                               # install go
│   └── setup-py                               # install python
├── setup-git                                  # install git
├── setup-kitty                                # install kitty
├── setup-supabase                             # install supabase
├── setup-tailwind                             # install tailwind
├── setup-tailwind-beta                        # 
├── templates                                  # boilerplate
│   ├── go                                     # 
│   │   ├── README.md                          # 
│   │   └── main.go                            # 
│   └── python                                 # 
│       ├── README.md                          # 
│       └── requirements.txt                   # 
├── utils                                      # util scripts
│   ├── common.sh                              # 
│   ├── convert-kitty-theme-nvim.sh            # 
│   ├── readme.sh                              # 
│   └── tree.sh                                # 
└── vscode-shortcuts.pdf                       # shortcuts
```

## Features

### Project Initialization
```bash
# Create a new Python project
./init-project my-project

# Create a new Go project
./init-project -l go my-project

# Initialize in current directory
./init-project --lang python
```

### Environment Setup
```bash
# Set up Python environment (interactive version selection)
./setup/setup-py

# Set up specific Python version
./setup/setup-py --version 3.13

# Set up Go environment
./setup/setup-go

# Set up Git configuration (supports SSH/HTTPS)
./setup-git

# Set up Kitty terminal with themes
./setup-kitty

# Set up Tailwind CSS (stable)
./setup-tailwind

# Set up Tailwind CSS (beta features)
./setup-tailwind-beta

# Set up Supabase development environment
./setup-supabase
```

### Utility Scripts

#### Directory Tree Generation
```bash
# Generate basic tree
./utils/tree.sh

# Add comment placeholders (aligned)
./utils/tree.sh -p

# Limit depth
./utils/tree.sh -d 2

# Exclude patterns
./utils/tree.sh -e "node_modules"
```

#### README Generation
```bash
# Generate README in current directory
./utils/readme.sh

# Generate for specific directory
./utils/readme.sh ~/projects/app

# Force overwrite existing README
./utils/readme.sh -f
```

#### Theme Conversion
```bash
# Convert Kitty terminal theme to Neovim theme
./utils/convert-kitty-theme-nvim.sh input.conf output.lua

# Convert included themes
./utils/convert-kitty-theme-nvim.sh config/catppuccin-mocha.conf nvim/lua/tucker/themes/catppuccin.lua
./utils/convert-kitty-theme-nvim.sh config/nord.conf nvim/lua/tucker/themes/nord.lua
```

### Project Templates
The `templates/` directory contains starter templates for various languages:

#### Python Template
- Basic project structure
- `requirements.txt` with common dependencies
- Pre-configured virtual environment
- Testing setup with pytest
- README template with badges

#### Go Template
- Standard Go project layout
- Go modules initialization
- Basic main package
- Example test file
- Makefile for common operations
- README template with badges

### Editor Configuration

#### Neovim Configuration
The `nvim/` directory contains a modern Neovim configuration:
- LSP support with Mason
- Treesitter for syntax highlighting
- Telescope for fuzzy finding
- Custom keymaps and options
- Multiple theme support
- Git integration with Lazygit
- Copilot integration
- Completion with nvim-cmp

#### VSCode Configuration
The `config/.vscode/` directory includes:
- Optimized settings.json
- Custom snippets
- Recommended extensions
- Keyboard shortcuts (see vscode-shortcuts.pdf)

### Terminal Configuration
The `config/` directory includes:
- Kitty terminal configuration
- Multiple theme options (Catppuccin Mocha, Nord)
- Alacritty configuration
- Starship prompt customization

## Configuration

### Editor and Terminal
The `config/` directory contains various configuration files:
- VSCode settings and snippets
- Alacritty terminal configuration
- Starship prompt configuration
- Catppuccin Mocha theme

### Shell Configuration
Shell configuration files should be symlinked to your home directory:
```bash
# Link shell configurations
ln -s $(pwd)/bashrc ~/.bashrc
ln -s $(pwd)/bash_profile ~/.bash_profile

# Reload shell configuration
source ~/.bashrc
```

## Command Reference

The `lexicon.md` file contains a comprehensive guide for:
- Essential command-line tools and usage
- Shell navigation shortcuts
- Vim commands and tips
- Screen/Tmux terminal multiplexing
- Time and scheduling (cron and launchd)
- macOS-specific commands and tools
- Advanced shell operators
- Git operations and workflows

Key sections include:
- **Command Line Basics**: Pipes, redirections, and operators
- **Essential Commands**: grep, find, sed, and more
- **Time Management**: Cron format, scheduling, and macOS launchd
- **Shell Navigation**: Keyboard shortcuts and efficiency tips
- **Git Workflows**: Common operations and best practices
- **macOS Specifics**: System commands and Homebrew management

View it with:
```bash
# Using cat
cat lexicon.md

# Using VSCode
code lexicon.md

# Using your default Markdown viewer
open lexicon.md  # on macOS
```

## Development

### Prerequisites
- macOS (primary support)
- Homebrew (will be installed if missing)
- Git (will be installed if missing)
- Bash 3.2+ (default on macOS)

### Contributing
1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Adding New Scripts
When adding new scripts:
1. Follow the naming convention (setup-* for environment setup, init-* for initialization)
2. Add MIT license header
3. Include usage documentation
4. Update README.md
5. Consider adding relevant tips to lexicon.md

## License

MIT License - Feel free to use and modify as needed.
