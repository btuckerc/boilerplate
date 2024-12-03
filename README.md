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
├── LICENSE                     # 
├── README.md                   # 
├── applications-list.md        # 
├── bash_profile                # Shell profile
├── bashrc                      # Shell configuration
├── config                      # Configuration files
│   ├── .vscode/                # VSCode settings
│   │   ├── settings.json       # 
│   │   └── snippets/           # 
│   ├── alacritty-config        # 
│   ├── catppuccin-mocha.toml   # 
│   └── starship.toml           # 
├── init-project                # 
├── lexicon.md                  # Command reference and tips
├── setup                       # Environment setup scripts
│   ├── setup-go                # Go environment setup
│   └── setup-py                # Python environment setup
├── setup-git                   # Git configuration
├── setup-supabase              # Supabase configuration
├── setup-tailwind              # Tailwind CSS setup
├── setup-tailwind-beta         # Tailwind CSS beta setup
├── templates                   # Project templates
│   ├── go                      # Go project templates
│   │   ├── README.md           # 
│   │   └── main.go             # 
│   └── python                  # Python project templates
│       ├── README.md           # 
│       └── requirements.txt    # 
├── utils                       # Utility scripts
│   ├── common.sh               # Shared shell functions
│   ├── readme.sh               # README generator
│   └── tree.sh                 # Directory tree generator
├── vimrc                       # 
└── vscode-shortcuts.pdf        # 
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

# Set up Tailwind CSS
./setup-tailwind
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
