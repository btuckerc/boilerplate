# Operating Bambu Studio

Use native Computer Use, which the user repeatedly requested. Follow the tool's live documentation, not fixed UI indices from this note. Select `com.bambulab.bambu-studio`. Use the existing instance. Read its current AX tree and screenshot. Device status can usually be read without raising the window; avoid stealing focus for routine status polls.

If a click does nothing because the app is inactive, get the current window root, perform its `Raise` secondary action, wait about 500 ms, click the observed target, then reread state in the same call. Old root indices and coordinates are not reusable evidence. A tiny dialog screenshot may require raising that dialog. Use menu `Cancel` if Escape does not dismiss it.

## Files and settings

Normal projects are in `outputs/bambu/`:

| Plate | File | Production pieces | GUI estimate |
|---|---|---|---|
| 1 | packed_01_H2D_PLA.3mf | 12 ring arcs, 6 ribs | 7 h 32 m, 284.14 g |
| 2 | packed_02_H2D_PLA.3mf | 3 supports, 12 keys, 1 collar | 2 h 49 m, 108.36 g |
| Test | coupon_H2D_PLA.3mf | 2 cropped ring samples, 1 key | 20 m 3 s, 7.37 g |

File > Recent projects avoids the problematic macOS file picker. Do not repeatedly open a hanging picker. Do not start a second Studio instance to load a file. For a new partial plate, use supported native open/drop facilities if available or save a reviewed project through a working UI path. If no path works, stop at the actual file-opening blocker, with the partial plate already prepared.

Verified printer configuration:

- Device BTC-3DP, Bambu H2D, both nozzles 0.4 mm hardened steel standard flow.
- RIGHT nozzle uses AMS A2, Bambu PLA Matte Bone White, color D1CCC0. Verify the current Send mapping, not just the model's display color.
- Textured PEI plate, 220 C nozzle, 55 C bed, 0.20 mm layers.
- 3 walls; 100% rectilinear infill for solid regions. The CAD already contains hollow cavities.
- No brim on the two packed production plates. Arc fitting off.
- Automatic bed leveling and flow calibration on. Timelapse and nozzle offset calibration were off.
- Right-nozzle reachable region X25..350, Y0..320 mm. Model print volume 325 x 320 x 325 mm.
- Production plate 1 has only 2 mm minimum XY gap. Do not add brims into neighboring parts. Rearrange more loosely onto extra plates if a brim becomes necessary.

## Import bug already fixed

Original CLI output had `different_settings_to_system=["","",""]`; GUI import silently reverted to 2 walls, 15% grid, and auto brim. The production projects were fixed and the GUI values inspected before sending. `outputs/scripts/preserve_bambu_overrides.py` writes the changed process keys into the first override group. `slice_h2d.py` creates derived settings and patches the exported projects. Preserve this fix for new partial plates. After any regenerate/import, inspect the GUI again. Saved CLI G-code does not replace this check; Studio re-slices model projects before sending.

Read `outputs/scripts/slice_h2d.py` and `preserve_bambu_overrides.py` before creating a new slicer project. Their CLI prepares/slices files but never sends to the printer. Avoid launching the Studio CLI while the GUI is operating if it would create a duplicate instance.

## Send and verify

Check plate/object count and toolpath bounds in Preview. Confirm no missing objects, unexpected supports, overlapping paths, or wrong nozzle. Compare time/weight to the table for unchanged full plates. In the Send dialog verify BTC-3DP and A2 explicitly. Reserve the ledger job only after these checks and a fresh clear-bed observation. Press Send once; inspect transfer and Device job identity. Persist startup evidence even if first-layer verification must wait.

The user already authorized tests and production printing. Removal of cooled parts, inspection, and clearing the bed still require actual physical evidence. A previous clear-bed confirmation was consumed by the next send.

The joint coupon fit was physically confirmed perfect. The coupon key is an extra test item, not one of the 12 production keys unless the user explicitly assigns it to the kit. Existing lubrication reminders were visible. Do not claim they were serviced.

## Machine history

Quick Look thumbnail containment followed Hydra GPU/memory runaway in `~/src/s3-amoled`. Open/save panels can hang while the broker is suspended. Another task was given the investigation. Do not resume/kill the broker, change PlugInKit flags, restart, or remove build blocks to get a file picker working. Project notes: `work/HYDRA_HANDOFF.md` and `work/FILE_PICKER_DIAGNOSIS.md`. PIDs in old notes are stale.

The second-account app is `/Users/tucker/Applications/Codex Second.app`. Its isolated home is `~/.codex-gui/second`; shared skills are linked to `~/.codex/skills`. The old T3 shadow-home collision was already repaired. No auth/config repair is needed to continue this print.
