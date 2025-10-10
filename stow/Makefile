# GNU Stow Makefile for dotfiles management
# Usage: make stow, make unstow, make restow
# Note: This setup works with the ../config/ and ../dotfiles/ structure

REPO_DIR := $(PWD)/..
CONFIG_DIR := $(REPO_DIR)/config
DOTFILES_DIR := $(REPO_DIR)/dotfiles
TARGET_DIR := $(HOME)

# Apps that should be symlinked from config/
CONFIG_APPS := nvim ghostty tmux btop vscode
# Shell configs that should be symlinked from dotfiles/
DOTFILE_APPS := zsh

.PHONY: all stow unstow restow clean help

# Default target
all: stow

# Stow all packages
stow:
	@echo "Creating symlinks for config apps and dotfiles..."
	@mkdir -p $(TARGET_DIR)/.config
	@for app in $(CONFIG_APPS); do \
		if [ -d "$(CONFIG_DIR)/$$app" ]; then \
			echo "Linking $$app config..."; \
			ln -sfn "$(CONFIG_DIR)/$$app" "$(TARGET_DIR)/.config/$$app"; \
		fi; \
	done
	@for app in $(DOTFILE_APPS); do \
		if [ "$$app" = "zsh" ]; then \
			echo "Linking zsh configs..."; \
			ln -sfn "$(DOTFILES_DIR)/zshrc" "$(TARGET_DIR)/.zshrc"; \
			ln -sfn "$(DOTFILES_DIR)/zsh_aliases" "$(TARGET_DIR)/.zsh_aliases"; \
			ln -sfn "$(DOTFILES_DIR)/zshenv" "$(TARGET_DIR)/.zshenv" 2>/dev/null || true; \
		fi; \
	done
	@echo "Done!"

# Unstow all packages
unstow:
	@echo "Removing symlinks for config apps and dotfiles..."
	@for app in $(CONFIG_APPS); do \
		if [ -L "$(TARGET_DIR)/.config/$$app" ]; then \
			echo "Removing $$app config link..."; \
			rm "$(TARGET_DIR)/.config/$$app"; \
		fi; \
	done
	@for app in $(DOTFILE_APPS); do \
		if [ "$$app" = "zsh" ]; then \
			echo "Removing zsh config links..."; \
			rm -f "$(TARGET_DIR)/.zshrc" "$(TARGET_DIR)/.zsh_aliases" "$(TARGET_DIR)/.zshenv"; \
		fi; \
	done
	@echo "Done!"

# Restow (unstow then stow) all packages - useful for updates
restow: unstow stow
	@echo "Restow complete!"

# Check what would be stowed without actually doing it
dry-run:
	@echo "Dry run - showing what would be linked:"
	@echo "Config apps that would be linked to ~/.config/:"
	@for app in $(CONFIG_APPS); do \
		if [ -d "$(CONFIG_DIR)/$$app" ]; then \
			echo "  $$app -> $(CONFIG_DIR)/$$app"; \
		fi; \
	done
	@echo "Dotfiles that would be linked to ~:"
	@for app in $(DOTFILE_APPS); do \
		if [ "$$app" = "zsh" ]; then \
			echo "  .zshrc -> $(DOTFILES_DIR)/zshrc"; \
			echo "  .zsh_aliases -> $(DOTFILES_DIR)/zsh_aliases"; \
			[ -f "$(DOTFILES_DIR)/zshenv" ] && echo "  .zshenv -> $(DOTFILES_DIR)/zshenv"; \
		fi; \
	done

# Clean up broken symlinks
clean:
	@echo "Cleaning up broken symlinks in $(TARGET_DIR)/.config"
	@find $(TARGET_DIR)/.config -type l -exec test ! -e {} \; -delete -print 2>/dev/null || true
	@echo "Done!"

# Check prerequisites (no longer needs GNU Stow)
check:
	@echo "Checking dotfiles setup..."
	@[ -d "$(CONFIG_DIR)" ] && echo "✓ Config directory exists" || echo "✗ Config directory missing"
	@[ -d "$(DOTFILES_DIR)" ] && echo "✓ Dotfiles directory exists" || echo "✗ Dotfiles directory missing"
	@echo "Ready to symlink dotfiles!"

# Show help
help:
	@echo "Available targets:"
	@echo "  stow       - Link all dotfiles using GNU Stow"
	@echo "  unstow     - Remove all stowed symlinks"
	@echo "  restow     - Restow all packages (useful for updates)"
	@echo "  dry-run    - Show what would be stowed without doing it"
	@echo "  clean      - Remove broken symlinks"
	@echo "  check      - Check prerequisites and directory structure"
	@echo "  help       - Show this help message"
	@echo ""
	@echo "Config apps: $(CONFIG_APPS)"
	@echo "Dotfile apps: $(DOTFILE_APPS)"