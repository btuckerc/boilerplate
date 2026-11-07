---
name: council
description: Multi-model review or design council that loops until the seats are satisfied. Use only when the user says "council", "full council" or "Sol high council"; seat names or a target ("push a 9.5", "+0.2") in that request shape it. Never self-convene.
argument-hint: "[full | seat names] [to N | +D] [what to review or decide]"
---

# Council

Models from different families review the same evidence independently. You,
the director, verify each finding, fix, and reconvene until every seat is
satisfied or another round adds nothing. Adapted from Theo Browne's tstack
`council` and `sol-loop`. Independent first opinions carry most of the value
and reviewer precision is low, so verification is your job.

First check the trigger. If the user did not say "council", stop: your own
consult is the single `architect` described in RULES.md. Outside OMP (Codex),
the seats cannot be dispatched: say so and stop.

## Seats

| Seat | Agent | Emphasis (goes in the brief) | Sits |
| --- | --- | --- | --- |
| Sol | `architect` | Breaker: make it fail | default |
| Fable | `fable` | Simplifier: what to cut | default |
| Astra | `astra` | Scenario: walk the real use end to end | `full council` or named |
| Opus | `opus` | Skeptic: attack the packet's assumptions | default |

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
  substitute, and continue as an incomplete council.

## Packet

Before round 1, fix known issues and run the checks: seats review the current
work, never known-broken code. Seats read from the run directory
`~/.local/state/council/<YYYY-MM-DD>-<slug>/` and, for context, the working
tree, which must match the candidate until they return. If it does not, or
you may edit before then, export each tree you build to a new directory
(`mkdir <run>/tree-rN && git archive <tree> | tar -x -C <run>/tree-rN`) and
point that round's seats there.

- Candidate: a commit, or for uncommitted work a tree built without touching
  the user's index: `export GIT_INDEX_FILE=$(mktemp -u); git read-tree HEAD;
  git add <paths>; git write-tree; rm -f "$GIT_INDEX_FILE"; unset
  GIT_INDEX_FILE`. Write `git diff <base> <tree>` to `diff-r1.patch`; from
  round 2, rebuild the tree and write `git diff <previous tree> <tree>` to
  `delta-rN.patch`.
- `packet.md`, frozen after round 1: the ask, acceptance criteria, what is out
  of scope, the tree id, the checks with raw output, and what stays untested.
  Pointers are labelled as pointers. Never include your reasoning, earlier
  reviews or scores, the target, or secrets.
- One concern per council. For mixed work, tell the user and suggest
  splitting the work itself; never clip a diff silently.
- Round 0 is an optional design question before any code exists: the packet
  holds the question, constraints and options. Seats answer in prose with
  their best approach, strongest objection and what to cut; no emphasis, no
  schema. A design-only council ends there with the recommended approach, the
  objections that stand and what to cut; scores and targets start in round 1.

## Rounds

Dispatch every seat from one eval cell so all start at once (`task` batches
queue behind `task.maxConcurrency`); round 1 is independent. One call per
seat: `agent(<whole brief>, agent="<agent>", label="<Slug>Seat<Name>1",
schema=<schema below>)`; `agent()` takes no shared context, and the label must
be CamelCase and unique in the session. Results auto-deliver; when blocked,
call the `wait` tool, not `.wait()`. A seat still running after 30 minutes has
timed out: `.cancel()` it. Brief, with a distinct id letter per seat:

```
Council seat, round 1. Review only; do not use MCP or xd:// devices.
Packet: ~/.local/state/council/<run>/packet.md and diff-r1.patch.
Emphasis: <emphasis>. Still cover correctness, scope and user outcome.
Judge from the code and evidence, not from other reviewers' findings.
In top_risk, name the single most likely way this ships broken or fails the
user.
Each finding (ids <letter>-01, -02, ...): exact location, the concrete
failure, and the evidence that would change your mind. blocker = the intended
case is wrong or the contract is broken. should = a real defect within the
intent, on any supported path. nit = anything else, including extra scope.
Score with one decimal, e.g. 8.6. The integer is the band: 10 nothing to fix
or cut; 9 ship, nits only; 7-8 shoulds open; 5-6 a blocker; below 5 wrong
approach. The tenth ranks the work within its band. APPROVE means no blocker
or should. In raise, name the change that would most raise your score, or
none. From round 2, list in basis the ids behind any score change.
```

Pass this `schema`:

```json
{"type":"object","required":["score","verdict","top_risk","raise","findings"],"properties":{"score":{"type":"number","minimum":0,"maximum":10},"verdict":{"enum":["APPROVE","CHANGES"]},"top_risk":{"type":"string"},"raise":{"type":"string"},"basis":{"type":"array","items":{"type":"string"}},"findings":{"type":"array","items":{"type":"object","required":["id","severity","location","claim","fix"],"properties":{"id":{"type":"string"},"status":{"enum":["new","resolved","open"]},"severity":{"enum":["blocker","should","nit"]},"location":{"type":"string"},"claim":{"type":"string"},"fix":{"type":"string"}}}}}}
```

Check every finding yourself; you set the final severity. Agreement between
seats is not proof.

- Agree: make the smallest fix.
- Disagree: give counter-evidence (file:line, a test, raw output). Settle a
  factual dispute by writing the test or the counterexample.
- Nit: fix it if cheap; otherwise decline it in one line and list it as
  follow-up. Out of scope: decline it the same way.

Keep one ledger in `local://council-<slug>-ledger.md`: id, seat, severity,
disposition, evidence.

**Next round.** Hold one while a seat has an open blocker or should or a fix
to confirm, while behavior changed after it approved, or while it is below a
target and its raise names a change you accept. Nit fixes, and wording fixes
that keep the meaning, need no round. Message only those seats' existing
agents (all seats when there is a target) with the handle's `.send(...)` or
`write agent://<id>`, carrying only:

```
Council seat, round N. Tree <id> in <run>/tree-rN; delta: <run>/delta-rN.patch.
Checks: <raw output or path>. Your rows: <id, disposition, evidence>.
Mark each of your ids resolved or open, raise new findings on changed code or
any blocker or should you missed in scope, and re-score, listing in basis
the ids behind any change. Reply by calling yield with the round-1 schema,
not by message.
```

The first line starts a round for `omp-council-yield`; a bounce or ruling
sent on its own must not start with it. Never restate the question, add a
verdict or scale, or send other seats' findings.

A score outside the band its own open findings set, APPROVE with a blocker or
should open, or a score change with no ids in basis goes back to the seat once
with the mismatch; if it stands, that seat is not satisfied.

**Target.** "push a 9.5" or "to N" needs every seat at N or above; "+0.2"
needs every seat 0.2 above its own round-1 score (10 counts as met). A seat
re-scores in the context where it judged the earlier work, so the step is a
comparison, not a fresh guess. A fix, evidence the seat accepts, or a ruling
can move a score; persuasion cannot. A raise is a finding like any other.
Seats never learn that a target exists: no packet, brief or message names it,
the stop rule, a seat's distance from it, or another seat's score, and every
round asks every seat the same thing.

**Tiebreak.** A blocker or should the seat still holds after answering your
counter-evidence once, or one the seats disagree on, goes to one fresh
`opus` agent, never a seat, with only the claim, the evidence
and both arguments. You wrote the code, so never rule on your own decline. A
ruling closes its item; new evidence makes a new finding. Pass the ruling to
the seat with the next message. Applying it needs no round unless it changes
behavior outside that item.

**No round cap.** Keep going while a round is warranted. Stop when none is,
when a round brings no verified blocker or should and no accepted raise
(declined and ruled items add nothing), or when a behavior comes back a second
time after a fix meant to keep both items: the fixes are oscillating, so
report both sides. If review grew the diff, cut first. Never agree just to end the
loop.

## Stop and report

A seat is satisfied when it approves, or when all it still holds are declined
nits or ruled items (record that dissent); with a target it must also meet
it. The council is **done** when every seated member is satisfied
and no blocker or should is open, and **incomplete** when it stops before
then: show each open item with 2-3 lines per side and never imply approval.
Council approval is advice: a high-consequence change still needs `/review`,
and nothing here overrides an auditor BLOCK or UNVERIFIED.

Report rounds, seat availability, fixed and declined findings with reasons,
dissent, open items, the diff size before and after, and the fixes made
after the last round, with the checks rerun on the final tree. Remove the
run's `tree-r*` exports. Then run

```
omp-council-yield add <run> <lines> <id>=<alone>/<shared>/<declined> ... [<id> ...]
```

where `<run>` is the run directory name, with one counted id per seat that
sat a scored round and bare ids for round-0 and tiebreak agents. lines is insertions plus deletions from
`git diff --shortstat <base> <tree>` for round 1; alone and shared count the
seat's verified blockers and shoulds; declined counts its findings you
rejected or downgraded. It reads model, cost and time from the seats'
transcripts, appends to the machine-local `~/.local/state/council/yield.tsv`,
and prints the per-round table (score, duration, cost). Put that table under
`## Council review` with a `Rounds: N` line: in the PR description (never a
comment) only when the user asked to ship or update the PR, otherwise in the
final reply.

## Changing seats

Seats are added, dropped or upgraded only through the council lane in
`model-eval`, and the user decides. A same-line upgrade is the generation
upgrade in `omp-config`. A new line needs a role, a read-only agent file,
contracts in `omp-agent-policy`, `omp-agent-smoke` and `omp-baseline`, a
manifest row, and a row in the seat table above.
