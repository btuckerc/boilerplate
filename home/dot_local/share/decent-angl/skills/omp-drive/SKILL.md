---
name: omp-drive
description: Use when the user types /drive, /board, /dispatch, /recover, /vibe, or says drive or swarm. Outline SMART tasks into the cwd board, spawn workers, answer hub questions. Main does not implement.
argument-hint: "[board|dispatch|drive|recover]"
---

# OMP drive

Default chat implements the request itself. This skill is the other mode.

Boards are always `$PWD/docs/board`. A session started in `~/tmp` writes `~/tmp/docs/board`. It must not write another repo's board. `local://` is not a board.

## Commands

| You type | What happens |
|---|---|
| `/board <idea>` | Write SMART cards. Do not spawn. |
| `/dispatch` | Spawn workers for the Active slug. |
| `/dispatch <slug>` | Spawn that topic. Works after `/new`. |
| `/drive <idea>` | Write the board, then spawn. |
| `/vibe` then `/dispatch` | Same list. Workers stay until `/vibe` is turned off. |
| `/recover [slug]` | Inspect orphan `in-flight` cards. Do not reset the board. |

Project `.omp/commands` override these. Present Company keeps its own luna/SLOT commands.

## Files

| Path | Role |
|---|---|
| `docs/board.md` | Index. Active slug plus one row per topic. |
| `docs/board/<slug>.md` | Cards for that topic. |
| `docs/board/<slug>-*.md` | Contracts for that topic. |
| `docs/board/archive/` | Old copies after "start over". |

Locks live in `~/.local/state/omp-board/<cwd-hash>/`. They are not git files.

## `omp-board`

Every board mutation goes through `omp-board`. Do not `write`/`edit` board files directly.

```
omp-board init
omp-board slug "<topic>"
omp-board lock <slug>
omp-board hash <slug>
omp-board write-topic <slug> --expect <hash>   # stdin is the new file
omp-board overlap <slug>                       # exit 2 = refuse spawn
omp-board orphans <slug>
omp-board index-upsert <slug> --title "..." --open N --active
omp-board unlock <slug>
```

`write-topic` fails (exit 76) if the file changed since `--expect`. Re-read, merge, retry once. `index-upsert` updates one row under its own index lock. Do not rewrite `docs/board.md` as a whole file.

## SMART card

```
# Status
pending | blocked | in-flight | done

# Target
exact files and symbols; explicit non-goals

# Change
steps, APIs, patterns to reuse

# Acceptance
observable result; no project-wide commands

# Blockers
what must finish first

# Ownership
exclusive paths this worker may edit

# Lease
host=<host> pid=<omp-pid> session=<id> expires=<ISO-8601>
```

Set `Lease` when you mark `in-flight`. Clear it when the card becomes `done` or `blocked`.

## Order

1. `omp-board lock <slug>`. If exit 75, stop. Another dispatcher holds it.
2. Shared contracts in `docs/board/<slug>-*.md` before fan-out.
3. `omp-board overlap <slug>` must print `ok` before any spawn.
4. Independent cards in one batch. A dependent card waits until you have read the upstream files.
5. Mark `in-flight` with a lease, `write-topic` with the current hash, then spawn.
6. Prefer `vibe_spawn` `cli: good` when those tools exist. Otherwise `task` with the default worker. Do not invent a model id.
7. After a yield, re-hash, mark `done` or `blocked`, `index-upsert` the Open count, next wave.
8. `omp-board unlock <slug>` before you stop.

Cap 3 unless the project overlay sets a higher `task.maxConcurrency` and the cards are disjoint.

## Recover

`in-flight` is not proof a worker is alive.

1. `omp-board orphans <slug>`
2. `hub list` in this session only
3. Live worker: leave the card. Message it.
4. Orphan: read the files. Mark `done` only if the work is there. Otherwise `blocked` with the stale lease in the note, then a new `pending` card. Never wipe every in-flight card.

Cancel with `hub cancel` and the job ids from this session. Then run `/recover`. Cancel does not undo file writes.

## Out of scope

No extra MCP. No marketplace. No CrewAI or LangGraph. Do not enable `task.prewalk` here. Do not write outside `$PWD`. Do not edit a sibling repo from the wrong cwd.
