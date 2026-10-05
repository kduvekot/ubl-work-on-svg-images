# Group B: the three phase and overview figures

Done 2026-10-05. Three of the UBL repository's other 8 figures (`history/remaining-figures.md`)
had no source anywhere, so they are **drawn from the UBL repository's PNGs**
(`art/<figure>.png`, `ubl-2.5` at `3d81e8a`), as draw.io drawings in `diagrams/<figure>/`,
exported to `to-ubl-repo/` like the rest: **92 figures now**.

**The basis is the PNG of the UBL repository, never Ken Holman's `history/svg-images/`.** His two
Open-edi SVGs only wrap that PNG (byte for byte the same, checked); his IMFM SVG is a hand-made
copy that is not the figure (3 captions where the PNG has 7 lines, other chevrons).

| figure | PNG | drawing | PNG ink not in the export | export ink not in the PNG |
|---|---|---|---|---|
| `UBL-2.2-IMFM-GenericIntermodalFreightProcess` | 3425x798 | 3 chevrons, 3 titles, 7 caption lines | 2.78 % | 0.88 % |
| `UBL-2.2-Open-edi-Overview` | 3425x2667 | 5 boxes, 1 dashed frame, 8 arrows, 14 texts | 5.46 % | 2.04 % |
| `UBL-2.2-Open-edi-Application` | 3425x3184 | 5 dotted frames, 9 boxes, 4 arrows, a brace, 20 texts | 7.06 % | 5.58 % |

(`history/group-a/compare_png.py`, the share of ink with no ink of the other within 4 px, at the
PNG's size, on the 1 bit print PNGs of `to-ubl-repo/art/`. For comparison Group A's redrawn
experiment matched its PNGs to 1-8 %.) What is left is mostly the anti-aliasing of the PNG's text
against the export's, and the **dotted frames of the Application figure**, whose dots cannot be
in the PNG's phase.

## Colour: there is none

IMFM's PNG is 8 bit greyscale; the two Open-edi PNGs are stored as RGB, but every pixel is a pure
grey (largest difference from its greyscale value: 0) and the only tones are black, white and
antialiasing. So the drawings are black and white and the print PNGs 1 bit, as the 78 are. Nothing
to ask the TC.

## How they were made

Each `build_*.py` writes the drawing (`lib_b.py` on `history/group-a/redrawn/lib.py`, in the editor's
form, `tools/drawio_format.py`) from numbers measured in the PNG: stroke centres, boxes, arrows and
the first line's ink top of each text, found with numpy/scipy. Then export, compare, and nudge:

```sh
python3 history/group-b/build_openedi_overview.py            # writes diagrams/<figure>/<figure>.drawio
NODE_PATH=$(npm root -g) node tools/export_drawio.js to-ubl-repo diagrams/UBL-2.2-Open-edi-Overview/*.drawio
python3 history/group-a/compare_png.py <ubl>/art to-ubl-repo/art <out> UBL-2.2-Open-edi-Overview
python3 history/group-b/align.py <ubl>/art to-ubl-repo/art UBL-2.2-Open-edi-Overview x0,y0,x1,y1,name ...
```

`align.py` says, per window of the PNG, how many pixels the export lies right of / below it; the
build scripts carry the corrections found that way (a `+3`, a `+7` and the like, commented).

- **Scale** is the Group A rule: the PNG's text height over draw.io's 12 px. All three figures have
  an 80 px (IMFM, Overview: 1/6.6) or 66 px (Application: 1/5.5) text, lines of 6-7 px (1 px), the
  frames and dashes 10 px (1.5-1.8). So the export prints them at 9, 9 and 7.9 pt. The IMFM
  titles (100 px) are 15 px, and the Overview's stacked "BUSINESS TRANSACTIONS" 16 px, as in the PNGs:
  the text is not all one size there.
- **Arrows are one outline each, a custom shape** (`shape=stencil(...)`, `lib_b.stencil`): the PNGs'
  heads are narrower and longer than any of draw.io's arrowheads (barbs swept back to the shaft;
  Overview 187 x 95 px with a 20 px shaft, Application 288 x 168 with 67). The editor shows them as
  ordinary shapes (Edit Style). They hold the ends at fixed places, so moving an arrow means
  moving the shape, not a connector. The alternative is draw.io's own `classic` or `flexArrow`
  edges (editable as connectors) at the cost of heads that differ visibly from the PNG.
- **Text** is live: html labels, line height set to the PNG's pitch (120 px in the Overview's boxes,
  82 px in the Application's), the rotated ones with `horizontal=0`.
- **The frame** is the PNG's own 10 px black border, drawn as a rectangle, as the PNG has it.
- **Notation:** `ubl-notation` is on the frame (`phase-map` for IMFM, `overview` for the two
  others), no `ubl-kind`s beyond a few names: like Group A, `check_drawio.py` reports "ok" with the
  notation.
- **Not matched on purpose:** the Application's dotted frames have the PNG's dash and gap
  (14 and 26 px) but not its phase; the corner radii of boxes, pills and frames are estimated
  (45, 60 and 60 px; trying 35 and 48 for the pills was worse).

## Checked

**In the live editor** (draw.io 32.2.0, 2026-10-05, `python3 tools/drawio_upgrade.py --editor <3 figures>`): opened and saved, all
three come back the same in every cell, style, geometry and the render (`VERDICT: SAFE`); the editor's own PNG
export of each shows the custom arrows, the rotated labels, the line heights and the brace as the export has them.
(Needs the proxy's CA in the browser's trust store: `certutil -d sql:$HOME/.pki/nssdb -A ...` only; do not run `-N` on the
existing database, it hangs.)


`tools/check_drawio.py` (all 92 drawings), `tools/check_svg.py to-ubl-repo` (92 of 92: SVG is vector,
words as text, 1 bit PNGs, export up to date), and every earlier figure's export is unchanged byte
for byte.
