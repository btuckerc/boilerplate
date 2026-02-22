# Global Agent Instructions

<!--
  This file provides global instructions for Codex CLI.
  Managed by chezmoi - edit source at:
  /Users/tucker/Documents/GitHub/boilerplate/home/dot_config/codex/AGENTS.md
-->

## Working Agreements

### Code Quality
- Always run relevant linters/formatters before completing a task
- Follow existing code style and conventions in the project
- Write clear, self-documenting code with appropriate comments
- Consider edge cases and error handling

### Testing
- Run existing tests after making changes
- Add tests for new functionality when appropriate
- Ensure tests pass before marking a task complete

### Git & Version Control
- Never commit secrets, API keys, or credentials
- Write clear, descriptive commit messages
- Ask before force-pushing or running destructive git commands
- Review changes with `git diff` before committing

### Dependencies
- Ask before adding new production dependencies
- Prefer standard library solutions when practical
- Document why new dependencies are needed

### Communication
- Explain what you're doing and why
- Ask clarifying questions when requirements are ambiguous
- Report issues or blockers promptly
- Provide context for significant decisions

## Tool Usage

### Shell Commands
- Prefer read-only commands when exploring
- Use `--dry-run` flags when available for potentially destructive operations
- Check command documentation (`--help`) when uncertain

### File Operations
- Back up important files before major changes
- Use version control for tracking changes
- Preserve file permissions and ownership when relevant

### Web Search
- Verify information from multiple sources when possible
- Cite sources for factual claims
- Be aware that web content may be outdated or inaccurate

## Project Context

This machine uses:
- **chezmoi** for dotfile management
- **mise** for tool/version management
- **git** for version control

Configuration is tracked in a dotfiles repository and can be pulled to remote machines.

## Safety Boundaries

### Auto-approved
- Reading files and exploring codebases
- Running linters, formatters, and tests
- Creating new files in appropriate locations
- Minor refactoring that doesn't change behavior

### Requires Confirmation
- Installing new packages or dependencies
- Modifying configuration files
- Changes to build/deployment scripts
- Database migrations

### Never Do
- Commit secrets or credentials
- Delete files without explicit permission
- Run commands that could lock you out of the system
- Modify system files outside the project directory