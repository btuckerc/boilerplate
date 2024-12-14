# Linux (and macOS) Holy Grail

## Basic Command Line Stuff
- `|`: Pipe output of one program to the next.
- `>>`: Append output to a file (does not overwrite).
- `>`: Write output to a file (overwrites existing content).
- `<`: Redirect input to a program.
- `A && B`: If command `A` succeeds (exit code 0), execute command `B`.
- `A || B`: If command `A` fails (non-zero exit code), execute command `B`.
- `$(command)`: Command substitution (embed output of a command).
- `${variable}`: Variable substitution (use a variable's value).

---

## Time and Scheduling

### Cron Time Format
```
* * * * * command to execute
│ │ │ │ │
│ │ │ │ └── Day of Week (0-6, Sunday=0)
│ │ │ └──── Month (1-12)
│ │ └────── Day of Month (1-31)
│ └──────── Hour (0-23)
└────────── Minute (0-59)
```

### Common Time Notation
- `m`: Minute (0-59)
- `h`: Hour (0-23)
- `dom`: Day of Month (1-31)
- `mon`: Month (1-12)
- `dow`: Day of Week (0-6, Sunday=0)

### Examples
```bash
# Run every minute
* * * * * /script.sh

# Run at 2:30 AM daily
30 2 * * * /script.sh

# Run at 2:30 AM every Monday
30 2 * * 1 /script.sh

# Run every 15 minutes
*/15 * * * * /script.sh
```

### Cron Locations
- `/var/spool/cron/crontabs/`: User-specific cron jobs
- `/etc/cron.d/`: System cron jobs
- `/etc/crontab`: System-wide cron configuration

### macOS Alternative (launchd)
macOS uses `launchd` instead of `cron`. Jobs are configured via `.plist` files:
```bash
# User agents (user-specific tasks)
~/Library/LaunchAgents/

# System agents (system-wide tasks)
/Library/LaunchAgents/
/Library/LaunchDaemons/

# View loaded jobs
launchctl list

# Load a job
launchctl load ~/Library/LaunchAgents/com.user.task.plist

# Unload a job
launchctl unload ~/Library/LaunchAgents/com.user.task.plist
```

---

## Commands To Know
- **`cut`**: Extract fields from input (e.g., `cut -d: -f2` splits by `:` and takes the 2nd field).
- **`sort`**: Sort lines of text files. Combine with `uniq` to deduplicate (`sort | uniq`).
- **`uniq`**: Filter adjacent duplicate lines. Use with `-c` to count occurrences.
- **`wc`**: Count words, lines, or characters (e.g., `wc -l` counts lines).
- **`grep`**: Search for patterns in files. Use `-r` for recursive search.
  - `grep -i`: Case-insensitive search
  - `grep -v`: Invert match (show non-matching lines)
  - `grep -l`: Only show filenames of matches
- **`find`**: Search for files in directory hierarchy
  - `find . -name "*.go"`: Find all Go files
  - `find . -type d`: Find directories
  - `find . -mtime -7`: Find files modified in last 7 days
- **`top`**: View running processes. On macOS, use `top` or install `htop` via Homebrew (`brew install htop`).
- **`uname`**: Print system information.
  - `uname -a`: Show all system info (kernel, hostname, etc.).
- **`ifconfig`** (macOS): View or configure network interfaces (similar to `ip addr` on Linux).
- **`df`**: Show disk space usage. Use `df -h` for human-readable output.
- **`du`**: Display directory/file sizes. Example: `du -sh *` for a summary.
- **`lsof`**: List open files. Example: `lsof -i :8080` to see what's using port 8080.
- **`ps`**: Display process table. Example: `ps aux` shows all processes.
- **`netstat`** (macOS): Deprecated. Use `lsof -i` or `ss` if installed.
- **`tee`**: Output to both file and terminal. Example: `ls | tee output.txt`.
  - `tee -a`: Append instead of overwriting.
- **`xargs`**: Build command lines from standard input
  - `find . -name "*.tmp" | xargs rm`: Remove all .tmp files
- **`sed`**: Stream editor for filtering and transforming text
  - `sed 's/old/new/g'`: Replace all occurrences of 'old' with 'new'
  - `sed -i ''`: Edit files in-place on macOS (use -i without '' on Linux)

---

## Git Commands
- **Basic Operations**:
  - `git add -p`: Interactively stage changes
  - `git commit --amend`: Modify the last commit
  - `git reset --soft HEAD^`: Undo last commit, keep changes staged
  - `git reset --hard HEAD^`: Undo last commit, discard changes
- **Branching**:
  - `git checkout -`: Switch to previous branch
  - `git branch -D`: Force delete branch
  - `git branch --merged`: Show merged branches
- **Remote Operations**:
  - `git remote prune origin`: Clean up deleted remote branches
  - `git fetch --prune`: Fetch and clean up in one step
- **Stashing**:
  - `git stash push -m "message"`: Stash with description
  - `git stash pop`: Apply and remove stash
  - `git stash apply`: Apply but keep stash

---

## Command Line Navigation
- `ctrl+a`: Move to the beginning of the line.
- `ctrl+e`: Move to the end of the line.
- `alt+f`: Move forward one word.
- `alt+b`: Move backward one word.
- `ctrl+r`: Search through command history.
- `ctrl+g`: Exit reverse search and keep what you typed.
- `ctrl+l`: Clear the terminal.
- `ctrl+w`: Delete word before cursor.
- `ctrl+k`: Delete from cursor to end of line.
- `ctrl+u`: Delete from cursor to start of line.

## Command History and Reuse
- `!!`: Run the last command
- `!$`: Use the last argument of the previous command
- `!*`: Use all arguments of the previous command
- `!string`: Run the most recent command that starts with "string"
- `!number`: Run command number 'number' from history
- `!-n`: Run the command n commands ago
- `^old^new`: Quick substitution - replace 'old' with 'new' in the previous command
- **History Navigation**:
  - `history`: Show command history
  - `history n`: Show last n commands
  - `ctrl+r`: Reverse search (press multiple times to cycle through matches)
  - `ctrl+s`: Forward search through history (if enabled)
  - Up/Down arrows: Navigate through previous commands
  - `fc`: Open last command in editor
- **History Shortcuts**:
  - `$_`: Last argument of the previous command
  - `!#`: Entire current command line typed so far
  - `!:n`: nth argument of previous command (0 is command, 1 is first argument)
  - `!:n-m`: Arguments n through m of previous command
- **History Settings**:
  ```bash
  # Add to ~/.bashrc or ~/.zshrc
  export HISTSIZE=10000        # Number of commands in memory
  export HISTFILESIZE=10000    # Number of commands in history file
  export HISTCONTROL=ignoredups:erasedups  # Don't store duplicates
  shopt -s histappend         # Append to history instead of overwriting
  ```

## Additional Bash Tips
- **Directory Stack**:
  - `pushd directory`: Push directory onto stack and cd to it
  - `popd`: Pop directory from stack and cd to it
  - `dirs -v`: View directory stack
- **Brace Expansion**:
  - `mkdir -p project/{src,test,docs}`: Create multiple directories
  - `cp file{,.bak}`: Quick backup (expands to: cp file file.bak)
  - `touch file{1..5}.txt`: Create file1.txt through file5.txt
- **Parameter Expansion**:
  - `${variable:-default}`: Use default if variable is unset
  - `${variable:=default}`: Set default if variable is unset
  - `${#variable}`: Length of variable
  - `${variable#pattern}`: Remove shortest match from start
  - `${variable##pattern}`: Remove longest match from start
  - `${variable%pattern}`: Remove shortest match from end
  - `${variable%%pattern}`: Remove longest match from end
- **Quick Substitution**:
  - `^error^correction`: Replace first occurrence
  - `!!:gs/error/correction/`: Replace all occurrences

---

## VIM
- **Basic Commands**:
- `set number`: Turn on line numbering.
- `number + command`: Repeat a command `number` times (e.g., `5dd` deletes 5 lines).
- `dd`: Delete a line.
- `dw`: Delete a word.
- `d$`: Delete to the end of the line.
- `u`: Undo.
- `ctrl+r`: Redo.
- `cw`: Change word.
- `c$`: Replace to the end of the line.
- `/string`: Search for `string` downward.
- `?string`: Search for `string` upward.
- `%`: Jump to the matching parenthesis, bracket, or brace.
- `:%s/string/replacement/gc`: Replace all occurrences of `string` with `replacement`, confirming each change.
- `i`: insert.
- `a`: insert after character.
- `A`: insert at end of line.
- **Advanced Commands**:
  - `:set paste`: Enable paste mode (better formatting)
  - `:set nopaste`: Disable paste mode
  - `gg=G`: Re-indent entire file
  - `zz`: Center cursor on screen
  - `ZZ`: Save and quit
  - `ZQ`: Quit without saving

---

## SCREEN (Terminal Multiplexing)
- `screen -ls`: List all screen sessions.
- `screen -r`: Reattach to a detached session.
- `screen -S <name>`: Start a new session with a name.
- **TMUX Commands**:
  - `tmux new -s name`: Create new named session
  - `tmux attach -t name`: Attach to named session
  - `tmux ls`: List sessions
  - `prefix + d`: Detach from session
  - `prefix + c`: Create new window
  - `prefix + p/n`: Previous/next window

---

## Additional Tips for macOS
### Homebrew
- **Install Homebrew**:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
- **Useful Commands**:
  - `brew update && brew upgrade`: Update all packages
  - `brew cleanup`: Remove old versions
  - `brew doctor`: Check for issues
  - `brew list --versions`: List installed packages
  - `brew deps --tree package`: Show dependency tree

### macOS Specific
- `pbcopy < file`: Copy file contents to clipboard
- `pbpaste > file`: Paste clipboard to file
- `open .`: Open current directory in Finder
- `open -a "App Name" file`: Open file with specific app
- `defaults write`: Modify macOS settings
  - `defaults write -g KeyRepeat -int 2`: Faster key repeat
  - `defaults write -g InitialKeyRepeat -int 15`: Faster initial key repeat

