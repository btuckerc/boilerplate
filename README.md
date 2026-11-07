# Boilerplate dotfiles

This repository is the shared chezmoi source for macOS and Linux hosts. It keeps
shell, editor, terminal, tool, and host-specific configuration in one reviewed
Git baseline.

## Fresh host

```sh
mkdir -p ~/src
git clone https://github.com/btuckerc/boilerplate.git ~/src/boilerplate
cd ~/src/boilerplate
./setup --plan
./setup
```

`setup` installs chezmoi if needed, links `~/.local/share/chezmoi` to this
checkout, initializes host data, runs prerequisite/tool hooks, and verifies OMP,
Codex, and shared skills. Account logins and OS permission prompts remain local.

## Daily workflow

1. Author in a worktree of this checkout:
   `git -C ~/src/boilerplate worktree add ~/src/boilerplate-wt/<task>`.
   Uncommitted edits in `~/src/boilerplate` itself hold back applies.
2. Preview: `chezmoi -S ~/src/boilerplate-wt/<task> diff`.
3. Review and commit there, then land with `git merge --ff-only` in
   `~/src/boilerplate`.
4. Publish and apply the committed baseline:
   ```sh
   decent-angl-sync reconcile
   ```

On another host, `decent-angl-sync reconcile` publishes reviewed local commits
when needed, fast-forwards, and applies committed state. The scheduled `guard`
converges without publishing. See [UPDATING.md](UPDATING.md) for the complete
publish/apply, recovery, and validation workflow.

## Tool ownership

`mise` owns language runtimes and CLI tools through exact pins in
[`home/dot_config/mise/config.toml`](home/dot_config/mise/config.toml). Homebrew
owns system packages, libraries, and GUI applications listed in
[`home/Brewfile`](home/Brewfile); do not duplicate mise tools there. Changed
pins install through `decent-angl-sync reconcile` and each host's guard.

## Agents and Herdr

Claude Code (`claude`, Opus 5.5 high on Tucker's own Claude login) is the
director. Its user settings and rules come from
[`home/private_dot_claude/`](home/private_dot_claude): `modify_settings.json`
owns only its listed keys and keeps Herdr hooks and local choices, and
`CLAUDE.md` holds the routing rules. The director delegates through
`agent-run` (Codex Sol workers in their own worktrees, read-only consults,
release audits, local Qwen runs), with receipts under
`~/.local/state/agent-runs/`. A receipt is `ok` only when the child's own
transcript shows the expected model and effort on every request, only the
lane's tools, and no subagent or MCP call. `attestation_evidence` identifies
Codex's `rollout`, Claude's `transcript`, or local
`omp-session-worker-writable` evidence: local model/effort evidence is not an
independent attestation. Local Qwen workers have only read, edit, write, grep
and glob tools; the director runs acceptance checks. They run under `bwrap`
(the runner attests it) with the caller repo, Git metadata and OMP launch
inputs read-only, private IPC and masked `/run` and `/var/run` (only a regular
resolver configuration file is restored for DNS). Codex Sol
workers exclude implicit `/tmp` and `$TMPDIR` writes; their only writable
roots are the worktree and `RUN/child/tmp`, also their `TMPDIR`, `TMP` and
`TEMP`; other lanes retain their temporary-directory environment, with local
workers using private `/tmp`. `gc` removes the worker worktree and
`RUN/child/tmp` (and audit candidate trees), keeping sessions and receipts.
GC persists worktree-removal progress before temporary cleanup. If cleanup
fails, `gc_tmp_error` records the error; rerun `agent-run gc ID` to retry
without repeating worktree removal. Temporary cleanup walks relative to
directory descriptors without recursion or following symlinks.
BSD user flags are cleared without following symlinks; the absolute-path
fallback checks the entry's inode/device identity before changing flags.
The `lchflags` fallback assumes no worker process survives during GC (one
could race the identity check), and ACL entries are not cleared automatically.
`gc --older-than 0` considers all finished runs, continues after individual
failures and exits 1 if any fail. A missing caller repository does not prevent
removal of its safely named worktree; `worktree_removed_without_repo` records
that cleanup mode.
As a backstop, `sol` and `local` still refuse a caller checkout under
`/tmp` or `$TMPDIR`. Every launch also refuses state, slot-lock or run
directories overlapping those temporary roots or the worker-worktree root;
only the designated `RUN/child` subtree is writable inside a local run.
`result.patch` applies to the advertised base and is saved before transcript
verification. Runner Git commands ignore worktree attributes and disable
filters, hooks, fsmonitor, external diffs and textconv regardless of Git
version; `GIT_ATTR_SOURCE` requires Git 2.40+ (nous has 2.53, mac has 2.56).
Trusted global excludes are preserved. Worker outputs must be regular,
non-symlink files; FIFOs cannot block settlement. Verification reads are
bounded to 512 MiB total and 16 MiB per JSONL line; `worker_bytes_read` records
the total in `meta.json`. Exceeding a limit leaves the patch intact and the
receipt unverified. Workers cannot launch
`agent-run` recursively. `meta.json` lists files a `--setup` step changed.
`--setup` is director input: it runs unsandboxed in the worktree with the
director's own rights before the worker starts. Setup keeps director SSH,
IPC and temporary-directory settings, but drops session identity and provider
credential variables; it is not marked as an agent-run child. `--net` gives a Sol worker
network access while Codex can read the director's files: it requires
director-level trust, the same as `--setup`.
`agent-quota` prints both subscriptions' remaining quota. OMP remains for the
zero-cloud `omp-local` session and legacy Codex-only roles.

Herdr is pinned through mise and configured at `~/.config/herdr/config.toml`.
Run `herdr` once, start each `claude` (or `omp`) session in its own workspace
or tab, and detach with `Ctrl-b q`; running sessions stay attached to the local
Herdr server. `herdr integration install claude|codex` supplies
working/blocked/idle state and native session restore. `agent-run` strips
`HERDR_*` from its children, so workers never report into the director's pane.
Runtime sessions and saved SSH-machine profiles remain machine-local.

Reverting the director commit returns `.claude` to the global ignore list, so
chezmoi stops managing it but leaves deployed files behind. After the revert
reconciles, on each agent host remove `~/.claude/CLAUDE.md` and
`~/.local/bin/{agent-run,agent-quota,claude-statusline,council-yield}`, drop the
skill links with
`find ~/.claude/skills -maxdepth 1 -type l -lname "$HOME/.local/share/decent-angl/*" -delete`,
and strip the owned settings keys:
`jq 'del(.model, .modelSettings["claude-opus-5-5"].effortLevel, .permissions.defaultMode, .skipDangerousModePermissionPrompt, .attribution, .cleanupPeriodDays, .statusLine, .env.DISABLE_AUTOUPDATER)' ~/.claude/settings.json`
(write the result back). Receipts under `~/.local/state/agent-runs/` stay as
history.

## Terminal font

macOS Ghostty uses [Obel Mono](https://typographic.systems/obel-mono) 1.000
(SIL OFL 1.1): regular at 400, bold at the ExtraBold instance, and cell height
16% to keep Meslo's line rhythm. `run_onchange_after_07-install-obel-mono`
installs pinned, hash-checked TTFs on macOS and Linux desktops, into
`~/Library/Fonts` or `~/.local/share/fonts/obel-mono`; existing hosts get it
through `decent-angl-sync reconcile --with-scripts` (the reviewed font hook).
The always-masked "Obel Mono Masked" family is installed for apps without font
feature settings. Linux Ghostty and kitty stay on JetBrains Mono until Obel
Mono is verified on screen there. macOS kitty keeps Meslo because CoreText does
not flag Obel Mono as monospace, so kitty there falls back to Menlo.

Feature `ss01` masks recognised secrets (`ghp_`, `sk-`, `TOKEN=`,
`Authorization: Bearer`, …) after their first four characters. Only pixels
change: copy, paste, files, and history keep the real value. The part of a key
that wraps onto the next line, and unrecognised formats, stay visible. For one
unmasked window, run `open -na Ghostty --args --font-feature=-ss01`.

## Where things live

| Path | Contents |
| --- | --- |
| [`setup`](setup) | Fresh-host bootstrap and plan mode |
| [`home/`](home) | Chezmoi source tree (`.chezmoiroot` points here) |
| `home/dot_config/` | XDG configuration: shell, mise, terminals, editors, and tools |
| `home/dot_local/bin/` | Installed local commands, including `decent-angl-sync` |
| `home/.chezmoidata/` | Fleet roles, package managers, and UI data |
| `home/private_dot_claude/` | Claude Code director settings and rules |
| `home/private_dot_codex/` | Codex configuration and baseline README |
| `home/private_dot_omp/` | OMP configuration |
| [`utils/`](utils) | Baseline checks and maintenance scripts |
| [`docs/`](docs) | Reference and operational notes |
| [`UPDATING.md`](UPDATING.md) | Publish, reconcile, guard, recovery, and validation |

Host names, fleet roles, and package managers are in
`home/.chezmoidata/decentangl.yaml`.

## Troubleshooting

Start with the sync and health summaries:

```sh
decent-angl-sync status
decent-angl-doctor
decent-angl-doctor --fleet
chezmoi diff
mise doctor
```

Useful verified gotchas:

- `~/.local/share/chezmoi` must point to `~/src/boilerplate`; on an existing
  host, `decent-angl-sync adopt-source` preserves the old source before linking.
- The guard excludes `run_*` hooks but runs `omp-baseline apply` once per revision,
  installing OMP and companion mise pins. Use `decent-angl-sync reconcile --with-scripts`
  only for reviewed hook installations, such as fonts or native prerequisites.
- Working edits are never deployed: ordinary targets are held back, while edits
  to shared chezmoi inputs defer the whole apply. Inspect `decent-angl-sync status`.
- Secrets, auth, history, caches, and databases stay machine-local; do not add
  them to the source checkout.

## References

- [Shell cheatsheet](docs/reference/shell-cheatsheet.md)
- [VS Code shortcuts](docs/reference/vscode-shortcuts.pdf)
- [macOS development storage](docs/macos-development-storage.md)
- [Codex baseline](home/private_dot_codex/README.md)
