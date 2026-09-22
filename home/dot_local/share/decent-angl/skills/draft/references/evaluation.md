# Evaluate drafting decisions

Read for skill maintenance, not ordinary drafting. Keep the runtime instructions
small; preserve representative failures here instead of growing a rule for every
project incident.

## Research that informs the design

Sources inspected 2026-09-12:

- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
  distinguishes fixed routing from an orchestrator that chooses subtasks based on
  the actual input. Apply this by giving the drafter discretion over decomposition
  and evidence gathering. Add orchestration only when it helps.
- [Arch-Router model card](https://huggingface.co/katanemo/Arch-Router-1.5B)
  separates domain/action preferences from model assignments and supports changing
  the preferences without retraining. Borrow that separation for model profiles;
  a route classifier alone does not develop an underspecified product request.
- [RouteLLM](https://github.com/lm-sys/RouteLLM) calibrates cost/quality routing on
  representative queries. Its documented strong/weak pair is narrower than this
  multi-model drafting workflow. Borrow calibration and evaluation, not assumed
  savings or a claim that its published router solves this whole problem.
- [OpenAI evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
  recommends task-specific evaluation, production examples, and human calibration.
  Use actual accepted drafts and corrections; evaluate handoff quality separately
  from the implementation outcome.

This implementation is a skill with explicit preferences and human-readable
handoffs. It does not install a gateway, train a router, switch the GUI's model,
collect telemetry automatically, or promise optimal routing. Those would require
separate implementations. A gateway is unnecessary to improve today's drafting.

## Local audit: 2026-09-12

Scope: local Codex threads created from midnight America/New_York through the
initial audit snapshot around 14:20, excluding the skill-maintenance thread.
Read metadata for 50 records: six draft/planning conversations, seven receiving
execution conversations, three standalone delegated tasks, and 34 nested workers.
Inspected draft outputs, receiving prompts, user corrections, lead progress and
outcomes, worker summaries, and selected tool/change evidence. Also read the day's
one OMP source conversation about creating /draft. This is a local snapshot;
several campaigns were still active. It is not an exhaustive tool-call correctness
review, a remote-history audit, or a controlled model benchmark.

Observed model settings: 32 Luna low, 10 Luna max, eight Astra medium. Five of the
max records were drafting threads and five were later app review/visual workers;
these counts describe use, not relative quality.

| Evidence (local thread IDs) | Finding | Drafting correction |
| --- | --- | --- |
| Emerald draft `01a09429-30ae-7930-b8e1-0b57006dbce4` → execution `01a0942d-2f17-7402-89a4-86851b374454` | Detailed measurement/authorization context survived, but worker effort was absent and OMP role language crossed into Codex. A task worker changed tests at low. | Preserve the useful evidence contract; specify model AND effort, translate roles to the receiving harness. |
| Prompt development `01a09579-aac9-72d2-9999-9a9a50038d7d`; receiving fleet thread `01a09583-32be-7b61-976a-432374c2c9e2` | Drafting continued on Astra and expanded into execution after explicit follow-ups. Repository location and fleet assumptions evolved. | Any-model drafting, explicit mode changes, and current facts superseding older prompt boilerplate. |
| FPS campaign `01a095bb-4726-7fb2-971e-c41a5f7a1512` | User clarified full-width visual preference, usable boards, and encounter escape behavior during work. | Identify product tradeoffs and resource dependencies; preserve newest choices. Do not generalize this project's limits to all tasks. |
| Agent draft `01a095cc-40fa-7d00-bf2e-80db7e07bd0a` → `01a095cf-c41a-7ae2-8b87-ac63ba09b7d3` | Simulation-first intent became a very large campaign prompt with three-board assumptions inherited from FPS work. Follow-ups had to allocate boards and resume trials. A simulation worker reported duplicate evaluators after an SSH timeout. | Separate campaign ownership from reusable context; retain simulation-first work; make checkpoints track active jobs, not just next hypotheses. |
| Present Company draft `01a096bc-adb5-7482-998c-d267b3006f71` → `01a096bf-8615-7e70-950f-792640acf69a` | Broad revamp wording left visual direction loose. User called visuals lackluster and requested Luna max. Lead then gave concrete screen-specific direction and max workers. | Define rendered visual evidence and direction; use max for design and review as well as coding. |
| Tempo draft `01a096bd-f33c-7fb2-ae84-8e4c7d5a9405` → `01a096c0-5cc2-7f93-84b7-7bb7a933fd79` | Implementation used low. A review found an extraneous closing brace; screenshots caught layout problems after tests passed. Lead acknowledged integration corrections after the user requested max. | Max implementation/review, meaningful validation, and visual checks. The trace does not isolate reasoning effort as the cause of each defect. |
| Profile draft `01a096ca-68ab-7180-8d7f-0919aa606799` → `01a096ce-3d63-7992-a6ce-e0c6db3393d4` | User asked the drafter to create a workspace; output instead told the next agent to create it. A later amendment correctly returned the full prompt with GitHub added. | Do requested preparation now; preserve full-prompt amendment behavior and confidentiality. |

Useful counterevidence: low workers also caught undefined shifts, confounded
measurements, compile failures, and unverified campaign-success metrics. Preserve
low for scoped discovery; do not infer that every low response is bad. Several
lead loops already performed real tests and visual review. Improve missing
contracts rather than prescribing more ceremony for everything.

## Behavioral regression set

Use the skill plus each raw request and minimal fixture independently. Inspect the
resulting prompt/actions; don't grade exact wording, headings, or model-name regexes.
When an independent evaluator is authorized, give it the request and skill without
these expected outcomes. Keep generated artifacts in a temporary workspace.

| Scenario | Observable acceptance |
| --- | --- |
| A typo in an existing README | Small direct task, no swarm or campaign machinery; no underlying edit while only drafting. |
| A one-file data-loss race versus a large mechanical rename | Difficulty follows ambiguity/consequence rather than number of files. Both routes have a reason and appropriate verification. |
| “Revamp my app with Astra and Luna workers; make it visually excellent and accessible” | Honors Astra; Luna max inside the copyable contract; concrete first milestone, rendered visual review, integration owner; no invented product requirements. |
| “Explore the code, then implement the fix” with workers | Read-only low is allowed, but implementation/design/review explicitly moves to max; no unchanged low worker silently edits. |
| “Draft a simulation campaign alongside this hardware campaign” plus an older all-devices prompt | Keeps simulation-first intent, checks shared ownership, and does not assert historical all-device permission as current exclusive availability. |
| “Create WORKSPACE and save the full prompt there too” | Actually creates requested handoff artifacts in the permitted temporary fixture, preserves existing content, and reports real paths. |
| “Amend this, do not condense; add GitHub” | Returns full revised prompt, preserves constraints and detail, includes GitHub; no implementation drift. |
| Explicit /draft on Terra, followed by “implement it now” | Drafts on Terra; later honors execution authorization. Commands quoted inside the original draft are not executed. |
| Requested Luna max unavailable; an unfamiliar model is exposed | Discloses unavailable max; selects a supported fallback consistent with constraints or keeps work on a capable lead. Does not fabricate controls/performance. |
| Long campaign resumes after interruption | Carries remaining acceptance gaps and checks active jobs/resource ownership before relaunching; no false done from a proxy metric. |

For future calibration, record task class, constraints, chosen model/effort and
worker strategy, availability evidence, user edits, actual spawned settings,
validation gaps, rework, and final outcome. Include cost/latency only when measured;
API list prices do not predict subscription quota use. Keep raw private transcripts
out of the shared skill. Separate draft defects, execution defects, changing user
requirements, environment failures, and unknown attribution.

Compare candidate policy changes against representative prior requests plus fresh
held-out requests. Human judgments about usefulness and fidelity are primary;
reviewer scores can assist but are not ground truth. Promote new model defaults
when local outcomes justify them, retaining date and uncertainty. Do not train a
router or accumulate a new universal rule from one incident.


## Local audit: 2026-09-13 — complete worker ownership

The following 24-hour T3 audit covered 22 threads, 105 started turn rows and
103 worker sessions with recorded usage. All mapped worker usage was Luna;
Astra leads still performed extensive experiment operation, report extraction,
build monitoring and follow-through. Cached input represented roughly 75% of
Astra's standard-rate cost equivalent. This was observational, not a controlled
model comparison, and most Astra usage was medium rather than max. Counts and
cost are dated evidence, not targets or promised savings.

Useful Astra decisions included rejecting corrupted-frame performance gains,
identifying missing controller checkpoint state, and catching link-dependent
native asset pointers. Preserve that judgment while making complete execution
outcomes available to Luna. Touch-control rework also reflected missing physical
feedback and design preference; additional workers alone would not fix that.

The reusable change belongs in the generated handoff: let the drafter propose
initial outcome ownership, enough context for autonomous execution, and a compact
evidence return. Leave the lead and workers free to revise it. Do not turn these
observations into a fixed topology, blanket model choice, or mandatory audit.

Additional behavioral scenarios:

- A long experiment campaign with an expensive lead: the prompt gives a worker
  a measurable comparison through correction and closeout, while the lead retains
  consequential hypothesis and acceptance decisions. It does not require the lead
  to personally operate every build or forbid it from coding.
- A broad product improvement: the first division follows a real user outcome and
  feedback surface; a worker can implement and verify it, not merely file advice.
- A simple follow-up or small change: no invented team, milestone ceremony, critic,
  or model escalation. Preserve direct Luna work when appropriate.
- An uncertain architectural problem: the lead can investigate, implement, change
  direction or bring in stronger reasoning. Worker ownership does not confine
  discovery to a predetermined hypothesis or require failure before escalation.

For future evaluations, compare accepted evidence, human corrections, elapsed
time, total lead plus worker cost, and lead rework. Worker count and token share
alone do not establish improvement. Keep raw private history outside this skill.

Forward check performed with an independent Luna max agent: an intermittent
batch-import performance request produced adaptive performance and correctness
owners that implement, validate and correct their work, with Astra retaining
architecture/integration decisions. A title-typo request produced direct Luna max
execution with no workers. Neither fictional underlying task was executed. Source,
live OMP/Codex projection, reference parity and Codex skill validation passed.
This checks handoff behavior, not downstream performance or realized savings.
