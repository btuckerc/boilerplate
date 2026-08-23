---
description: You drive. Brainstorm, then spawn. Main does not implement.
---

Read `skill://omp-drive`.

You are driving. Do not edit product code. Do not run project-wide tests.

Topic: $ARGUMENTS

Stay in this mode until the user leaves it.

1. Brainstorm. Ask only when a choice has a real product or architecture tradeoff. Prototype a fact you can run instead of asking it.
2. Same board rules as `/board`. Use `omp-board` for every board write. One slug. Do not touch other slugs. Do not rewrite `in-flight` or `done` cards. Do not use `local://`.
3. Answer the four checkpoint questions. When a card is SMART and unblocked, lock, `overlap` must print `ok`, mark `in-flight` with a lease, write-topic, then spawn. Do not wait for "go" unless the user said outline only. If they want a clean director later, stop after the topic file and tell them `/new` then `/dispatch <slug>`.
4. Prefer `vibe_spawn` `cli: good` when those tools exist. Otherwise `task` with the default worker. Independent cards in one batch. Exclusive file paths only.
5. Answer worker hub questions yourself. Ask the user only if you cannot.
6. After a yield, run the card's proof command or write `unproven`. Re-hash, mark `done`, `index-upsert`. Unlock when idle.
