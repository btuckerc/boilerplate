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