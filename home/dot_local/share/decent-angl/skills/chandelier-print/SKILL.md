---
name: chandelier-print
description: Operate Bambu Studio through Computer Use to continue Tucker's chandelier frame print kit, track accepted and failed pieces, print the next required plate, recover after compaction, or reset the print run. Use for chandelier print progress, bed-cleared updates, missing or broken pieces, reprints, and requests to continue the next round.
argument-hint: "[next | status | reset | natural-language update]"
---

# Chandelier printing

This is an operating workflow. On `next`, `continue`, or an update such as "the plate is clear," conduct the next round through Bambu Studio. Persist progress before returning. `status` only inspects and reports. Natural language is supported; translate it into the ledger operations below.

The project is `~/src/chandelier-reconstruction-20260907`. Its `print_tracking/ledger.json` is the authority for print accounting. This shared skill contains no changing inventory. Read the ledger every invocation and after compaction. If it is missing, restore from `print_tracking/history/` and project checkpoints, then reconcile with the user and printer. Never silently initialize an empty run.

Read [printer operation](references/bambu.md) before controlling Bambu, [ledger operations](references/ledger.md) before changing counts, and [project memory](references/project.md) when recovering context or changing a plate/design.

Use `python3 <this-skill-directory>/scripts/ledger.py status` and `next`. Use the script through its actual installed skill path, not an assumed current directory. The helper handles accounting, archives, file hashes, and duplicate-send reservations. The agent operates the UI.

## Run the next round

1. Read `status` and `next`. If continuation is paused, resume with a `control` event only for a fresh user `next`/`continue` request; scheduled checks never resume it on their own. Apply any new user report with its evidence. Repeated reports must not add counts twice. Physically accepted parts, printer-reported completion, and active jobs are separate states. A finished timer alone does not establish usable inventory.
2. Read fresh BTC-3DP status through native Computer Use. Match job identity before updating the ledger. If a send is uncertain, inspect the printer and job history before doing anything that could resend. An idle screen alone does not prove a past job never printed.
3. If a job is active, record its status and inspect actionable faults. Do not send another plate. Read `print_tracking/automation.json` for the existing follow-up id. On an explicit user request to resume, reactivate that same follow-up with the app tool, preserving its fields. Keep an existing scheduled follow-up attached to this task; if the user requests background watching, create or update a thread heartbeat with the app automation tool. Do not claim the skill itself schedules runs. While unchanged, stay quiet. Notify once on completion, failure, or a needed physical action.
4. When a job ends, record the printer result. Obtain the usable/failed quantities and physical removal evidence. Ask only for missing physical information. A clear-bed statement does not also mean every part passed inspection. For "everything looks good and the bed is clear," record both without asking again.
5. Plan from shortages. A full missing plate uses its saved Bambu project. A partial failure needs a new plate containing only missing quantities. Prepare and inspect the 3MF first, register it with `add_plate`, and preserve the original projects. See the project reference for packing and profile constraints.
6. Verify live idle status, a clear build surface, right 0.4 mm nozzle, A2 bone-white PLA, bed type, object counts, slice, and settings. Existing authorization covers sending this chandelier kit and reasonable test/reprint jobs. Do not ask for print permission again. Unknown material, unreadable UI, a busy bed, or mismatched geometry must be resolved first.
7. Immediately before the final Send action, use `reserve`. It atomically records a `sending` job and consumes clear-bed evidence. Only the invocation whose reservation succeeded may click Send. If it fails, reread state. Never work on this printer through parallel agents.
8. Send through Computer Use. Observe transfer and the new job identity, then `observe` it as printing. Verify startup and the first layer when practical. If the outcome is uncertain, leave `sending` unresolved and reconcile, never click Send again from assumption. Persist the result and the next step.
9. Continue until a physical action or active print requires waiting. On all 34 accepted production parts, stop the print follow-up. Do not keep generating spares after the kit is complete.

## Reset and corrections

`$chandelier-print reset` or an explicit request to start the print accounting from scratch runs the helper's `reset` command with a stable event id and the user's words as evidence. It archives the old state and zeros the new run's accepted production counts. It preserves known fit/settings, files, and history, and pauses continuation until an explicit `next`/`continue`. An active or uncertain old job still blocks sending until reconciled. Pause the existing heartbeat after reset, preserving its fields. Reset does not cancel a printer job or clear the physical bed, and does not start another print unless the user also says to continue.

An explicit "pause the automation" writes `control` with `enabled: false` and pauses its heartbeat. It does not press the printer's Pause or Stop unless the user requested that physical job action.

"One rib broke" updates the absolute accepted/rejected totals for the job that supplied it, then plans the missing rib. Do not restart the whole kit. Ask only if the source job or quantity cannot be determined from the ledger.

## Preserve continuity

Keep runtime state under the project, never in the shared skill source. Every mutation has dated evidence and an id. The helper writes `print_tracking/STATUS.md` and snapshots prior revisions. Store useful new UI, material, fit, and assembly findings in the project `print_tracking/MEMORY.md`. Do not overwrite the original historical `outputs/PRINT_STATUS.md` as though it were live.

Use natural Computer Use for Bambu. Do not substitute AppleScript, window-control shell commands, direct printer APIs, or a new Bambu process. Do not alter the Hydra containment to make file pickers work. If Computer Use is unavailable, preserve state and name that specific blocker.
