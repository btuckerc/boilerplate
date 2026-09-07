# Chandelier project memory

All real work is under `~/src/chandelier-reconstruction-20260907`, not Documents. For changing progress read `print_tracking/ledger.json` and `MEMORY.md`. Historical print evidence is in `outputs/PRINT_STATUS.md`.

## Accepted design

The user replaced the proposed printable metal-mesh imitation with a fabric-covered printed frame. The printed shade is 508 mm outer diameter and 203.2 mm high. Its top stays at the original top and the added height extends downward toward the candle stands. Original height was estimated at 153.744 mm, not measured. Center bore is nominal 15.875 mm. The 254 mm "leg" measurement remains unassigned; do not silently label it a stem or arm. One Blender unit is one millimetre, unit scale 0.001.

The full master remains editable, with named parts. The nickel five-arm inner fixture, sockets, flame bulbs, stem, hub, and chain are a separate visual assembly and are omitted from print exports. All exported kit pieces passed manifold, winding, positive-volume and intersection checks. Physical coupon fit is confirmed, whole-frame heat/load/stiffness is not yet qualified. The frame supports its own shade/fabric, not the chandelier or electrical hardware. Preserve existing metal mounting hardware where available. LED bulbs only for this PLA prototype; confirm actual operating clearance and heat before installation.

| Part | Required | STL basename |
|---|---:|---|
| Ring arcs | 12, six per ring | 01_ring_arc_60deg |
| Curved alignment keys | 12 | 02_curved_alignment_key |
| Vertical ribs | 6 | 03_vertical_rib |
| Top radial supports | 3 | 04_radial_support |
| Center collar | 1 | 05_center_collar_15p875 |

STLs are under `outputs/stl/`; inspect the current files before assuming this path. `outputs/parts_manifest.json` contains authoritative dimensions and quantities, including separate optional coupon crops. Production count is 34.

Rings have radial bounds 244..254 mm and height 13 mm, with 1.2 mm hollow walls. Seam gap 0.2 mm, key face clearance 0.25 mm, rib peg side clearance 0.2 mm. Six hollow ribs and three top I-section supports stiffen the assembly. There are 48 fabric sewing tabs, 24 per ring. Hardware faces inside; keep the bottom outside surface flush.

Hardware from `outputs/ASSEMBLY.md`: 24 M3x8, 12 M3x12, 3 M3x20 screws, 39 standard M3 nuts, AF 5.5 mm/thickness 2.4 mm, six thin M3 washers. Captive nuts go into keys before insertion. The previously found Amazon kit is https://www.amazon.com/dp/B09XN629BF; verify availability/specs before another shopping recommendation. Visible heads can be cleaned, scuffed, primed and painted white; keep threads and fit faces clear.

## Fabric decision

Ballard Designs Freya Multi Fabric by the Yard, FF016FYM:
https://www.ballarddesigns.com/freya-multi-fabric-by-the-yard/706340

Verified specifications: 100% cotton, 54 in width, 27.25 in horizontal repeat, 26 in vertical repeat, non-railroaded, dry clean. No published transmission or lampshade heat rating was found. Actual vendor image is packed in the Blender file with nominal physical repeat. Color, light transmission, and exact crop need a swatch; do not claim measured physical appearance.

Buy two continuous yards. Cut two panels 828 x 235 mm, about 32.6 x 9.25 in. Each long edge goes across the roll width so the plants stand upright. Cut the second panel in the same horizontal position 26 in down the roll to repeat the pattern phase. Each short side allows a 15 mm seam; finished circumference is approximately 1596 mm. Top/bottom turn-ins are approximately 16 mm. Put the two seams above opposite ribs. A single 1625 x 235 mm strip rotates this directional print sideways, shown only as an alternative. Fractional repeats mean a pattern break at the seam is expected.

Attach folded fabric to the existing tabs with thread loops that encircle solid plastic: through tab hole/fabric, around the free inner edge of the tab, back through the hole. Two or three loops, knot inside. Passing back through the same hole without wrapping the tab does not capture the plastic. Overcast or narrow-zigzag raw edges; avoid a deep hem consuming the turn-in allowance.

## Deliverables and rebuilding

- `outputs/chandelier_fabric_frame.blend`, six named scenes, Freya upright is the default look study.
- `outputs/pdf/chandelier_fabric_shopping_and_attachment.pdf`, two pages with cutting/attachment diagrams.
- `outputs/FABRIC_FREYA.md`, fabric provenance and assumptions.
- `outputs/previews/freya_orientation_comparison.png` and photo-angle PNGs.
- `outputs/ASSEMBLY.md`, `REBUILD.md`, `README.md`, validation JSONs.
- `outputs/chandelier_fabric_frame_complete.zip`, snapshot of deliverables. It does not automatically include later ledger changes.
- `outputs/scripts/apply_freya_material.py`, `finalize_freya.py`, `make_fabric_guide.py`, `package_delivery.py`.
- Blender executable `/Applications/Blender.app/Contents/MacOS/Blender`; geometry Python at `work/venv/bin/python`.

Source media is preserved in `source/`, including the MOV, converted stills and original HEICs. The original paths were under Downloads. Build geometry with bpy scripts, render, inspect the images, fix, and repeat. Never substitute a fused mesh or a generated illustration for editable, printable geometry.
