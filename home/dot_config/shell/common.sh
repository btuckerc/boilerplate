#!/bin/sh
# Managed by chezmoi - https://github.com/btuckerc/boilerplate
# Shared POSIX-compatible shell configuration
# Sourced by both ~/.zshrc and ~/.bashrc

# === Environment Variables ===
export EDITOR="nvim"
export PROJECTS_ROOT="${PROJECTS_ROOT:-$HOME/src}"
export DEV_DIR="${DEV_DIR:-$PROJECTS_ROOT}"
export LOGFILE="${LOGFILE:-$HOME/.shellrc_log}"

# XDG Base Directory Specification
# https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"

# History file locations (XDG-compliant)
export LESSHISTFILE="$XDG_CACHE_HOME/less_history"
export PYTHON_HISTORY="$XDG_DATA_HOME/python/history"

# === PATH Setup ===
# Add key user-level bin directories to PATH if they exist.
# Iterate from lowest to highest precedence because each directory is prepended.
# remove_path_dir walks PATH with ${%%:*} instead of IFS word splitting, which
# zsh skips and bash drops trailing empty fields from, so every other component,
# including empty ones (the current directory), survives in every shell; an
# empty PATH has no components. A lone remaining empty component is written as
# ':' because '' would read back as no components. .zshrc/.bashrc call it again
# after mise activation.
remove_path_dir() {
	path_rest="${PATH:+$PATH:}"
	path_new=""
	path_sep=""
	while [ -n "$path_rest" ]; do
		path_entry="${path_rest%%:*}"
		path_rest="${path_rest#*:}"
		[ "$path_entry" = "$1" ] && continue
		path_new="$path_new$path_sep$path_entry"
		path_sep=:
	done
	PATH="${path_new:-$path_sep}"
}

prepend_path_dir() {
	[ -d "$1" ] || return 0
	remove_path_dir "$1"
	PATH="$1${PATH:+:$PATH}"
}

remove_path_dir "$HOME/.local/share/omarchy/bin"

prepend_path_dir "$HOME/.local/share/mise/shims"
prepend_path_dir "$HOME/.local/bin"
export PATH
unset path_entry path_new path_rest path_sep
unset -f prepend_path_dir 2>/dev/null || true

# === Pager Configuration ===
export MANPAGER="less -R --use-color -Dd+r -Du+b"
# F: quit at once when output fits one screen (git's own default, lost once LESS is set).
export LESS="FR --use-color -Dd+r -Du+b"

# === FZF Configuration ===
export FZF_DEFAULT_OPTS="--style minimal --color 16 --layout=reverse --height 30% --preview='bat -p --color=always {}'"

# === Aliases (POSIX-compatible) ===
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

# Git aliases
alias gs='git status'
alias ga='git add'
alias gb='git branch'
alias gc='git commit'
alias gd='git diff'
alias gl='git --no-pager log --oneline --decorate --all --graph'
alias gst='git status'
alias gpl='git pull'
alias gps='git push'
alias gcm='git commit -m'

# Git tools
alias lg='lazygit'

# Editor aliases
alias vim='nvim'
alias v.='nvim .'
alias practice='nvim +VimBeGood'

# Codex aliases
alias c='codex'
alias cx='codex --dangerously-bypass-approvals-and-sandbox'

# Python virtual environment
alias venv_activate='source venv/bin/activate'
alias vde='deactivate'

# Obsidian/notetaking aliases
alias oo="cd '$HOME/Documents/00-Vault/00 - Inbox/'"
alias dn='nvim +ObsidianToday'

# Fun/Utility aliases
alias rot13="tr 'A-Za-z' 'N-ZA-Mn-za-m'"
alias dunnet="emacs -batch -l dunnet"

# === Functions ===

# Navigate to source directory
dev() {
	if [ ! -d "$DEV_DIR" ]; then
		echo "$(date): source directory not found. Creating..." >>"$LOGFILE"
		mkdir -p "$DEV_DIR"
	fi
	cd "$DEV_DIR" || echo "$(date): Failed to navigate to $DEV_DIR" >>"$LOGFILE"
}

# Create projects outside cloud-synced Documents/Desktop trees.
mkproject() {
	case ${1-} in
	"" | /* | .. | ../* | */../* | */..)
		echo "Usage: mkproject <name-or-relative-path>" >&2
		return 2
		;;
	esac
	mkdir -p "$DEV_DIR/$1" || return
	cd "$DEV_DIR/$1" || return
}

# Create and activate Python virtual environment
venv() {
	if [ ! -d "venv" ]; then
		echo "Creating virtual environment..."
		python3 -m venv venv
	fi
	echo "Activating virtual environment..."
	. venv/bin/activate
}

# File extraction helper
ee() {
	if [ -f "$1" ]; then
		case $1 in
		*.tar.bz2) tar xvjf "$1" ;;
		*.tar.gz) tar xvzf "$1" ;;
		*.bz2) bunzip2 "$1" ;;
		*.rar) unrar x "$1" ;;
		*.gz) gunzip "$1" ;;
		*.tar) tar xvf "$1" ;;
		*.tbz2) tar xvjf "$1" ;;
		*.tgz) tar xvzf "$1" ;;
		*.zip) unzip "$1" ;;
		*.Z) uncompress "$1" ;;
		*.7z) 7z x "$1" ;;
		*) echo "'$1' cannot be extracted via ee" ;;
		esac
	else
		echo "'$1' is not a valid file!"
	fi
}

# Archive creation helpers
mtar() {
	tar cvzf "${1%%/}.tar.gz" "${1%%/}/"
}

mzip() {
	zip -r "${1%%/}.zip" "$1"
}

# File swap function
swap() {
	local TMPFILE=tmp.$$
	[ $# -ne 2 ] && echo "swap: 2 arguments needed" && return 1
	[ ! -e "$1" ] && echo "swap: $1 does not exist" && return 1
	[ ! -e "$2" ] && echo "swap: $2 does not exist" && return 1
	mv "$1" "$TMPFILE"
	mv "$2" "$1"
	mv "$TMPFILE" "$2"
}

# Make directory and cd into it
mc() {
	local dir="$1"
	if [ -z "$dir" ]; then
		echo "Usage: mc <directory>"
		return 1
	fi
	mkdir -p -- "$dir" && cd -- "$dir"
}

# New note helper function
nn() {
	if [ -z "$1" ]; then
		echo "Error: No filename provided."
		echo "Usage: nn <filename>"
		return 1
	fi
	local filename="$1.md"
	vim "$filename"
}

# === Conditional Tool Loading ===

# Generated init code (zoxide/starship init) costs a process spawn per shell.
# _shell_cached_init <variant> <tool> [args...] caches "<tool> args" output as
# one flat file per variant and canonical tool path in a private cache root,
# $XDG_CACHE_HOME/shell-init: a real directory owned by this user with no
# group/other access, every ancestor of which only this user or root can
# rename or replace. Whoever could write there could plant code that gets
# sourced, so any other root disables the cache. The variant names the shell
# plus any environment the generator reads, encoded as fixed literals (never
# raw values: it becomes part of a file name and the header line). An entry is
# regenerated when its header differs or the binary or its directory is newer.
# The tool path is canonicalized, so relinking a symlink to another version
# changes the key; bash has no builtin realpath and does not cache a symlinked
# executable at all.
# On success it sets _shell_init_file for the caller to source at top level
# (sourcing in here would scope the generated code's typeset/local/setopt).
# Entries end with `_shell_init_ok=1`; the helper requires that last line
# before returning an entry, and callers recheck it after sourcing.
# Returns 1 when the tool is missing or the cache is unusable; callers then
# fall back to running the generator directly.
_shell_cached_init() {
	_shell_init_file=
	_shell_init_ok=
	_sci_variant=$1
	_sci_bin=$2
	shift 2
	[ -n "${ZSH_VERSION:-}" ] && setopt localoptions equals nonomatch glob bareglobqual
	case $_sci_bin in
	*/*) ;;
	*)
		if [ -n "${ZSH_VERSION:-}" ]; then
			# =cmd looks up one command; $commands[cmd] would hash all of PATH.
			_sci_bin==$_sci_bin
		elif [ "${BASH_VERSINFO[0]:-0}" -ge 4 ]; then
			hash "$_sci_bin" 2>/dev/null && _sci_bin=${BASH_CMDS[$_sci_bin]}
		else
			# macOS /bin/bash 3.2 (e.g. `bash -lc` under launchd's PATH)
			_sci_bin=$(type -P "$_sci_bin")
		fi
		;;
	esac
	_sci_root="${XDG_CACHE_HOME:-$HOME/.cache}/shell-init"
	_sci_file=
	_sci_head=
	case $_sci_bin in
	/*)
		if [ ! -x "$_sci_bin" ]; then
			_sci_bin=
		elif [ -n "${ZSH_VERSION:-}" ]; then
			_sci_bin=${_sci_bin:A}
		elif [ -L "$_sci_bin" ]; then
			_sci_bin=
		elif _sci_dir=$(builtin cd -P -- "${_sci_bin%/*}" 2>/dev/null && builtin pwd -P) && [ -n "$_sci_dir" ]; then
			_sci_bin="${_sci_dir%/}/${_sci_bin##*/}"
		else
			_sci_bin=
		fi
		;;
	*) _sci_bin= ;;
	esac
	# ACL check via the system ls: Linux marks ACLs with '+' after the mode;
	# macOS shows '@' over '+' when xattrs exist, so list ACL entries with -e.
	_sci_lsf=-ld
	case ${OSTYPE-} in darwin*) _sci_lsf=-led ;; esac
	_sci_nl='
'
	if [ -n "$_sci_bin" ] && { [ "${_shell_init_root_ok-}" != "$_sci_root" ] || [ -z "${_shell_init_root-}" ]; }; then
		_shell_init_root_ok=
		_shell_init_root=
		if [ ! -e "$_sci_root" ] && [ ! -L "$_sci_root" ]; then
			# Drop any ACL inherited from the parent: the mode check below is
			# only meaningful for a directory without ACL entries.
			(umask 077 && mkdir -p -- "$_sci_root" &&
				{ command -p chmod -N "$_sci_root" || command setfacl -b -- "$_sci_root" || :; }) 2>/dev/null
		fi
		# Entries are trusted by pathname, so check every directory from / down
		# to the canonical root, once per shell with one system ls:
		#   root: owned by this user, d???------, no ACL;
		#   ancestors: owned by this user or root, group/other-writable only
		#   with the sticky bit, ACL entries only of the deny kind (macOS; Linux
		#   ls shows only '+', so any ACL there disables the cache).
		# Nobody else can then rename a directory on the path, nor reach the
		# entries or temp files inside the root.
		if [ -n "${ZSH_VERSION:-}" ]; then
			_sci_real=${_sci_root:A}
		else
			_sci_real=$(builtin cd -P -- "$_sci_root" 2>/dev/null && builtin pwd -P)
		fi
		_sci_ok=
		case $_sci_real in
		*"$_sci_nl"*) ;;
		/?*) [ -d "$_sci_real" ] && [ ! -L "$_sci_root" ] && _sci_ok=1 ;;
		esac
		# The subshell lists the root and each ancestor up to /, after a first
		# line with how many paths it passed.
		_sci_all=
		if [ -n "$_sci_ok" ]; then
			_sci_all=$(
				set --
				_sci_p=$_sci_real
				while [ -n "$_sci_p" ]; do
					set -- "$@" "$_sci_p"
					_sci_p=${_sci_p%/*}
				done
				set -- "$@" /
				printf '%s\n' "$#"
				command -p ls -n"${_sci_lsf#-}" -- "$@" 2>/dev/null
			) || _sci_ok=
		fi
		_sci_count=${_sci_all%%"$_sci_nl"*}
		_sci_all=${_sci_all#*"$_sci_nl"}$_sci_nl
		_sci_seen=0
		_sci_rootseen=0
		_sci_cur=
		while [ -n "$_sci_ok" ] && [ "$_sci_all" != "$_sci_nl" ] && [ -n "$_sci_all" ]; do
			_sci_line=${_sci_all%%"$_sci_nl"*}
			_sci_all=${_sci_all#*"$_sci_nl"}
			case $_sci_line in
			' '*)
				# A macOS ACL entry of the line above.
				case $_sci_cur$_sci_line in
				ancestor*' deny '*) ;;
				*) _sci_ok= ;;
				esac
				;;
			*)
				_sci_seen=$((_sci_seen + 1))
				_sci_mode=${_sci_line%% *}
				_sci_rest=${_sci_line#"$_sci_mode"}
				_sci_rest=${_sci_rest#"${_sci_rest%%[! ]*}"}
				_sci_rest=${_sci_rest#*' '}
				_sci_rest=${_sci_rest#"${_sci_rest%%[! ]*}"}
				_sci_uid=${_sci_rest%%' '*}
				case $_sci_line in
				*" $_sci_real")
					_sci_cur=root
					_sci_rootseen=$((_sci_rootseen + 1))
					[ "$_sci_uid" = "$UID" ] || _sci_ok=
					case $_sci_mode in
					d???------ | d???------[.@]) ;;
					*) _sci_ok= ;;
					esac
					;;
				*)
					_sci_cur=ancestor
					case $_sci_uid in
					0 | "$UID") ;;
					*) _sci_ok= ;;
					esac
					case $_sci_mode in
					d?????????+) [ "$_sci_lsf" = -led ] || _sci_ok= ;;
					d?????????[.@] | d?????????) ;;
					*) _sci_ok= ;;
					esac
					case $_sci_mode in
					?????w* | ????????w*)
						case $_sci_mode in
						?????????[tT]*) ;;
						*) _sci_ok= ;;
						esac
						;;
					esac
					;;
				esac
				;;
			esac
		done
		[ "$_sci_seen" = "$_sci_count" ] && [ "$_sci_rootseen" = 1 ] || _sci_ok=
		if [ -n "$_sci_ok" ]; then
			_shell_init_root_ok=$_sci_root
			_shell_init_root=$_sci_real
		else
			_sci_bin=
		fi
	fi
	_sci_root=${_shell_init_root-}
	if [ -n "$_sci_bin" ]; then
		_sci_file="$_sci_variant$_sci_bin"
		_sci_file=${_sci_file//\%/%25}
		_sci_file=${_sci_file//\//%2F}
		[ "${#_sci_file}" -le 200 ] && _sci_file="$_sci_root/$_sci_file" || _sci_file=
	fi
	_sci_key="# shell-init v3 $_sci_variant $_sci_bin $*"
	# A directory in an entry's place cannot be replaced safely: fall back.
	[ -n "$_sci_file" ] && [ -d "$_sci_file" ] && [ ! -L "$_sci_file" ] && _sci_file=
	# Trust an entry only in the shape this helper writes: a regular file owned
	# by this user, not group/other-writable, without a second hard link (which
	# could live outside the private root), framed by the key line and the
	# sentinel line. Anything else is regenerated, which replaces the inode.
	if [ -n "$_sci_file" ] && [ -f "$_sci_file" ] && [ ! -L "$_sci_file" ] && [ -O "$_sci_file" ] &&
		[ -r "$_sci_file" ]; then
		_sci_ok=
		_sci_last=
		if [ -n "${ZSH_VERSION:-}" ]; then
			eval '_sci_ok=( $_sci_file(N.Uf:go-w:l-2) )'
		else
			_sci_ls=$(command -p ls $_sci_lsf -- "$_sci_file" 2>/dev/null)
			case $_sci_ls in
			*"$_sci_nl"* | ??????????+*) ;;
			-????-??-*)
				_sci_ls=${_sci_ls#* }
				_sci_ls=${_sci_ls#"${_sci_ls%%[! ]*}"}
				[ "${_sci_ls%% *}" = 1 ] && _sci_ok=1
				;;
			esac
		fi
		if [ -n "$_sci_ok" ]; then
			if [ -n "${ZSH_VERSION:-}" ]; then
				eval '_sci_lines=( "${(@f)$(<$_sci_file)}" ); _sci_head=$_sci_lines[1]; _sci_last=$_sci_lines[-1]'
			else
				{
					IFS= read -r _sci_head
					while IFS= read -r _sci_line || [ -n "$_sci_line" ]; do
						_sci_last=$_sci_line
					done
				} <"$_sci_file"
			fi
			[ "$_sci_last" = "_shell_init_ok=1" ] || _sci_head=
		fi
	fi
	if [ -n "$_sci_file" ] && { [ "$_sci_head" != "$_sci_key" ] ||
		[ "$_sci_bin" -nt "$_sci_file" ] || [ "${_sci_bin%/*}" -nt "$_sci_file" ]; }; then
		# Publish only complete, non-empty output; if regeneration fails, drop
		# the stale or invalid entry and let the caller fall back.
		# The subshell scopes umask 077 and the temp-file trap, and forks only
		# when regenerating.
		if (
			umask 077
			_sci_tmp=$(mktemp "$_sci_root/.tmp.XXXXXXXX" 2>/dev/null) || exit 1
			trap 'rm -f "$_sci_tmp"' EXIT
			printf '%s\n' "$_sci_key" >"$_sci_tmp" &&
				"$_sci_bin" "$@" >>"$_sci_tmp" &&
				{ IFS= read -r _sci_head && IFS= read -r _sci_head || [ -n "$_sci_head" ]; } <"$_sci_tmp" &&
				printf '\n_shell_init_ok=1\n' >>"$_sci_tmp" &&
				{ [ ! -L "$_sci_file" ] || rm -f "$_sci_file"; } &&
				mv -f "$_sci_tmp" "$_sci_file" 2>/dev/null
		) && [ -f "$_sci_file" ] && [ ! -L "$_sci_file" ]; then
			:
		else
			rm -f -- "$_sci_file"
			_sci_file=
		fi
	fi
	_shell_init_file=$_sci_file
	unset _sci_variant _sci_bin _sci_root _sci_file _sci_key _sci_head _sci_dir _sci_ok _sci_ls _sci_last \
		_sci_line _sci_lines _sci_lsf _sci_nl _sci_real _sci_count _sci_all _sci_seen _sci_rootseen \
		_sci_cur _sci_mode _sci_rest _sci_uid
	[ -n "$_shell_init_file" ]
}

# Load Cargo if available
[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"

# Load Deno if available
[ -f "$HOME/.deno/env" ] && . "$HOME/.deno/env"

# Load secrets if they exist
[ -f "$HOME/.secrets" ] && . "$HOME/.secrets"
