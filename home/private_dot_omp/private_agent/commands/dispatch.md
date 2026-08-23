---
description: Spawn workers for one cwd board topic.
---

Read `skill://omp-drive`.

You are the dispatcher. Do not edit product code yourself.

Slug: $ARGUMENTS
If empty, use `omp-board active`. If none, or the topic file is missing, stop.

1. `omp-board lock <slug>`. Exit 75 means stop.
2. `omp-board orphans <slug>`. Do not spawn over an orphan. Tell the user to `/recover` if any exist.
3. Skip `in-flight` and `done`. You did not start those workers.
4. `omp-board overlap <slug>` must print `ok`. If it exits 2, stop and split ownership.
5. For each unblocked `pending` card you will spawn: set Status to `in-flight`, add a Lease line, `write-topic --expect <current-hash>`, then spawn. Prefer `vibe_spawn` `cli: good` when those tools exist. Otherwise one `task()` batch with the default worker.
6. After a yield, re-hash, mark `done` or `blocked`, `index-upsert` the Open count, update the todo, next pending wave.
7. Hold blocked cards. `omp-board unlock <slug>` when the wave is idle.

Workers hub Main.
