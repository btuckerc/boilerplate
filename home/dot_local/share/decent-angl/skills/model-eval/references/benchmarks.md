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
