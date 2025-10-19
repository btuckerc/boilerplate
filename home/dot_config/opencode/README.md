# OpenCode + Spec-Kit Integration

Automated spec-kit commands for opencode, managed via chezmoi and mise.

## Setup

1. Add to `~/Documents/GitHub/boilerplate/home/dot_config/mise/config.toml`:

```toml
[tools]
uv = "latest"
```

2. Apply:

```bash
cd ~/Documents/GitHub/boilerplate
chezmoi apply
mise install
```

Commands are now available in opencode as `/speckit.*`

## How It Works

- **Chezmoi external** fetches spec-kit from GitHub (weekly, configurable)
- **Run script** copies commands to `~/.config/opencode/command/` on apply
- **Zero manual intervention** - just `chezmoi apply` to update

## Updates

**Automatic:** Chezmoi checks for spec-kit updates weekly

**Manual:** Run `chezmoi update` to force check now

Then `chezmoi apply` to deploy.

## Available Commands

- /speckit.constitution
- /speckit.specify
- /speckit.clarify
- /speckit.plan
- /speckit.tasks
- /speckit.implement
- /speckit.analyze
- /speckit.checklist

## Files

- `.chezmoiexternal.toml` - Fetches spec-kit from GitHub
- `run_after_speckit.sh.tmpl` - Deploys commands automatically
- `dot_specify/` - Reference templates
- `.chezmoiremove` - Cleans up old files

Fully repeatable. No manual steps beyond standard chezmoi/mise workflow.
