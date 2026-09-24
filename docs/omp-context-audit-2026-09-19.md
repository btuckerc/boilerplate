# OMP context and routing audit — 2026-09-19

This records the OMP 18.2.6 audit and the production RULES wording plus on-demand `local-workers` guidance changes made afterward. Credentials, `.env`, auth storage, databases, and personal/auth logs were not read; one synthetic trace was inspected. A bounded native Astra→Luna routing proof and synthetic acceptance-fixture inspection were performed; this is not a quota or quality benchmark.

Historical snapshot: the [execution policy](omp-execution-policy-2026-09-19.md#routing-evidence-and-limitations--2026-09-22) now supersedes the default routing below with Sol direction, local-first nous/Luna delegation, and evidence-triggered Astra escalation. The original experiments and their limitations remain unchanged.

## Findings

- `~/.omp/agent/RULES.md` is the only user-owned body that OMP always injects. It measured 1,245 bytes before and 1,237 bytes after the wording patch (roughly 311→309 tokens at the rough bytes/token estimate) and is forced into the always-apply rule path by `packages/coding-agent/src/discovery/builtin.ts:372-425`.
- Native skills contribute catalog metadata only: nine visible descriptions are about 2,581 bytes (roughly 645 tokens). Skill bodies are injected on explicit invocation or agent `autoloadSkills`; current user agents have no `autoloadSkills`.
- `draft` and `omp-drive` remain explicit-only. OMP hides them from the skill catalog; Codex projections add `agents/openai.yaml` with `allow_implicit_invocation: false`. Explicit `$skill`/`/skill:<name>` access remains available.
- All other skills remain model-invocable because their natural-language routing is useful: Bitwarden, chandelier bed-clear/plate workflow, OPNsense router requests, local workers, and config/platform/shared-baseline operations. Hiding them would remove useful discovery for only a few hundred catalog bytes each.
- `readSummarize: false` in `nous.md` is the supported camelCase field. OMP parses it and maps it to the child `read.summarize.enabled=false`; `read-summarize` would be ignored.
- Effective settings checked with `omp config get`: memory, recap, advisor, context promotion, unexpected-stop recovery, and both prewalk paths are off; compaction is on; retry model fallback is false. `features.unexpectedStopDetection: false` is migrated to effective enum `none`.
- Automatic title generation remains enabled through `providers.tinyModel: online`; `title.refreshOnReplan: false` only suppresses replan refreshes. Auto-thinking is dormant while the default thinking level is medium.
- Native catalog selectors resolve Luna (272k context/128k output, text+image), Astra (272k/128k, text+image), Ornith (16k/2k, text-only), and Bonsai (catalog only). The local `/v1/models` endpoint confirms Ornith loaded with `--ctx-size 16384` and `--parallel 1`; a second local request queues at the server inference slot. Bonsai’s endpoint was unavailable for read-only verification.
- A reduced `[read, write, yield]` `nous` tool-surface candidate was tested and reverted. The native Luna→nous acceptance run failed exact-byte validation after an invalid per-call tool override and stray child output; no production tool reduction is retained. The canonical six-tool surface and model/body settings remain unchanged.

## Routing decisions

| lane | current choice | decision |
|---|---|---|
| ordinary/default | Astra medium director | retain; local-first delegation is conditional on a bounded, independently checkable task |
| delegated generic task | Luna medium | capability fallback for ordinary coding/tests, larger context, novelty or local failure |
| plan/slow | Astra | retain; conditional role routing only, with no claim that every task uses Astra |
| bounded `nous` | Ornith, background-capable, read/grep/glob/edit/write/yield | explicit local-first lane; one local worker because server parallelism is 1 |
| OpenRouter | explicit enabled alternatives | retain; `retry.modelFallback=false` prevents silent entry |

Model metadata is native discovery data, not a billing or availability guarantee. Full `provider/id` selectors are the stable policy identifiers.

With live `async.enabled=true`, OMP supports background task jobs and native hub
status/send/cancel supervision. Local `nous` remains background-capable so the
director can steer at model/tool boundaries; the one-worker GPU policy remains
in the rules because the backend has one inference slot. No transcript polling
or advisor loop is added.

## Applied change

Replaced the worker-handoff policy in `home/private_dot_omp/private_agent/RULES.md`, clarified the `nous` return contract, and made the local child background-capable for native hub steering. A reduced `nous` tool-list candidate was tested, failed native-child exact-byte acceptance, and was reverted; the canonical six-tool surface remains unchanged.

> Give workers owned files/facts/acceptance; return paths/checks/blockers. Read compact results first; inspect needed diff/tests. Verify once; re-check after changes/failures; avoid full history/duplicates.

The replacement makes the return contract and compact-evidence rule explicit while removing redundant wording. The separate drive/board line was already absent from the dirty canonical file before this change and was preserved as-is; it is shown as a deletion only because the worktree diff compares against `HEAD`. No model defaults, fallback policy, skill invocation flags, or other current rule lines changed. The on-demand `local-workers/SKILL.md` note records native OMP task-item tool semantics, exact-path briefs, and parent-side verification without adding an always-loaded rule.

## Validation boundary

Completed checks: `omp --version`; effective `omp config get` values and types; `omp models --json` selector/metadata inspection; unauthenticated local `GET /v1/models`; source review of OMP discovery, system-prompt, skill, task-executor, retry, title, and model-schema code; dirty-tree inspection; targeted `chezmoi apply` of RULES and reverted `nous` candidate; `decent-angl-skills sync`; `decent-angl-skills validate`; and core `omp-baseline` policy/model/skill checks. The strict source-tracking gate remains pending solely because the pre-existing untracked `home/private_dot_omp/private_agent/commands/draft.md` is reported as PENDING. The standalone utility smoke runs used during the wider audit were isolated/no-skills or proxy-only and therefore did not prove managed baseline savings. Existing user edits and draft files remain untouched; concurrent changes to `home/.chezmoidata/ui.yaml` and `home/dot_config/ghostty/themes/current-theme` were not staged or normalized.

The parent’s native director proof is recorded in `/tmp/omp-context-20260919/director.md`: it verifies an earlier Astra-to-Luna routing and compact handoff with an exact marker, but does not establish token quotas, model-equivalence, or general quality. The two-case local acceptance matrix passed both profiles with no tool errors: edit, six tools 20.309s versus three tools 6.984s; corrected extraction, six tools 8.724s (398 input / 21,391 cache-read / 552 output) versus three tools 9.301s (441 / 13,135 / 635). This is a bounded sample, not a general benchmark or quota claim. A later Luna→native-nous tool-reduction trial failed exact-byte acceptance: task-item tool names were interpreted as undefined evaluation tools, the child used its normal built-ins plus hub, and a stray unexecuted file write plus missing final newline violated the oracle. The candidate was reverted; no native-child success, production reduction, or safety guarantee follows.

## Primary sources

- [OMP 18.2.6 source tree](https://github.com/can1357/oh-my-pi/tree/v18.2.6), especially [task agents](https://github.com/can1357/oh-my-pi/tree/v18.2.6/packages/coding-agent/src/task) and [skills documentation](https://github.com/can1357/oh-my-pi/blob/v18.2.6/docs/skills.md).
- [OpenAI subagents configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents) and [OpenAI pricing](https://learn.chatgpt.com/docs/pricing).
- [Claude advisor strategy](https://claude.com/blog/the-advisor-strategy), relevant to conditional strong-model guidance but not evidence of equivalent OMP performance.
- [OMP execution policy and measured migration](omp-execution-policy-2026-09-19.md), the broader routing and validation record.
