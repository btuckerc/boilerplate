---
description: Outline SMART tasks into one cwd board topic. Do not implement or spawn.
---

Read `skill://omp-drive`.

You are the board, not the implementer. Do not edit product code. Do not spawn workers.

Topic: $ARGUMENTS

Boards are `$PWD/docs/board`. Not `local://`. Not another repo.

1. `omp-board init`. `omp-board slug` the topic. Empty topic uses `omp-board active`. If Active is none, stop and ask for a topic.
2. `omp-board lock <slug>`. Exit 75 means stop.
3. Read the current topic if `omp-board hash <slug>` is not `missing`. Touch only that slug.
4. Ask only when a choice has a real product or architecture tradeoff.
5. Write the topic on stdin to `omp-board write-topic <slug> --expect <hash>`. Keep `in-flight` and `done` cards byte-for-byte unless the user named them. "Start over" copies the file to `docs/board/archive/<slug>-YYYYMMDD.md` first.
6. `omp-board overlap <slug>` must be `ok` or stop and split the cards.
7. `omp-board index-upsert <slug> --title "<title>" --open <pending+in-flight> --active`
8. Init the parent todo from this slug only. Block cards that wait.
9. `omp-board unlock <slug>`. Stop. Show the slug. The user types `/dispatch` or `/drive` continues in another command.
