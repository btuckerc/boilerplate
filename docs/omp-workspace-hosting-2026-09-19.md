# OMP workspace hosting review — 2026-09-19

The old project is **omp-serve**, not OMP Sync. Its source was
`admin@macmini:~/src/omp-serve` (a symlink to `/Volumes/E0/angl-src/omp-serve`).
The running app used a separate `~/.local/lib/omp-serve` copy. Both source and
deployment were backed up before editing. A local Git baseline and refreshed
checkout now live at `~/src/omp-serve` on the MacBook.

## Host recommendation

| Host | Appropriate work | Current limit |
| --- | --- | --- |
| nous | Linux repo clones, builds, persistent remote workspaces; local bounded workers | Cloud OMP logins not configured; backup policy not established |
| Mini | macOS app automation, Apple builds, Mac-specific dependencies | Model config is still Grok-era despite an updated OMP binary; no native Codex accounts found |
| MacBook | Existing four-account Codex/OMP workflow and computer use | Not the intended long-term central execution host |

`/home/tux/repos -> /srv/workspaces/repos` is the existing canonical path.
The 678 GB Btrfs partition had 668 GB free. It shares one Crucial T500 NVMe
with `/srv/models`; independent partitions do not eliminate device contention.
The i9-13900K/32 GB RAM host is promising, but Linux filesystem choice alone
does not prove faster project builds. Use representative project builds before
claiming a speed advantage. Keep inference stable while evaluating CPU/RAM use.

Use separate clones and Git worktrees for concurrent edits. Git worktrees
provide separate working directories/branches while sharing repository objects:
https://git-scm.com/docs/git-worktree. Do not sync live uncommitted trees in both
directions. Keep the Mac copies and remotes until off-host backup and restore
are verified; empty snapshot directories or snapshots on the same disk are
not an independent backup.

## Verified pilot

- Official Bun 1.3.11 / OMP 18.2.6 Linux executables, SHA256 checked against
  official GitHub release API digests. No global dotfile bootstrap.
- Isolated `~/.local/share/omp-serve-pilot` runtime/config/state. Workspace
  `~/repos/omp-serve-pilot/palette-fixture`; existing `llama.cpp` and
  `Bonsai-demo` checkouts untouched. GPU services were not switched.
- Native Ornith provider at loopback `8080`; no paid fallback or cloud login.
- Full default tool prompt failed at **18,699 > 16,384 tokens**. This is an
  integration limit, not a task-quality result. The error is now visible in UI.
- With `OMP_SERVE_TOOLS=read,write`, Ornith changed three supplied RGB565
  constants in a TypeScript file. Parent ran Bun test independently: 1 pass.
  Browser showed the response and changed file. Download returned exact code.
  Archive/restore restarted OMP and recovered the same two-message transcript.
- Pilot access is tailnet-only `http://100.83.125.83:8745/`, two OMP processes
  maximum. This is a bounded-worker pilot, not the replacement cloud workspace.
- Release `b1837d8` is running under the `omp-serve-pilot` tmux session on
  nous. No boot service was enabled. Attach with
  `ssh -t nous 'tmux attach -t omp-serve-pilot'`; stop with Ctrl-C there;
  restart with `ssh nous 'tmux new-session -d -s omp-serve-pilot /home/tux/.local/share/omp-serve-pilot/run.sh'`.
  Runtime `app` is a symlink to its versioned release. Source is `~/repos/omp-serve`.
- All 12 initial app tests passed on MacBook, Mini, and nous. The final overlay,
  model-picker, and usage-label patch passes 12 tests / 73 assertions. Browser checks
  also caught and fixed an inherited undefined scroll helper and sidebar flow
  bug that syntax tests could not detect.

Release `b1837d8` is active on Mini under
`~/.local/share/omp-serve/releases/b1837d8`, with `~/.local/lib/omp-serve`
pointing to the release and `~/src/omp-serve` pointing to its Git source at
`~/.local/share/omp-serve/source`. Host configuration is
`~/.config/omp-serve/config.json`, linked into the release. Original installed app, source, session
state, launcher, and LaunchAgent are backed up under
`~/.local/state/omp-serve/backups/20260919-before-refresh`. Production on port
8744 was switched after explicit user approval. All nine existing thread IDs
were preserved; native provider credentials/config were left in place. Previous
runtime remains at `~/.local/lib/omp-serve.before-425565f`; original source link
is retained in the backup directory. No accounts were migrated during this rollout.

The desktop settings/app overlays now stack above the sidebar. The current
model badge opens a searchable model picker and shows reasoning effort.
Confirmed native Astra selection and xhigh in Safari without invoking inference.
Model changes on an existing thread use OMP's `set_model` RPC and show any
rejection visibly. New threads inherit native effort unless explicitly chosen.
Model availability reflects the execution host's own configuration and auth.

## App improvements

Portable host paths and direct pinned OMP invocation; no blanket external-volume
rejection. Actual filesystem errors remain visible. Explicit steering/queue and
separate Stop. Reasoning inherits native defaults. Agent questions wait for a
real answer. Model errors appear in the transcript. Workspace Git changes and
file downloads are available. Desktop sidebar and reconnect/history behavior
were checked in Safari against the actual Linux backend.

RPC startup/requests time out, protocol-v2 fragments are decoded with limits,
event history/client queues are bounded, thread-index writes are atomic, and
same-workspace concurrent writers are rejected inside this server. Metadata
reads do not launch OMP. Project recency uses the thread index rather than
rescanning every conversation. Account usage is redacted and cached.

The app remains a trusted single-user tailnet tool. Host/Origin validation is
not authentication; permitted clients can execute tools as the service user.
No public exposure, multi-user permission system, network-mounted working
tree, automatic LLM router, or custom scheduling layer was added.

## Promotion requirements

Choose an execution host before logging in cloud accounts. Native independent
OAuth accounts stay machine-local; do not copy refresh tokens. The MacBook's
four working account entries do not imply four working accounts on the Mini
or nous. The Mini currently has xAI OAuth and a local OpenRouter key; updating
its UI does not finish its provider migration. Keep Luna medium for ordinary
work and Astra for hard planning/review; local models remain bounded workers.

Install app releases from a reviewed commit into a versioned directory and
switch a runtime symlink, preserving `~/.omp/serve` and host-specific config.
Do not duplicate editable source into an untracked installed tree again.
Mac computer tools run where OMP runs; moving sessions to Linux does not forward
the Mini's desktop permissions or Apple apps.
