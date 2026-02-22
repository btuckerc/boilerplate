# Codex CLI Configuration

This directory contains the chezmoi-managed configuration for OpenAI's Codex CLI.

## Overview

Codex CLI is OpenAI's coding agent that runs locally in your terminal. It can read, modify, and run code on your machine. This configuration is tracked in the dotfiles repository and can be pulled to remote machines via chezmoi.

## Directory Structure

```
~/.codex/
├── config.toml          # Main configuration (model, approval, features)
├── AGENTS.md            # Global instructions for Codex
├── skills/              # Skill definitions
│   └── codex-config/    # Configuration management skill
│       └── SKILL.md
└── auth.json            # Authentication (not tracked by chezmoi)
```

## Installation

Codex CLI is installed via mise. The tool is defined in `~/.config/mise/config.toml`:

```toml
"npm:@openai/codex" = "latest"
```

To install:

```bash
mise install
```

## Configuration

### Main Config (`config.toml`)

Key settings:
- **model**: Default model (e.g., `gpt-5-codex`)
- **approval_policy**: When to prompt for approval (`on-request`, `untrusted`, `never`)
- **sandbox_mode**: Filesystem access level (`workspace-write`, `read-only`, `danger-full-access`)
- **web_search**: Web search mode (`cached`, `live`, `disabled`)
- **model_reasoning_effort**: Reasoning depth (`minimal`, `low`, `medium`, `high`, `xhigh`)

### Global Instructions (`AGENTS.md`)

Persistent instructions that Codex reads before any work. Includes:
- Working agreements
- Code quality standards
- Safety boundaries
- Tool usage guidelines

### Skills

Specialized knowledge packages for specific tasks. Add new skills in the `skills/` directory.

## Usage

### Starting Codex

```bash
codex
```

First run will prompt for authentication. Sign in with your ChatGPT account (Pro subscription recommended).

### Common Commands

| Command | Description |
|---------|-------------|
| `codex` | Start interactive TUI |
| `codex "task"` | Run a single task |
| `codex --help` | Show help |
| `codex --model gpt-5.2` | Use specific model |
| `codex --search` | Enable live web search |

### Slash Commands (in TUI)

| Command | Description |
|---------|-------------|
| `/model` | Switch models |
| `/help` | Show help |
| `/review` | Run code review |
| `/undo` | Undo last change |
| `/clear` | Clear conversation |

## Making Changes

**Always edit the source files, not the live config:**

```bash
# Edit source
vim /Users/tucker/Documents/GitHub/boilerplate/home/dot_config/codex/config.toml

# Apply changes
chezmoi apply --force ~/.codex/

# Verify
cat ~/.codex/config.toml
```

## Documentation

- [Codex Documentation](https://developers.openai.com/codex)
- [Codex CLI Reference](https://developers.openai.com/codex/cli/reference)
- [Config Reference](https://developers.openai.com/codex/config-reference)
- [AGENTS.md Guide](https://developers.openai.com/codex/guides/agents-md)

## Related

- **opencode**: Alternative AI coding assistant (also configured in this dotfiles repo)
- **chezmoi**: Dotfile manager used to sync this configuration
- **mise**: Tool manager used to install Codex CLI