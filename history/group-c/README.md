# Group C: the four reference figures

Done 2026-10-05. The last four figures of the UBL repository that are used
(`history/remaining-figures.md`) had no source anywhere, so they are **drawn from the UBL repository's
PNGs** (`art/<figure>.png`, `ubl-2.5` at `3d81e8a`), as draw.io drawings in `diagrams/<figure>/`, exported to
`to-ubl-repo/` like the rest: **96 figures now**. The basis is the PNG, never Ken Holman's
`history/svg-images/` (each of those only wraps the PNG).

| figure | PNG | drawing | PNG ink not in the export | export ink not in the PNG |
|---|---|---|---|---|
| `UBL-2.2-DefaultValidation` | 3425x2248, grey | 3 triangles, 2 rounded boxes, 3 circles, 7 arrows, 16 texts | 5.51 % | 4.12 % |
| `UBL-2.2-UDT-QDT` | 3425x2200 | 12 boxes with circled letters, 6 braces, 8 rules, 7 arrows, 42 texts | 4.50 % | 2.67 % |
| `UBL-2.2-SchemaDependencies` | 3425x1957 | 18 boxes, 26 arrows, 5 lines, dashed outlines, a legend, 29 texts | 1.76 % | 1.81 % |
| `UBL-2.3-ModelRealization` | 3425x2013 | 28 boxes (3 stacked pages), 33 arrows, 13 lines, 2 frames, 41 texts | 0.23 % | 0.27 % |

(`history/group-a/compare_png.py`, within 4 px, at the PNG's size, on the export's print PNG.)

## Colour

The PNGs have **one grey, 230 (`#e6e6e6`)**, as a fill (the qdt, udt, ccts boxes, the Core Component
Parameters box, the grey boxes of UDT-QDT); everything else is black and white. DefaultValidation is pure black
and white. The three with the grey are marked `ubl-art="grey"` on the frame, so the print PNG is greyscale
(8 bit) on purpose, as Business Information's.

## How they were made

`lib_c.py` (on Group B's `lib_b.py`) writes the drawing from numbers in PNG px; `build_<figure>.py` has the
numbers measured with `measure.py` (long strokes), `lines.py` (text lines) and `bb.py` (ink boxes), then
`export_check.sh <figure> <ubl>/art <out>` exports and compares, and the diff image (red: only in the PNG,
blue: only in the export) says what to nudge.

- **Scale** is the Group A rule: the main text's size is draw.io's 12 px (so S = 5.9, 5.9, 4.4 and 4.5 PNG px per
  drawing px); smaller texts in proportion (italic notes, legends, circled letters).
- **Text is live**: separate text cells placed by their ink; the export snaps lines to whole drawing px, so
  positions were swept to within 2 px of the PNG.
- **Arrows are draw.io connectors** (`block` heads, attached at both ends, exit and entry points fixed), so
  they move with their boxes; the heads are a little shorter than the PNGs' (draw.io's are as long as wide).
  Where a flow's end is on no box (legend samples, replace arrows) it is attached to an invisible 1 px
  `anchor`; plain lines have the kind `line`, braces `brace`.
- **A triangle that points west** is turned half way, and so are its exit constraints (`lib_c.py` handles it).
- **Dashes:** draw.io multiplies `dashPattern` by the stroke width; `lib_c.py` does not allow for that, and
  the SchemaDependencies, UDT-QDT and ModelRealization scripts convert in their own code. Fix `lib_c.py`
  before a fifth script uses it.
- **Not matched:** the dash phase and the PNGs' round caps and joins, the arrowheads' length, brace curvature.

`ubl-notation="reference"` is on each frame; `tools/check_drawio.py` says "ok (reference)" for the four,
`tools/drawio_format.py --check` and `tools/check_svg.py to-ubl-repo` (96 of 96) pass.

## Checked in the live editor

draw.io 32.2.0 (2026-10-06, `python3 tools/drawio_upgrade.py --editor <the 4 figures>`): the four drawings opened
and saved again come back the same in every cell, style, geometry and the render (`VERDICT: SAFE`).
(Needs the proxy's CA in the browser's trust store: every certificate of `/root/.ccr/ca-bundle.crt`, imported one by
one with `certutil -d sql:$HOME/.pki/nssdb -A`; the first alone is not enough; `libnss3-tools` for `certutil`.)
