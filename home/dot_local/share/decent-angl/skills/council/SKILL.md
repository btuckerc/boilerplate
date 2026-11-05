---
name: council
description: Multi-model review or design council that loops until the seats are satisfied. Use only when the user says "council", "full council" or "Sol high council"; seat names in that request pick the seats. Never self-convene.
argument-hint: "[full | seat names] [what to review or decide]"
---

# Council

Independent models review the same evidence. You, the director, verify each
finding, make the fixes and reconvene until every seat is satisfied or the
budget ends. Adapted from Theo Browne's tstack `council` and `sol-loop`
(October 2026).

First check the trigger. If the user did not say "council", stop: your own
consult is the single `architect` described in RULES.md. Outside OMP (Codex),
the seats cannot be dispatched: say so and stop.

## Seats

| Seat | Agent | Emphasis | Sits |
| --- | --- | --- | --- |
| Sol | `architect` | Breaker | default |
| Fable | `fable` | Simplifier | default |
| Astra | `astra` | Outcome | `full council` or named |
| Opus | `opus` | Outcome | `full council` or named; otherwise tiebreaker |

- "Sol high council" seats Sol alone. Named seats replace the default set.
- Seats have read, grep, glob and web_search only: no shell, no edit, no file
  write. They still inherit MCP and xd:// devices, as `architect` always has,
  so the brief forbids those.
- Model and effort come from the agent and the `config.yml` roles. Never pass
  `effort`. Diversity comes from model family, effort and emphasis. Every seat
  rejects or strips temperature.
- Run `omp-quota` first and skip any seat whose pool is under 10%. A seat that
  errors, times out, or served a model other than its role (the
  `model_change` line in its `history://<id>`) is skipped too. Report the
  skip, never substitute a model, and continue as an incomplete council.
  `task.maxConcurrency` is 3, so a fourth seat starts late.

## Packet

Before the first round, fix known issues, address PR comments and run the
checks. Seats review the current work, never known-broken code. The run
directory `~/.local/state/council/<YYYY-MM-DD>-<slug>/` holds everything. It
is machine-local and stays as the archive that `model-eval` replays, so never
overwrite an earlier round's file.

- Candidate: snapshot the intended files without touching the user's index:
  `export GIT_INDEX_FILE=$(mktemp -u); git read-tree HEAD; git add <paths>;
  git write-tree; rm -f "$GIT_INDEX_FILE"; unset GIT_INDEX_FILE`. Write
  `git diff <base> <tree>` to `<run>/diff-rN.patch` for round N. Repeat the
  snapshot after each round: the same tree id proves that no seat changed the
  work.
- `packet.md` (frozen after round 1): the ask, acceptance criteria, explicit
  out of scope, the tree id, the checks run with raw output, and what stays
  untested. Add pointers only, labelled as pointers, not your reasoning. No
  secrets.
- Round 0 is a design question asked before any code exists. Its packet holds
  the question, the constraints and the draft or options.

## Rounds

Dispatch all seats in one `task` batch. Round 1 is independent. Use this
brief:

```
Council seat, round N. Review only; do not use MCP or xd:// devices.
Packet: ~/.local/state/council/<run>/ (packet.md, diff-rN.patch, ledger.md).
Emphasis: <emphasis>. Still cover correctness, scope and user outcome.
Name the single most likely way this ships broken or fails the user, and the
evidence that would change your mind.
blocker = the intended case is wrong or the contract is broken.
should = a real defect within the intent. nit = anything else, including
other paths, rare cases and extra scope.
```

Pass this `outputSchema`:

```json
{"type":"object","required":["score","verdict","top_risk","findings"],"properties":{"score":{"type":"integer","minimum":0,"maximum":10},"verdict":{"enum":["APPROVE","CHANGES"]},"top_risk":{"type":"string"},"findings":{"type":"array","items":{"type":"object","required":["id","severity","location","claim","fix"],"properties":{"id":{"type":"string"},"status":{"enum":["new","resolved","open"]},"severity":{"enum":["blocker","should","nit"]},"location":{"type":"string"},"claim":{"type":"string"},"fix":{"type":"string"}}}}}}
```

Round 0 has no emphases and no schema. Each seat answers in prose with three
parts: its best approach, its strongest objection to the draft, and what to
cut.

Check every finding yourself. You set the final severity.

- Agree: make the smallest fix.
- Disagree: give counter-evidence (file:line, a test, raw output). Settle a
  factual dispute by writing the test or the counterexample.
- Nit or out of scope: decline it in one line and list it as follow-up.

`ledger.md` holds one row per finding, with a neutral id (R1-03), severity,
disposition and evidence. Keep seat attribution in
`local://council-<slug>-seats.tsv`, where seats are not told to look, and
copy it into the run directory when you stop.

**Next round.** Hold one while any seat still says CHANGES and either it has
a fix to confirm or an open blocker/should, or when behavior changed after a
seat approved. Message each seat's existing agent with `write agent://<id>`.
Send the new tree id, `diff-rN.patch`, the updated ledger, and its own ids.
The seat repeats each of its ids with status `resolved` or `open`, and raises
new findings only on changed code.

**Tiebreak.** Some disputes cannot be settled by a test: a blocker or should
that the seat still holds after it has answered your counter-evidence once,
or where seats disagree. Take each one to one fresh `opus`, with only the
claim, the evidence and both arguments. If Opus is seated, use a separate
fresh agent. You wrote the code, so never rule on your own decline. A ruling
closes its item. Applying a ruled fix needs no new round unless it changes
behavior outside that item.

**Budget.** At most 3 rounds, counting round 0, and 2 tiebreaks. Extend only
when the user asks. If review grew the diff, cut first. Do not agree just to
end the loop.

## Stop and report

A seat is satisfied when it approves, or when everything it still holds is a
declined nit or a ruled item. In that case record its dissent. The council is
**done** when every seated member is satisfied and no blocker or should is
open. It is **incomplete** when the budget ends, or no further round is
warranted, before that. Then show each open item with 2-3 lines per side,
and never imply approval. Council approval is advice: a high-consequence
change still needs `/review`, and nothing here overrides an auditor BLOCK or
UNVERIFIED.

Report the rounds, seat availability, fixed and declined findings with
reasons, dissent, open items, and the diff size before and after. Add a score
table with one row per seat and one column per round, under the heading
`## Council review` and a `Rounds: N` line. Write `no score` when a seat gave
none, and never invent one. Put it in the PR description (never a comment)
only when the user asked to ship or update the PR. Otherwise it goes in the
final reply.

## Changing seats

A new candidate model arrives about every 18 days. It earns or keeps a seat
only through the council lane in `model-eval`, which replays archived runs.
Keep one seat per model line (Sol, Fable, Astra, Opus). A same-line upgrade is
the generation upgrade in `omp-config`. A new line needs a role, a read-only
agent file, contracts in `omp-agent-policy`, `omp-agent-smoke` and
`omp-baseline`, a manifest row, and a row in the seat table above.
