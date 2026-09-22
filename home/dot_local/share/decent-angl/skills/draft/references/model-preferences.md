# Model preferences and capability checks

Reviewed 2026-09-13. These are local starting preferences, not measured rankings.
Keep model-specific choices here so adding models/providers does not require
rewriting the drafting workflow. User choices override these defaults.

## Current candidates

| Candidate | Useful starting role | Effort guidance |
| --- | --- | --- |
| `gpt-5.6-luna` | Interactive drafting; bounded work with clear verification | max for drafting judgment, implementation, design, and substantive review; low only for read-only exploration |
| `gpt-5.6-terra` | Everyday coding with manageable ambiguity | medium initially; increase when the reasoning burden warrants it |
| `gpt-5.6-sol` | Cross-cutting professional work and synthesis | medium initially; choose greater effort for interdependent reasoning |
| `gpt-6-astra` | Difficult architecture, uncertain diagnosis, or integration with costly errors | medium or high based on uncertainty; xhigh/max when justified by depth or observed failures |

There is no requirement to fail on medium before choosing high, or to escalate
through every model. A missing tool, stale evidence, or bad task contract needs
that problem fixed rather than more reasoning alone. Ultra is not a routine
recommendation: use only when explicitly requested and supported, after checking
its harness-specific behavior.

Official [model descriptions](https://developers.openai.com/api/docs/models)
describe Luna as cost-sensitive, Terra as balanced, and Astra as suited to complex
work. [Luna documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
supports max reasoning. These API facts do not establish subscription usage,
GUI availability, or performance on this user's tasks. The local preference for
Luna max on implementation/review comes from user feedback, not an official claim
that low always fails.

## Resolve capabilities, then map the role

Use the current harness's exposed model/effort list before recommending an exact
setting. Consult a local model inventory if exposed; check official provider
documentation for unfamiliar or changed capabilities. Do not inspect auth files.
If no inventory is available, identify the recommendation as conditional on the
receiving UI supporting it. Do not query every provider for each draft.

For a new candidate, record its exact provider/model ID, supported efforts, tools
and modalities, availability evidence/date, promising roles, limitations, and
local outcome evidence. Unknown performance remains unknown. A trial on a bounded,
verifiable task can establish suitability before assigning it critical work.
Model availability and observed quality are separate facts. If effort names
differ between providers, use their real controls; do not translate max blindly.

## Worker handoff

Use this compact contract when Luna implementation workers are appropriate:

> Use Luna subagents (`gpt-5.6-luna`) with reasoning effort `max` for implementation,
> debugging, design, and substantive review. Use `low` only for explicitly
> read-only exploration. Set both model and effort on each spawn; an exploration
> worker must be reassigned at max before editing or making substantive design
> decisions. Give each worker an outcome it can own through investigation,
> implementation, validation and correction, with relevant evidence and acceptance
> checks. Return a compact recommendation with artifacts, decisive evidence and
> remaining gaps. The lead owns integration and targeted acceptance review,
> and can revise the division of work or work directly where useful. If max
> cannot be selected, report the limitation and use a supported capable fallback
> or let the lead do that work; do not silently use low.

Adapt to the actual receiving tool schema:

- Codex `collaboration.spawn_agent`: set `model: "gpt-5.6-luna"` and
  `reasoning_effort: "max"`. In the observed harness, model overrides require
  `fork_turns: "none"` or a positive turn count; `"all"` inherits the parent's
  settings. Supply the task's necessary context explicitly with a fresh fork.
  Recheck the tool schema if this changes. A task name such as `visual_review`
  is a label, not the model selector.
- OMP: inspect the available task tool/agent registry and model/effort override
  mechanism. Agent role IDs such as `task`, `scout`, and `reviewer` are not model
  IDs. Do not invent `agent: luna`, assume prose selects max, or retain an OMP-only
  role restriction in a Codex handoff. Use verified override fields or the fallback
  above; do not mutate global agent defaults just to draft a prompt.

The receiving agent can revise decomposition and supported routes as evidence
changes, within explicit user constraints. Recommendations do not automatically
change the running lead's model or create a new GUI thread.
