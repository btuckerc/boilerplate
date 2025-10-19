# OpenCode + Spec-Kit

## Setup

Add to `~/Documents/GitHub/boilerplate/home/dot_config/mise/config.toml`:

```toml
[tools]
uv = "latest"
```

Apply:

```bash
cd ~/Documents/GitHub/boilerplate
chezmoi apply ~/.config/mise/config.toml
mise install uv
cd ~/.config/opencode
mise run setup-opencode-speckit
```

## Update

```bash
cd ~/.config/opencode
mise run update-speckit
```

## Commands

Available in opencode projects via `/speckit.*`:

- constitution
- specify
- clarify
- plan
- tasks
- implement
- analyze
- checklist
