---
name: codex-config
description: Comprehensive guide for modifying Codex CLI configuration including models, agents, skills, and system settings. Covers both general Codex conventions and this machine's chezmoi-based dotfiles setup.
---

# Skill: Codex Configuration Management

A complete reference for modifying Codex settings on this machine, covering the chezmoi-managed dotfiles structure and Codex's configuration architecture.

## Quick Reference

| What you want to change | Where to edit | Applied via |
|------------------------|---------------|-------------|
| Main model, approval policy, features | `$(chezmoi source-path)/dot_codex/config.toml` | chezmoi apply |
| Global system instructions | `$(chezmoi source-path)/dot_codex/AGENTS.md` | chezmoi apply |
| Skills | `$(chezmoi source-path)/dot_codex/skills/` | chezmoi apply |
| Project-specific settings | `.codex/config.toml` in project root | Direct file (not chezmoi) |
| Authentication | Run `codex` and sign in | Stored in `~/.codex/auth.json` |

---

## Machine-Specific Context

### This Machine's Setup

This machine uses **chezmoi** to manage dotfiles from the source tree returned by `chezmoi source-path`.

**Key locations:**
- **Source (chezmoi):** `$(chezmoi source-path)/dot_codex/`
- **Live config:** `~/.codex/`
- **Credentials:** `~/.codex/auth.json` (managed by Codex, not chezmoi)

**Important:** Always edit files in the **source directory** (`$(chezmoi source-path)/...`) and run `chezmoi apply` to apply changes. Never edit files directly in `~/.codex/` as they will be overwritten.

### Workflow for Changes

```bash
# 1. Edit the source file
cd "$(chezmoi source-path)/dot_codex/"
# Edit config.toml, AGENTS.md, or create skills

# 2. Apply changes
chezmoi apply --force ~/.codex/

# 3. Verify
cat ~/.codex/config.toml
```

---

## Codex Configuration Architecture

### Configuration Precedence

Codex resolves values in this order (highest precedence first):

1. **CLI flags** and `--config` overrides
2. **Profile values** (from `--profile <name>`)
3. **Project config files:** `.codex/config.toml`, ordered from project root down to current working directory
4. **User config:** `~/.codex/config.toml`
5. **System config:** `/etc/codex/config.toml` (Unix)
6. **Built-in defaults**

### Current Configuration Structure

```
~/.codex/
├── config.toml          # Main config: model, approval, features
├── AGENTS.md            # Global instructions
├── skills/              # Skill definitions
│   └── codex-config/
│       └── SKILL.md
└── auth.json            # Authentication (not tracked)
```

---

## 1. Modifying Models

### Model Configuration Location

Models are configured in `config.toml` with the `model` key.

### Current Setup

```toml
model = "gpt-5-codex"
model_reasoning_effort = "high"
```

### Available Models

For OpenAI Pro subscribers:
- `gpt-5-codex` - Default coding model
- `gpt-5.2` - Latest GPT-5 model
- `gpt-5.1-codex` - Previous generation
- `o3` - Reasoning model
- `o4-mini` - Fast, efficient model

### Changing the Model

**Step 1:** Edit the source config:

```bash
vim "$(chezmoi source-path)/dot_codex/config.toml"
```

**Step 2:** Update the model field:

```toml
model = "gpt-5.2"
model_reasoning_effort = "medium"  # minimal, low, medium, high, xhigh
```

**Step 3:** Apply changes:

```bash
chezmoi apply --force ~/.codex/config.toml
```

**Step 4:** Verify in Codex:

```
/model
```

---

## 2. Modifying Approval & Security Settings

### Approval Policy

Controls when Codex pauses for approval:

```toml
# "untrusted" - Strict, prompts for most operations
# "on-request" - Balanced, prompts for potentially destructive operations
# "never" - No prompts (use with caution)
approval_policy = "on-request"
```

### Sandbox Mode

Controls filesystem and network access:

```toml
# "read-only" - No writes allowed
# "workspace-write" - Writes to project directory only (recommended)
# "danger-full-access" - Full system access (use with extreme caution)
sandbox_mode = "workspace-write"
```

### Common Configurations

**Safe exploration:**
```toml
approval_policy = "on-request"
sandbox_mode = "read-only"
```

**Active development:**
```toml
approval_policy = "on-request"
sandbox_mode = "workspace-write"
```

**Automation/CI:**
```toml
approval_policy = "never"
sandbox_mode = "workspace-write"
```

---

## 3. Modifying System Instructions (AGENTS.md)

### AGENTS.md Purpose

The `AGENTS.md` file provides persistent instructions that Codex reads before any work. It's ideal for:
- Working agreements and conventions
- Project-specific context
- Safety boundaries
- Communication preferences

### Modifying AGENTS.md

**Step 1:** Edit the source file:

```bash
vim "$(chezmoi source-path)/dot_codex/AGENTS.md"
```

**Step 2:** Add your instructions:

```markdown
## My Custom Rules

- Always use TypeScript strict mode
- Prefer functional programming patterns
- Run `npm run lint:fix` before committing
```

**Step 3:** Apply changes:

```bash
chezmoi apply --force ~/.codex/AGENTS.md
```

### AGENTS.md Discovery

Codex discovers instructions in this order:
1. Global: `~/.codex/AGENTS.md` (or `AGENTS.override.md`)
2. Project: Walks from Git root to current directory
3. Merges all found files, with closer files overriding earlier ones

---

## 4. Modifying Skills

### What Are Skills?

Skills are specialized knowledge packages that provide domain-specific instructions. They can include:
- Markdown documentation
- Scripts
- Reference files

### Skill Structure

```
skills/
└── skill-name/
    ├── SKILL.md          # Main skill documentation
    ├── scripts/          # Optional helper scripts
    └── reference/        # Optional reference files
```

### Creating a New Skill

**Step 1:** Create skill directory:

```bash
mkdir -p "$(chezmoi source-path)/dot_codex/skills/my-skill"
```

**Step 2:** Create `SKILL.md`:

```markdown
---
name: my-skill
description: What this skill helps with
---

# Skill: My Skill Name

## Overview

What this skill does and when to use it.

## When to Use

- Scenario 1
- Scenario 2

## Workflow

1. Step one
2. Step two
3. Step three
```

**Step 3:** Apply changes:

```bash
chezmoi apply --force ~/.codex/skills/
```

---

## 5. Feature Flags

### Enabling Features

In `config.toml`:

```toml
[features]
multi_agent = true        # Enable multi-agent collaboration
shell_snapshot = true     # Speed up repeated commands
unified_exec = true       # Use PTY-backed exec
```

### From CLI

```bash
codex --enable multi_agent --enable shell_snapshot
```

### Available Features

| Feature | Default | Description |
|---------|---------|-------------|
| `shell_tool` | true | Enable shell command execution |
| `collaboration_modes` | true | Enable plan mode |
| `personality` | true | Enable personality selection |
| `undo` | true | Enable undo via git snapshots |
| `request_rule` | true | Smart approval suggestions |
| `shell_snapshot` | false | Speed up repeated commands |
| `unified_exec` | false | PTY-backed exec tool |
| `multi_agent` | false | Multi-agent collaboration |

---

## 6. Troubleshooting

### Changes Not Applied

```bash
# Check if chezmoi is tracking the file
chezmoi managed | grep codex

# Force apply
chezmoi apply --force ~/.codex/

# Check diff
chezmoi diff ~/.codex/config.toml
```

### Model Not Found

```bash
# List available models in Codex
codex
/model
```

### Authentication Issues

```bash
# Re-authenticate
codex
# Select "Sign in with ChatGPT" or use API key
```

### Permission Errors

```bash
# Check chezmoi permissions
chezmoi doctor

# Ensure files are readable
ls -la ~/.codex/
```

---

## 7. Best Practices

### DO

- Always edit files in `$(chezmoi source-path)/` then apply with chezmoi
- Use version control (commit changes to the boilerplate repo)
- Test configuration changes with simple tasks first
- Use `approval_policy = "on-request"` for interactive work
- Set `sandbox_mode = "workspace-write"` for development

### DON'T

- Edit files directly in `~/.codex/` (will be overwritten)
- Store API keys in config files (use Codex's auth system)
- Use `approval_policy = "never"` with `sandbox_mode = "danger-full-access"`
- Enable experimental features without testing

---

## 8. Common Workflows

### Switching Models

```bash
# 1. Edit source config
vim "$(chezmoi source-path)/dot_codex/config.toml"

# 2. Update model field
# model = "gpt-5.2"

# 3. Apply
chezmoi apply --force ~/.codex/config.toml
```

### Adding a Project-Specific Config

```bash
# 1. Create project config
cd /path/to/project
mkdir -p .codex

# 2. Create config file
cat > .codex/config.toml << 'EOF'
model = "o3"
approval_policy = "on-request"

[features]
multi_agent = true
EOF

# 3. Use immediately (no chezmoi needed for project configs)
codex
```

### Updating Global Instructions

```bash
# 1. Edit AGENTS.md
vim "$(chezmoi source-path)/dot_codex/AGENTS.md"

# 2. Apply
chezmoi apply --force ~/.codex/AGENTS.md

# 3. Verify in new Codex session
codex
# Ask: "Summarize the current instructions"
```

---

## Related Resources

- [Codex Documentation](https://developers.openai.com/codex)
- [Codex CLI Reference](https://developers.openai.com/codex/cli/reference)
- [Codex Config Reference](https://developers.openai.com/codex/config-reference)
- [AGENTS.md Specification](https://agents.md)
- [Chezmoi Documentation](https://www.chezmoi.io/)

Base directory for this skill: `~/.codex/skills/codex-config/`
