# Ledger operations

Use `python3 <skill>/scripts/ledger.py [--project PATH] status|next|apply EVENT.json|reset ...`.

Runtime files live in `print_tracking/` in the project. `ledger.json` is authoritative. `STATUS.md` is generated. `history/revision-N.json` preserves previous revisions. A file lock serializes updates and atomic replacement protects the ledger. Never edit counts directly or test against the real ledger. The helper never controls Bambu; the agent must operate and verify the UI.

Create an event JSON with a file-writing tool, then pass its path to `apply`. Each event needs a unique `id` and concrete `evidence`. Reuse the same id/content when retrying the same action. Reusing an id for different content is rejected. Count updates are absolute per job, not increments. Part ids are `arc`, `key`, `rib`, `support`, `collar`.

Examples below are syntax only, not evidence or instructions to change the current job. Replace ids and evidence with actual observations.

```json
{"id":"obs-unique","type":"observe","state":"printing","job":"production-01","job_status":"printing","name":"packed_01_H2D_PLA","details":{"percent":14,"layer":"2/65"},"evidence":"Live Bambu Device AX at the recorded time showed this job printing."}
```

An observation uses state `idle`, `printing`, `paused`, `finished`, `error`, or `unknown`. Optional `job_status` is `sending`, `printing`, `paused`, `finished`, `failed`, or `cancelled`. Match the on-screen job to the ledger. Unknown or foreign jobs block a send through the printer observation. Never mark finished from elapsed time alone. A printer error can leave the job paused; it does not mean all pieces failed.

```json
{"id":"completion-unique","type":"observe","state":"finished","job":"production-01","job_status":"finished","evidence":"Live Device view reported 100 percent and job complete for packed_01_H2D_PLA."}
{"id":"inspection-unique","type":"inspect","job":"production-01","good":{"arc":12,"rib":5},"bad":{"rib":1},"evidence":"User removed the parts and reported twelve good arcs, five good ribs, one failed rib."}
```

Each JSON object is a separate file/event. `inspect` replaces the entire good/bad map for that job; preserve previously accepted counts when correcting one piece. Omitted counts are uninspected and block the next round. A finished plate does not automatically credit any parts. Corrections may reduce good totals when a part breaks later. Old-run jobs never count toward a reset run.

```json
{"id":"idle-unique","type":"observe","state":"idle","evidence":"Live BTC-3DP Device view shows idle, parked, and no active job."}
{"id":"clear-unique","type":"bed_clear","evidence":"User just confirmed all parts removed and the bed ready for the next plate; live view agrees."}
{"id":"send-intent-unique","type":"reserve","job":"production-02","plate":"plate-02","evidence":"Inspected current slice, 16 parts, right nozzle, AMS A2, 3 walls, 100 percent rectilinear, no brim; ready to press Send."}
```

`reserve` requires live idle observation within 10 minutes and clear-bed evidence within 30 minutes, checks the file SHA256 and exact needed quantities, and refuses active/unresolved jobs or uninspected pieces. Evidence must be real even if timestamps are fresh. It writes `sending` and consumes the bed-clear record. On success this invocation may press Send once. On any uncertainty, reconcile the existing reservation. Never retry Send just because the tool call returned without a clear result.

After a proven failed transfer that never started any print, `void_send` may resolve the reservation. First record a fresh idle observation and corroborate with job history/transfer error. An idle printer alone is insufficient because a job may have already finished.

```json
{"id":"void-unique","type":"void_send","job":"production-02","evidence":"Transfer failed before receipt; current printer and history confirm this job never started."}
```

For a partial reprint or changed prepared file, create and visually inspect a new 3MF under the project. Register it before reserving. The script stores its SHA256 and verifies it at send time. Registered quantities must not exceed current shortages. Preserve original plate files.

```json
{"id":"reprint-file-unique","type":"add_plate","plate":"rib-reprint-01","parts":{"rib":1},"file":"print_tracking/prepared/rib-reprint-01.3mf","evidence":"Inspected the single-rib slice in Bambu with the proven right-nozzle PLA settings."}
```

`next` chooses the first original plate with shortages, using a registered exact partial plate when available. It does not certify slicing or send automatically. The skill does that work. For new geometry, update the project manifest and reviewed kit definition explicitly rather than silently treating mismatched files as approved originals.

A reset is explicit:

```sh
python3 <skill>/scripts/ledger.py reset --event-id user-reset-UNIQUE --evidence 'User explicitly requested a fresh print run.'
```

It snapshots the old state, creates a unique new run, pauses print continuation, clears usable production counts and clear-bed evidence, retains historical jobs and proven calibration, and keeps any active/uncertain job blocking. It neither cancels printing nor erases CAD. Repeating the same reset id/content is idempotent. To record other findings use `{"id":"note-unique","type":"note","evidence":"The actual new finding."}`.

A fresh user `next`/`continue` after reset or pause enables continuation with `{"id":"resume-unique","type":"control","enabled":true,"evidence":"User requested continuing the next round."}`. Use `enabled:false` for an explicit request to pause the automation. Scheduled checks must not change this control state on their own.
