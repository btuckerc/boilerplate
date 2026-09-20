# Nous decision-model smoke evaluation

These are synthetic, manually labelled triage examples, not an end-to-end coding
benchmark. Laya's general English and typed-decision checkpoints each matched
7/12 labels; Jev matched 12/12. Accuracy here means agreement with our chosen
execution policy, not proof of task completion or calibrated confidence.

The two Laya scripts preserve the trial as executed. They run on **nous**, not
on a workstation. They use CPU only, four Torch threads, and the pinned model
revision. Their model paths are under `/home/tux/.local/share/nous-triage-eval/`.
The base script explicitly raises `head_max_len` to 256 so the unchanged rubric
fits. The assembled question head was 208 tokens; all four option texts fit.
Input states were at most 36 tokens. No service or network listener is needed.
Cold-load measurements exclude downloads. RSS is the Linux process peak, not
an estimate of all host/model-cache memory. Warm timing is one pass over these
cases, not a sustained load test.

Installed trial environment on nous: Python 3.14.4; CPU Torch 2.14.0+cpu;
Transformers 4.57.1; Laya 0.3.3. See `dependencies.lock` for the exact installed
Python packages. A fresh environment needs the CPU Torch wheel index at
`https://download.pytorch.org/whl/cpu`; do not install CUDA Torch for this trial.
`laya.load` uses the reviewed package and pinned checkpoint directories. The
model downloads are intentionally outside Git and remain on nous.

To reproduce using the existing isolated environment:

```sh
scp utils/nous/triage-eval/{base-trial,typed-trial}.py nous:/home/tux/.local/share/nous-triage-eval/
ssh nous 'CUDA_VISIBLE_DEVICES="" ~/.local/share/nous-triage-eval/venv/bin/python ~/.local/share/nous-triage-eval/typed-trial.py'
ssh nous 'CUDA_VISIBLE_DEVICES="" ~/.local/share/nous-triage-eval/venv/bin/python ~/.local/share/nous-triage-eval/base-trial.py'
```

There is no automatic routing integration. Ordinary OMP work makes no Laya/Jev
request. For an explicit cloud comparison, `omp-triage` takes supplied text and
returns one advisory Jev decision; it uses the same criteria/instructions. The
`synthetic-fixture.py` file contains the cases without credential-handling code.
`jev-results.json` preserves the matched initial probe, including reported API
cost. Do not equate API spend or token counts with Codex subscription allowance.

Checkpoint revisions:

- `convaiinnovations/laya`: `c5d78730f3493e4fe16d61507ef4b78eef7318cf`
- `convaiinnovations/laya-typed-decisions`: `f9ab0b228f0fc0f14d873dbc99038f135c2da1b2`

See [the execution report](../../../docs/omp-execution-policy-2026-09-19.md) for
the resulting recommendation and the broader native OMP behavioral tests.
