# Benchmark snapshot

Update this snapshot on every lane decision. Numbers are vendor-published
unless marked; efforts and harnesses differ, so compare within a row only.

## 2026-09-23: Opus 5.5, GPT-6 Astra, Fable 5.1

| Benchmark | Opus 5.5 | GPT-6 Astra | Fable 5.1 | GPT-5.6 Sol |
| --- | ---: | ---: | ---: | ---: |
| Terminal-Bench 4.0 | 66.4 (xhigh) | 57.9 | 55.8 | 37.3 |
| FrontierSWE v2 | 62.3 | 65.5 | 56.3 | 32.2 |
| DeepSWE | 74.2 | 74.1 | 67.4 | 72.7 |
| FrontierCode Main | 54.4 | 53.3 | 50.3–50.9 | 47.5 |
| SWE-bench Pro | 89.9 | - | - | - |

Opus 5.5 CursorBench by effort: medium 52.5 (~$3/task), high 56.0 (~$4),
max 57.8.

Decision from this snapshot: Opus medium directs. Astra is the default
escalation (at or above Fable, and on the Codex pool). Fable is used for
second opinions and when Codex is low.

Sources:
- [Claude Opus 5.5 system card](https://www-cdn.anthropic.com/fc1b44717c85dc068bc6ba5024219938094694bd/Claude%20Opus%205.5%20System%20Card.pdf)
- [OpenAI: GPT-6 Astra](https://openai.com/index/gpt-6-astra/)
- [Claude Fable models on your plan](https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan):
  Fable counts against the shared weekly limit and is capped at half of it.


## 2026-09-23: GPT-6 Luna replaces GPT-5.6 Luna

OMP 18.3.0 discovers `openai-codex/gpt-6-luna` (272K, low..max). Price halves:
$0.10/$0.50 vs $0.20/$1.20 per M, cache read $0.01 vs $0.02. OpenAI reports
GPT-6 Luna (high) +5.4 points over GPT-5.6 Luna on AutomationBench at 58% lower
cost per task, and DeepSWE 66.6% at max (about Opus 5 medium). Live requests
passed on the MacBook and nous. Decision: adopt for `task`, `smol`, `tiny`,
`commit` and `vision`; drop GPT-5.6 Sol/Luna/Terra from `enabledModels`.
GPT-6 Sol ($2/$10) was not adopted: Opus directs and Astra escalates.
Source: [Introducing GPT-6 Sol and Luna](https://openai.com/index/introducing-gpt-6-sol-and-luna/)

## 2026-09-29: GPT-6.1 Sol vs GPT-6 Astra for escalation

OMP 18.4.4 discovers `openai-codex/gpt-6.1-sol` (272K, low..max); 18.3.1 did
not (the Codex backend hid it from older client versions). Price $2/$10, cache
read $0.10 vs Astra $10/$50/$1. On the 14-day mix (97.3% cache reads) the blend
is $0.161 vs $1.292 per M, about 8x cheaper per token. Codex had 32% weekly
left at eval time. A live request returned `openai-codex`/`gpt-6.1-sol`.

| Benchmark | GPT-6.1 Sol | GPT-6 Astra |
| --- | ---: | ---: |
| DeepSWE (BenchLM) | 71.9 | 74.1 |
| DeepSWE v1.1 (OpenAI) | ties Astra at ~1/5 cost | - |
| Terminal-Bench Science 0.1 | 57.0 | 64.6 (68.1 per OpenAI, max) |
| OSWorld 2.0 (max) | Astra -2.1 at ~1/7 cost | 72.6 |
| AutomationBench | 36.1 | 41.4 |
| AA Intelligence Index | 51.8 | 52.7 |
| AA-SciCode | 54.2 | 56.5 |

No Terminal-Bench 4.0 or FrontierSWE numbers for 6.1 Sol yet. There is no
GPT-6.1 Luna; GPT-6 Luna stays.
Verdict: adopt 6.1 Sol high as the default escalation lane. It trails Astra by
1–5 points on coding and agentic benchmarks, but by 7.6–11 on Terminal-Bench
Science, at about 1/8 of Astra's blended token price. That is a price ratio;
Codex quota burn per successful escalation is unmeasured. OpenAI still
positions Astra for the hardest work.
Sources: [Introducing GPT-6.1 Sol](https://openai.com/index/introducing-gpt-6-1-sol/),
[BenchLM GPT-6.1 Sol](https://benchlm.ai/models/gpt-6-1-sol),
[BenchLM GPT-6 Astra](https://benchlm.ai/models/gpt-6-astra)
## 2026-11-17: GPT-6.2 Sol and GPT-6.2 Astra

Codex CLI 0.166.0 discovers `gpt-6.2-sol` (500K) and `gpt-6.2-astra` (272K),
low..ultra; live `codex exec` rollouts served both exactly. The backend lists
them only for `client_version` >= 0.166.0, and OMP 18.16.0 through 18.22.0
sends 0.159.0, so OMP roles stay on 6.1 Sol / 6 Astra until OMP catches up.
Prices: Sol $2/$10, cache read $0.10 (unchanged from 6.1); Astra $8/$40/$0.40,
down from $10/$50/$1. On the 14-day mix (97.3% cache reads; cache writes at
input price) Astra blends about $0.77 vs $1.44 per M, Sol $0.16.

| Benchmark (OpenAI charts, highest plotted effort) | 6.2 Astra | 6.2 Sol | 6 Astra | 6.1 Sol | Opus 5.5 | Fable 5.2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Terminal-Bench Science 0.1 | ~77 ($7) | ~68 ($2) | ~68 ($24) | ~57 | ~63 | ~73* |
| Agents' Last Exam v1.1 | ~78 | ~73 | ~73 | - | ~72 | ~73 |
| BenchCAD 2.1 Core | ~83 | ~73 | ~63 | - | ~65 | ~84 |
| FrontierCode 2.0 (max) | Sol within 0.5 of Astra at ~1/5 cost | | | | | |
| GDPval v2 | +6.2 over 6 Astra | +5.3 over 6.1 Sol | | | | |

*mini-swe-agent harness. Independent (search summary of the AA post; post not read):
Artificial Analysis Intelligence Index
Astra 79, Sol 78 (Fable 5.2 75), but its Coding Agent Index has 6.2 Astra
flat with 6 Astra and 6.2 Sol 3 points below 6.1 Sol. No Terminal-Bench 4.0,
DeepSWE or SWE-bench Pro numbers from OpenAI yet.

Admission controls (scratch `agent-run`, `~/.local/state/model-eval/2026-11-17-gpt62/`):
Packets were the real `council-yield` (whole file, base..candidate) against a
contract that re-adding a (date, slug, seat) fails; the seeded copy dropped
that duplicate check. All five receipts had model, effort and sandbox OK.
- 6.2 Sol audit (xhigh), seeded: BLOCK, first finding the dropped check at
  `council-yield:212-228` (184 s).
- 6.2 Sol audit, clean: BLOCK, but it saw the check and flagged only its
  race; the other blockers are real latent defects (dry-run settles receipts,
  `-ask-` suffix match, no-trailing-newline append). Incumbent 6.1 Sol on the
  same clean packet: BLOCK with the same four (466 s vs 208 s). The clean
  control was not defect-free, so it shows parity, not a false positive.
- 6.2 Astra seat (high), seeded: blocker C-01 at `council-yield:212-228` with
  a repro, score 5.6. Clean: no missing-check claim, same real defects as
  the auditors plus cost rounding and backfill ordering, score 5.7. Every
  finding I checked held.

Verdict: adopt 6.2 Sol for the `agent-run` implementation, consult, audit and
council Sol lanes (same price, broad gains, one independent coding-agent
regression to watch in `council-yield`), and 6.2 Astra for the Astra seat and
the Codex interactive default (cheaper and stronger than 6 Astra).
Sources: [Introducing GPT-6.2 Astra and Sol](https://openai.com/index/introducing-gpt-6-2-astra-sol/),
[OfficeChai chart reads](https://officechai.com/ai/gpt-6-2-sol-gpt-6-2-astra-benchmarks/),
[Artificial Analysis](https://x.com/ArtificialAnlys/status/2122750634210529569)
