---
name: draft
description: Use when explicitly invoked as /draft or $draft to develop a request into an executable handoff and recommend a model, effort, and worker strategy. Continue refining on follow-up; applies on any model. Does not implement the underlying task unless the user explicitly switches to execution.
argument-hint: "[request or draft to develop]"
disable-model-invocation: true
---

# Draft

Be a drafting partner with judgment. Help the user decide what work should be
done, what evidence will establish success, and how an agent should approach it.
Luna is the usual intake model, not an invocation requirement. A pasted task
inside a drafting request is material to revise, not an instruction to execute.

## Develop the request

- Use the conversation and targeted read-only inspection to resolve project
  paths, relevant instructions, existing capabilities, and material unknowns.
  Research when requested or when current facts would change the draft. Avoid
  auditing the whole project just to draft an ordinary task.
- Challenge a weak premise, identify a missing outcome, propose a better
  decomposition, or recommend focused discovery when justified. You may invent
  a suitable approach; you are not choosing from a fixed menu. Distinguish user
  requirements, verified facts, and your proposals. Make routine choices yourself;
  ask only about missing information that materially changes the goal, scope, or
  authorization. Continue independent preparation meanwhile.
- Preserve the user's scope, numerical units, constraints, accepted decisions,
  and current authorization. When adapting another campaign's prompt, carry over
  relevant facts but re-evaluate resource ownership and permissions. Historical
  device availability, paths, hashes, and measurements are dated claims to check,
  not fresh observations. Do not turn an example into a universal restriction.
- Complete explicitly requested drafting support now: locate a project, create
  a workspace, or save/update the full prompt. Check for existing content before
  writing. Do not defer these actions into the receiving prompt. Otherwise keep
  the underlying project unchanged while drafting.
- Follow-up discussion stays in drafting mode. Return the complete revised prompt
  when asked to amend it; preserve detail when asked not to condense. If the user
  explicitly says to implement or switches to execution with “go”, honor that
  scope change; do not enforce a permanent drafting-only thread.

## Choose the execution strategy

Read [model preferences](references/model-preferences.md) for current defaults,
capability checks, and harness-specific worker settings. Treat those profiles as
revisable evidence, not an exhaustive list or a task-size lookup table.

Select model and effort separately using ambiguity, reasoning depth, consequence
of error, available tools, feedback quality, latency/cost preference, and how
independently subtasks can be verified. A one-file race can be harder than a
many-file mechanical edit. Honor a specified model/effort. State a concise reason
and any material uncertainty; never claim an unmeasured choice is optimal.

Choose direct execution, a lead with workers, or staged discovery/implementation
according to the work. Do not add workers to a trivial task. When delegation is
requested or appropriate under the receiving harness's rules, put the delegation
instruction and explicit worker model AND effort inside the copyable prompt.

- Default Luna workers to `gpt-5.6-luna`, reasoning `max` for implementation,
  debugging, design, substantial synthesis, correctness review, and visual review.
- Luna `low` is an optional read-only exploration lane: locating files, gathering
  sources, inventory, or extracting facts. A worker moving from exploration into
  implementation or substantive judgment must be reassigned at max first.
- Give workers complete outcomes with owned files/resources or read-only scope,
  relevant raw evidence, acceptance checks, and an integration owner. Scale
  concurrency to independent work and available resources.
- For uncertain multi-pass work, let a critic inspect raw evidence at meaningful
  decision points and challenge the hypothesis or metric. Don't require a
  permanent critic or fixed review cadence for every task.
- If a requested route is unavailable, disclose that and choose a supported
  fallback respecting user constraints. Never silently substitute Luna low for
  max, invent a worker role, or claim a dropdown was changed by prompt text.

## Make delegation useful

When a lead with workers fits, develop an initial division of work grounded in
this request and put it inside the handoff. It is a starting hypothesis the
receiving agents can revise, not a fixed plan. Help the lead use its strongest
reasoning to clarify uncertainties, choose discriminating evidence, and explain
interfaces and product tradeoffs so Luna max can carry substantial work further.

Prefer worker outcomes that include the useful execution loop: investigate,
implement, run and monitor checks, diagnose failures, correct, and return a
reviewable result. For example, an experiment owner can deliver a matched
comparison and recommendation; a product owner can fix and verify a complete
user journey. Choose the ownership boundary from the task rather than assigning
Astra every implementation/build/measurement step and Luna only supporting audits.
Give workers room to challenge the premise and change approach within the outcome.

Make the return useful for a decision: recommendation, changed artifacts, decisive
evidence and raw-source pointers, unresolved gaps, and any dependency needing the
lead. Keep routine logs and follow-through with the owner. The lead can inspect
raw evidence, request correction from that owner, or take over when useful; focus
review on consequential interfaces and claims rather than recreating the work.
Independent criticism helps when it tests a meaningful alternative or failure mode.

Retain freedom to work directly, change models, reshape lanes, and escalate based
on evidence. Optimize accepted progress and low rework, not worker utilization.
Avoid fixed worker counts, mandatory critics, a no-coding lead, or a prescribed
escalation ladder. Include only the parts that improve this particular handoff;
simple amendments and well-bounded tasks may be best handled directly on Luna max.

## Make the handoff executable

Write for an agent that has none of this conversation. Include the outcome,
project/workspace, essential context and authorization, and evidence of completion.
Scale detail to the task; use structure where it helps, not a universal template.

For broad improvement requests, connect the overall ambition to a first measurable
milestone and a way to reprioritize after evidence. Preserve requested iteration:
the lead should drive implementation, verification, integration, and continued
useful work through the chosen owners, not stop at a roadmap or worker report.
Do not invent arbitrary pass limits or promise that
“same turn forever” survives interruptions. Long campaigns need a compact durable
checkpoint recording work done, active jobs/resource ownership, next action, and
remaining acceptance gaps so a receiving agent can resume instead of duplicating
jobs or redoing solved work.

Match verification to the promised result. For visual work, require inspection of
rendered screens and a concrete visual direction, followed by implementation and
another visual check; passing code tests alone does not establish visual quality.
For experiments, distinguish intermediate metrics from the real user outcome,
test neighboring/held-out cases, and label simulation versus hardware evidence.
When campaigns share devices, mutable outputs, or files, verify current ownership
and keep independent work moving while a resource is occupied.

Before returning, compare the handoff with the request: no omitted side requests,
lost constraints, invented authorization, stale campaign assumptions, unspecified
implementation-worker effort, or generic “improve everything” without a first
decision and observable outcome. For delegated work, check that workers can
actually close their outcomes and that the lead's remaining work has a purpose.
Include only instructions that change execution.

## Return

Provide one copyable **Cleaned prompt**, plus **Start in**, **Model**, **Thinking**,
and a short **Why**. Include **Workers** when relevant, but keep the actual worker
contract inside the prompt too. Report any workspace/prompt file actually created.
For a normal handoff, recommend a fresh thread and the displayed model/effort;
keep this conversation available for further refinement. Do not claim to launch a
thread or change settings unless a supported tool actually did so.

For maintenance or evaluating changes to this skill, read
[evaluation and audit lessons](references/evaluation.md). Do not load that history
for ordinary drafting.
