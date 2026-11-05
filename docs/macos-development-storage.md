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

The following fully local repositories were checksum-verified under `~/src`. Their former paths are compatibility symlinks. The first eight source/Git archives use the suffix `.icloud-archive-20260726`; the five deeper-audit archives use `.icloud-archive-20260727`. Reproducible dependency and build trees were removed or moved out of those archives after verification.

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
| `GitHub/2025/_angl-advantage` | `~/src/_angl-advantage` |
| `GitHub/2025/angl-comic-scanner` | `~/src/angl-comic-scanner` |
| `GitHub/dev-practice` | `~/src/dev-practice` |
| `GitHub/code-can` | `~/src/code-can` |
| `GitHub/helium-macos` | `~/src/helium-macos` |

`cluewell/server` now uses `~/src/jeopardy` as its local Git remote. An invalid iCloud-created `.git/refs/.DS_Store` from `ascii` is preserved at `~/src/ascii/.git/icloud-artifacts/refs.DS_Store`; the migrated repository passes `git fsck`.

The legacy `~/Documents/google-cloud-sdk` is also a compatibility symlink to Homebrew's `gcloud-cli`. The obsolete SDK archive was removed after `gcloud` 577.0.0 and the existing configuration were verified; credentials and configuration remain under `~/.config/gcloud`.

### Generated-data cleanup

The 27 dependency/build roots omitted from the eight active copies were moved intact to:

```text
~/.local/state/icloud-development-migration/20260726/generated
```

That quarantine contains 8,707,004 KiB (about 8.30 GiB) and preserves paths relative to `~/Documents`. It includes only `node_modules`, `.next`, `.build`, `_build`, virtual environments, and Python bytecode caches. The dated iCloud archives contain none of those 27 roots.

A separate whole-Documents audit found 15,291 top-level matches before nested environments were opened. The cleanup removed 32,858 generated cache/environment directories outside the active Codex task, then removed three verified build-cache leftovers and three caches from inactive Codex task artifacts. The higher removal count includes bytecode caches nested inside structurally verified virtual environments.

A Git-index audit then caught 30,088 tracked files inside generated-looking paths. No tracked deletion was left silent: 59 vendored Copilot files were restored in their inactive Codex artifact, and the other 30,029 files were restored into five newly migrated local project trees (including Helium's nested Chromium repositories). Each destination matches its source outside the intentionally pruned paths and passes `git fsck`. The final Documents audit has nine intentional matches: three Python standard-library source modules named `venv`, five Chromium/Helium source directories named `target`, and the 59-file Git-tracked Copilot dependency snapshot. They were deliberately preserved.

Historical dependency trees removed by the whole-Documents cleanup are not quarantined. They were limited to reproducible paths such as `node_modules`, `.next`, bytecode/test/lint/Turbo caches, structurally verified Python virtual environments (`pyvenv.cfg` present), Swift `.build` beside `Package.swift`, and Rust `target` beside `Cargo.toml`. Reinstall dependencies or rebuild those historical projects before use.

## 2026-11-04 migration

The remaining development trees, device backups, and game data were moved out of iCloud Documents. Every item was fully local (no dataless files) and on the same APFS volume, so each move was a single `rename(2)`: no bytes were copied and no iCloud archive was left behind. Before and after each move, file counts, byte totals, and every repository's `HEAD` and porcelain status were compared; all matched. The log is `~/.local/state/icloud-development-migration/20261104/moves.jsonl`.

| Former path under `~/Documents` | New path | Compatibility symlink |
| --- | --- | --- |
| `GitHub` | `~/src/github` | yes |
| `Codex` | `~/src/codex-app-workspaces` | yes; Codex.app keeps creating task workspaces through it |
| `repos` | `~/src/repos` | yes |
| `mole`, `notion-ai`, `StockModeler`, `rom_reader`, `PokeRNG`, `UNITY_BUILDS` | `~/src/<same name>` | no |
| `Apps`, `Cursor`, `Games` | `~/src/apps`, `~/src/cursor`, `~/src/games` | no |
| `random_usb/backups`, `random_usb/iPhone Backups` | `~/Archive/iphone-backups/random_usb-backups`, `~/Archive/iphone-backups/random_usb-iPhone Backups` | no |
| `random_usb/games`, `valheim_server`, `old 3ds backup` | `~/Archive/games/random_usb-games`, `~/Archive/games/valheim_server`, `~/Archive/games/old 3ds backup` | no |
| every `*.icloud-archive-2026072x` from the July migration | `~/Archive/icloud-migration-july-2026/Documents/<former relative path>` | no |

`.claude.json`, Codex trust entries, and Codex saved workspace roots still name `~/Documents/GitHub/...` and `~/Documents/Codex/...`; the symlinks keep them valid. External Git worktrees for `jeopardy` resolve through `~/Documents/GitHub/jeopardy` → `~/src/github/jeopardy` → `~/src/jeopardy`. FileZilla's local tab path now points at `~/Archive/games/valheim_server`.

`git fsck` passes in all 166 moved repositories except one inactive Codex snapshot (`2026-04-17-is-there-anything-available-to-make/boilerplate-pre-consolidation-2026-04-17`). That snapshot has an iCloud `refs/.DS_Store` and a tmux `tpm` submodule whose module directory never existed. Two iCloud conflict refs were moved into the repositories' `.git/icloud-artifacts/`: `py-finance` `refs/heads/main 2`, an ancestor of `main`, and `music-recs` `refs/remotes/origin/HEAD 2`. The dangling `origin/HEAD` symref in `music-recs` was deleted with `git remote set-head origin -d`.

Restic already covers `~/src`. On the `macbook` it now also includes `~/Archive/iphone-backups`. The rest of `~/Archive` is local-only: the Fortnite packs can be downloaded again, and the July archives duplicate `~/src`.

These stay in iCloud Documents on purpose: music and music-production material, `flipper` (its `Wav_Player` holds music), `career`, `cluewell` design documents, Obsidian vaults, photos, and personal files under `random_usb`.

To reverse one move, stop its processes, remove its compatibility symlink if there is one, and rename the new path back to the former path.

## Future migrations

1. Stop processes whose working directory is inside the source tree.
2. Confirm the destination is new and the source has no cloud-only files.
3. Copy source and Git state while omitting only reproducible, untracked dependency/build caches.
4. Compare included files by checksum, compare Git `HEAD` and tracked status, and run `git fsck` in the destination.
5. Rename the iCloud source to a dated archive, put a compatibility symlink at the old path, and validate the application from `~/src`.

Do not bulk-delete the dated archives until active projects, dirty worktrees, local remotes, and credentials have been exercised from their new locations and a separate backup has completed. Python virtual environments and some build trees contain absolute paths; rebuild them in `~/src` when each project is next used.

## Reversal

For one July project, stop its processes, remove only its compatibility symlink, and rename the corresponding dated `.icloud-archive-YYYYMMDD` directory from `~/Archive/icloud-migration-july-2026/Documents/` back to the original path. Restore a quarantined generated tree only if it cannot be rebuilt; copy its matching relative path from the quarantine back into the restored project. Never run a recursive cleanup against `~/Documents`, `~/src`, or a variable that has not been resolved to one exact project path.
