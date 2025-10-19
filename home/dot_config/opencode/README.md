# OpenCode + Spec-Kit

## What This Is

Global spec-kit commands for opencode. Commands are available as `/speckit.*` in any project.

## One-Time Setup

Add to `~/Documents/GitHub/boilerplate/home/dot_config/mise/config.toml`:

```toml
[tools]
uv = "latest"
```

Then:

```bash
cd ~/Documents/GitHub/boilerplate
chezmoi apply
mise install
```

Done. Commands deployed to `~/.config/opencode/command/` automatically.

## Update Spec-Kit

When spec-kit releases updates:

```bash
cd ~/.config/opencode
uv tool install --force specify-cli --from git+https://github.com/github/spec-kit.git
specify init --here --ai opencode --force
```

Then commit changes in chezmoi source.

## Commands

Available globally in opencode:

- `/speckit.constitution`
- `/speckit.specify`
- `/speckit.clarify`
- `/speckit.plan`
- `/speckit.tasks`
- `/speckit.implement`
- `/speckit.analyze`
- `/speckit.checklist`

## How It Works

- Commands in `command/` (chezmoi → `~/.config/opencode/command/`)
- Templates in `.specify/` (chezmoi → `~/.config/opencode/.specify/`)
- OpenCode reads commands automatically
- First use in a project bootstraps `.specify/` into that project
