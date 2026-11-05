---
name: council
description: Multi-model review or design council that loops until the seats are satisfied. Use only when the user says "council", "full council" or "Sol high council"; seat names or a target score ("push a 9") in that request shape it. Never self-convene.
argument-hint: "[full | seat names] [to N] [what to review or decide]"
---

# Council

Models from different families review the same evidence independently. You,
the director, verify each finding, fix, and reconvene until every seat is
satisfied or the budget ends. Adapted from Theo Browne's tstack `council` and
`sol-loop`. Independent first opinions carry most of the value and reviewer
precision is low, so verification is your job.

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
- Seats can read, grep, glob and web_search; they cannot run a shell, edit or
  write files. They still inherit MCP and xd:// devices, so the brief forbids
  those.
- Model and effort come from the agent files and `config.yml` roles; never
  pass `effort`. No seat accepts a temperature: diversity is model family,
  effort and emphasis.
- Run `omp-quota` before each round and skip a seat whose pool is under 10%.
  Also skip a seat that errors, times out, or served another model than its
  role (the `model_change` line in `history://<id>`). Report each skip, never
  substitute, and continue as an incomplete council. `task.maxConcurrency` is
  3, so a fourth seat starts late.

## Packet

Before round 1, fix known issues and run the checks: seats review the current
work, never known-broken code. Everything lives in the run directory
`~/.local/state/council/<YYYY-MM-DD>-<slug>/`, which stays machine-local as
the archive `model-eval` replays. Never overwrite an earlier round's file.

- Candidate: a commit, or for uncommitted work a tree built without touching
  the user's index: `export GIT_INDEX_FILE=$(mktemp -u); git read-tree HEAD;
  git add <paths>; git write-tree; rm -f "$GIT_INDEX_FILE"; unset
  GIT_INDEX_FILE`. Write `git diff <base> <tree>` to `diff-r1.patch`; from
  round 2, rebuild the tree and write `git diff <previous tree> <tree>` to
  `delta-rN.patch`.
- `packet.md`, frozen after round 1: the ask, acceptance criteria, what is out
  of scope, the tree id, the checks with raw output, and what stays untested.
  Pointers are labelled as pointers. Never include your reasoning, earlier
  reviews or scores, or secrets.
- Round 0 is an optional design question before any code exists: the packet
  holds the question, constraints and options. Seats answer in prose with
  their best approach, strongest objection and what to cut; no emphasis, no
  schema.

## Rounds

Dispatch all seats in one `task` batch; round 1 is independent. Brief, with a
distinct id letter per seat:

```
Council seat, round 1. Review only; do not use MCP or xd:// devices.
Packet: ~/.local/state/council/<run>/packet.md and diff-r1.patch.
Emphasis: <emphasis>. Still cover correctness, scope and user outcome.
Judge from the code and evidence, not from other reviewers' findings.
Name the single most likely way this ships broken or fails the user.
Each finding (ids <letter>-01, -02, ...): exact location, the concrete
failure, and the evidence that would change your mind. blocker = the intended
case is wrong or the contract is broken. should = a real defect within the
intent. nit = anything else, including other paths, rare cases and extra scope.
Score: 10 nothing to fix or cut; 9 ship, nits only; 7-8 shoulds open;
5-6 a blocker; below 5 wrong approach. APPROVE means no blocker or should.
```

Pass this `outputSchema`:

```json
{"type":"object","required":["score","verdict","top_risk","findings"],"properties":{"score":{"type":"integer","minimum":0,"maximum":10},"verdict":{"enum":["APPROVE","CHANGES"]},"top_risk":{"type":"string"},"findings":{"type":"array","items":{"type":"object","required":["id","severity","location","claim","fix"],"properties":{"id":{"type":"string"},"status":{"enum":["new","resolved","open"]},"severity":{"enum":["blocker","should","nit"]},"location":{"type":"string"},"claim":{"type":"string"},"fix":{"type":"string"}}}}}}
```

Check every finding yourself; you set the final severity. Agreement between
seats is not proof.

- Agree: make the smallest fix.
- Disagree: give counter-evidence (file:line, a test, raw output). Settle a
  factual dispute by writing the test or the counterexample.
- Nit or out of scope: decline it in one line and list it as follow-up.

Keep the ledger, one row per finding (neutral id R1-03, severity,
disposition, evidence), and the seat attribution in
`local://council-<slug>-ledger.md` and `-seats.tsv`, where no seat looks. At
stop, copy them into the run directory as `ledger.md` and `seats.tsv`.

**Next round.** Hold one while a seat has an open blocker or should or a fix
to confirm, while behavior changed after it approved, or while it is below a
target and has named what would raise it. Nit fixes, and wording fixes that
keep the meaning, need no round. Message each seat's existing agent (`write
agent://<id>`) with the new tree id, `delta-rN.patch` and only its own ledger
rows. It marks each of its ids `resolved` or `open`, raises new findings only
on changed code, and re-scores.

**Target.** "push a 9" or "to N" makes every seat's score at N or above part
of done. A fix, evidence the seat accepts, or a ruling can move a score;
persuasion cannot. Ask a seat below target with nothing open, once, what
would raise it; its answer is a finding like any other.

**Tiebreak.** A blocker or should the seat still holds after answering your
counter-evidence once, or one the seats disagree on, goes to one fresh
`opus` (a separate agent if Opus is seated) with only the claim, the evidence
and both arguments. You wrote the code, so never rule on your own decline. A
ruling closes its item; pass it to the seat with the next message. Applying it
needs no round unless it changes behavior outside that item.

**Budget.** 3 rounds counting round 0, 5 with a target, and 2 tiebreaks.
Extend only when the user asks. If review grew the diff, cut first. Never
agree just to end the loop.

## Stop and report

A seat is satisfied when it approves, or when all it still holds are declined
nits or ruled items (record that dissent); with a target it must also score
at N or above. The council is **done** when every seated member is satisfied
and no blocker or should is open, and **incomplete** when the budget ends or
no round is warranted before then: show each open item with 2-3 lines per
side and never imply approval.
Council approval is advice: a high-consequence change still needs `/review`,
and nothing here overrides an auditor BLOCK or UNVERIFIED.

Report rounds, seat availability, fixed and declined findings with reasons,
dissent, open items, and the diff size before and after. Add a score table,
one row per seat and one column per round, under `## Council review` with a
`Rounds: N` line; write `no score` when a seat gave none. It goes in the PR
description (never a comment) only when the user asked to ship or update the
PR, otherwise in the final reply.

## Changing seats

A new candidate model arrives about every 18 days. It earns or keeps a seat
only through the council lane in `model-eval`, which replays archived runs.
Keep one seat per model line (Sol, Fable, Astra, Opus). A same-line upgrade is
the generation upgrade in `omp-config`. A new line needs a role, a read-only
agent file, contracts in `omp-agent-policy`, `omp-agent-smoke` and
`omp-baseline`, a manifest row, and a row in the seat table above.
