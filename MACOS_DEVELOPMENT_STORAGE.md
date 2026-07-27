# macOS development storage

Use `~/src` for repositories, package trees, virtual environments, build output, SDKs, and Codex workspaces. Keep iCloud-managed `~/Documents` and `~/Desktop` for human-authored documents that benefit from synchronization.

## Why

On the `macbook`, source and build churn under iCloud-managed Documents produced a multi-gigabyte File Provider metadata workload. After the macOS 26.5.2 restart, `fileproviderd` consumed 84–96% of one CPU core for more than an hour while doing local SQLite work. Development trees amplify this workload because dependency installers and compilers create, rename, lock, and delete many small files.

## Guardrails

- `PROJECTS_ROOT` and `DEV_DIR` default to `~/src`.
- `dev` changes to that root; `mkproject <name>` creates a project there and enters it.
- On macOS, zsh warns once per project when a Git/package tree or dependency environment is entered under iCloud-managed Desktop or Documents.
- The first Ghostty window starts in `~/src`; later windows, tabs, and splits retain Ghostty's normal directory inheritance.
- Shared Codex guidance directs new repositories, build trees, virtual environments, and workspaces to `~/src`.

## 2026-07-26 migration

The following fully local repositories were checksum-verified under `~/src`. Their former paths are compatibility symlinks, and the untouched source trees remain beside them with the suffix `.icloud-archive-20260726`.

| Former path under `~/Documents` | Active local path |
| --- | --- |
| `trade-roads` | `~/src/trade-roads` |
| `money` | `~/src/money` |
| `synth-analyzer` | `~/src/synth-analyzer` |
| `career/job-hunt` | `~/src/job-hunt` |
| `decent-angl` | `~/src/decent-angl` |
| `GitHub/2025/ascii` | `~/src/ascii` |
| `cluewell/server` | `~/src/cluewell/server` |
| `GitHub/jeopardy` | `~/src/jeopardy` |

`cluewell/server` now uses `~/src/jeopardy` as its local Git remote. An invalid iCloud-created `.git/refs/.DS_Store` from `ascii` is preserved at `~/src/ascii/.git/icloud-artifacts/refs.DS_Store`; the migrated repository passes `git fsck`.

The legacy `~/Documents/google-cloud-sdk` is also a compatibility symlink to Homebrew's `gcloud-cli`. Its original installation remains at `~/Documents/google-cloud-sdk.icloud-archive-20260726` until cleanup is approved.

## Future migrations

1. Stop processes whose working directory is inside the source tree.
2. Confirm the destination is new and the source has no cloud-only files.
3. Copy source and Git state while omitting only reproducible, untracked dependency/build caches.
4. Compare included files by checksum, compare Git `HEAD` and tracked status, and run `git fsck` in the destination.
5. Rename the iCloud source to a dated archive, put a compatibility symlink at the old path, and validate the application from `~/src`.

Do not bulk-delete the dated archives until active projects, dirty worktrees, local remotes, credentials, and any path-dependent virtual environments have been exercised from their new locations and a separate backup has completed. Python virtual environments and some build trees can contain absolute paths; rebuild them in `~/src` when each project is next used.

## Reversal

For one project, stop its processes, remove only its compatibility symlink, and rename the corresponding `.icloud-archive-20260726` directory back to the original name. Never run a recursive cleanup against `~/Documents`, `~/src`, or a variable that has not been resolved to one exact project path.
