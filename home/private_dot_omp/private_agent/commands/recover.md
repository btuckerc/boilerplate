---
description: Reconcile orphan in-flight board cards in this cwd. Do not reset the board.
---

Read `skill://omp-drive`.

You recover. You do not implement product code. You do not spawn unless the user then types `/dispatch`.

Slug: $ARGUMENTS
If empty, use `omp-board active`.

1. `omp-board lock <slug>`. Exit 75 means stop.
2. `omp-board orphans <slug>` and `hub list`.
3. Live worker in this session: leave that card. Say so.
4. Orphan: read the owned files. If the work is present, mark `done` and clear the lease. If not, mark `blocked` and keep the stale lease in a note. Add a new `pending` card only if the user wants a retry.
5. `write-topic --expect <hash>`. `index-upsert` the Open count.
6. `omp-board unlock <slug>`. Print what changed. Do not spawn.
