# History: how the drawings came to be

The repository's [README](../README.md) is the guide to the drawings as they are now. This folder
is the record of how they came to be: the path from the UBL PNGs to the draw.io drawings, kept
whole (each step's scripts still run from here), and, below, the measurements and trials behind the
README's rules, moved here from it word for word on 2026-10-06.

## How we got here

The drawings are the end of a path, kept whole in `history/`: the repository
as it was before the switch, which still runs from there, and the edits made
since:

1. **The original PNGs** - `art/` in the [UBL repository](https://github.com/oasis-tcs/ubl),
   branch `ubl-2.5` (not copied here).
2. **Ken Holman's SVGs** - `history/svg-images/`: the first conversion, by hand.
3. **The reading: PNG to JSON** - `history/tools/` reads each PNG into three JSONs
   (`history/diagrams/<figure>/`: the model, its layout, the reading's
   measurements), with every decision taken with the TC recorded
   (`history/tools/model-corrections.json`, `direction-verdicts.json`,
   `artwork-faults.json`) and written up in `history/docs/`. The baselines of the
   reading are in `history/baselines/`.
4. **JSON to SVG** - `history/diagrams/<figure>/<figure>.svg`, drawn by
   `history/tools/draw-from-json.sh`; the comparison decks in
   `history/comparison-pdf/`.
5. **JSON to draw.io** - `history/drawio-writer/`: the writer that drew the
   drawings in `diagrams/` from the JSONs, with its README (every element, the
   draw.io construct chosen for it, what differs from the SVG and why, and the
   decisions taken) and its comparison against the SVGs (`sweep.md`).
6. **draw.io as the source** - `diagrams/` (2026-09-29). The changes made to
   all 78 drawings since (12 pt text, one arrowhead, the 3x arrow rule), and the
   comparison of the drawings with the original PNGs, are scripts in
   `history/drawio-edits/`, with a README saying which commit each made.
7. **The illustrations** - `history/illustrations/` (2026-09-30): the four
   Fulfilment figures, from Tim McGrath's deck (linked there, not kept) and
   fitted to the UBL PNGs; their pictures (`illustrations/parts/`) and drawings,
   and how to make them again.
8. **The CPFR step illustrations** - `history/illustrations/cpfr/` (2026-10-05):
   the three CPFR step figures, their clip art redrawn (the originals are lost),
   drawn from the UBL PNGs.
9. **Four figures of other notations** - `history/group-a/` (2026-10-05): Ordering and
   Business Information (BPMN), Pre-award and Procurement (phase maps): the TC's own
   sources from the UBL repository, adopted as they are (Ordering's bpmn-js SVG too, until it
   was redrawn as a draw.io BPMN diagram, 2026-10-06); and `history/remaining-figures.md`:
   the figures then still to do.
10. **Three phase and overview figures** - `history/group-b/` (2026-10-05): the IMFM Generic
    Intermodal Freight Process and the two Open-edi figures, drawn from the UBL repository's
    PNGs (no source exists).
11. **Four reference figures** - `history/group-c/` (2026-10-05): Default Validation, Schema
    Dependencies, UDT-QDT and Model Realization, drawn from the UBL repository's PNGs (no
    source exists). With them every figure UBL uses has a source.

12. **Ordering as a draw.io BPMN diagram** - `history/group-a/build_ordering.py` (2026-10-06): the
    figure redrawn from the TC's bpmn-js SVG with draw.io's BPMN shapes, every element linked as in a
    BPMN model, and made its source, so that all 96 are draw.io drawings (`history/group-a/README.md`).
13. **A baseline of all 96** - `baselines/2026-10-06/` (2026-10-06): the comparison scripts of
    `history/drawio-edits/diff/` taught the figures drawn later; and the README cut down to a guide,
    what it held of the record moved here (below).
14. **The build renders them** - `to-ubl-repo/utilities/artwork/` (2026-10-06): once committed, the
    UBL repository's drawings are the source (A3), and its build renders them before Ant
    (`render.sh`), with the tools copied there; tested on a checkout of `ubl-2.6` (README, "In the
    UBL repository: the build renders the drawings").
15. **One picture, one origin** - `tools/drawio_picture.js` (2026-10-06): the render and the export
    of a drawing start at the same point, said once (below, "One picture, one origin").

`history/former-README.md` is the repository's README until 2026-09-29, describing steps 1-4.

## Checked against the UBL repository (2026-10-06)

Checked 2026-10-06 against the UBL repository: the `UBL.xml` of the OASIS Standard
(`ubl-2.5-os`, published 2026-08-12), of `ubl-2.5-iso` and of `ubl-2.6` cites these 96 and no
other, as at `3d81e8a` (CSD03), which this work was read from; `art/`, `htmlart/` and
`images/` have not changed since. `art/` has a 97th PNG, no longer used
(`history/remaining-figures.md`; the commit removes it, A5); two more figures, `UBL-2.2-UseCase` and
`UBL-2.2-UseCaseOverview`, are named only inside an XML comment and have no PNG (the comment is
removed in a commit of its own: README, "Images made from the drawings").

## How the 78 were drawn

The conventions the README states, with what keeping them took (the edits of
`history/drawio-edits/`, 2026-09-29 to 2026-10-05):

Each drawing is built from draw.io's own parts:

- the frame is a **pool** (BPMN palette, "Vertical Pool 1") and each party a
  **lane** in it: widening a lane moves the lanes beside it and grows the pool;
- actions, documents, decisions, starts, ends, fork/join bars and notes are the
  shapes of draw.io's **UML palette**, standing in their lane (a child of it);
- **flows** are attached to their elements at both ends; a guard is the flow's
  own label, a decision's question the diamond's own label;
- CPFR's dashed phase boxes and IMFM's phase rules and names are part of the
  pool, so they move with it;
- drawn at the figures' **natural scale**, with **whole pixels** only and
  **fixed line weights** (1, and 2 for documents and the frame); flows that the
  artwork draws almost level or upright are exactly so;
- **one arrowhead everywhere:** UML's open head, 10 px (`endArrow=open;endSize=10`),
  where the artwork had sizes of 6-17 px and a filled head in the 2.3 customs
  figures; and every arrow at least **3 times its head long** (30 px, the
  stretch after its last bend). Where one was shorter, space was inserted across
  the whole figure, as draw.io's own "insert space" does: a band of height or a
  column of width, everything beyond it moved along, lanes and pool grown (109
  insertions in 35 figures, 1-20 px each; a figure grew by at most 58 px in
  height (Tender Contract Post) and 30 px in width).
  Nothing tilted or came to overlap. A shape the space ran through kept its
  size: it stayed, or moved whole past the space, wherever its flows still met
  it (12 shapes); only one grew, as its flows meet it on both sides of the space
  (CPFR Exception Monitor's "Ordering", 2 px wider);
- **one text size: draw.io's own 12 pt** for every label (no `fontSize` in the
  style). Where a box no longer held its words at 12 pt it was made wider or
  taller about its centre (83 boxes, by 2-18 px), and where that would have taken
  it out of its lane, its label was broken over one more line (10 labels, in the
  two Tender figures with long one-line labels). Words beside a shape (a
  decision's question, "From Order") and guards kept their gap to the shape or
  line: the shape keeps its size, and the words move out by what they grew.

## The editor, tried

Tested by editing Billing with Debit Note in the draw.io editor (web, 31.5.3): a flow
reconnected to another element, an action resized, another relabelled, an action
and a flow from the library added and connected, and a lane added to the pool.
The saved file passed the check, and the model read back out of it changed
exactly as edited. Moving the pool and widening a lane were tried too: all that
belongs to the pool and its lanes moves with them. (Since then all 96 drawings have
been opened and saved again, unchanged, in the live web editor 32.x: the 85 in
"draw.io upgrades tried" (below), the 11 of Groups A, B and C in their READMEs. The desktop app is
not tried yet: README, "Open work".)

## The drawings against their JSON models

With `--against history/diagrams` it also reads the model back out of each
drawing and compares it, field by field, with the JSON model it was drawn from.
At the switch (2026-09-29) all 78 were equal - all but what records how the PNG
was read (a flow's direction confidence, the figure's source PNG), which stays
in the history. After the drawings have been edited, they will differ from the
JSONs, as they should: the JSONs are history now.

## The illustrations against their PNGs

They were made from Tim McGrath's deck, placed where the UBL PNGs have them, and
match those PNGs within 0.5-2.5 % (the baseline's `summary.txt`): see
`history/illustrations/README.md`, which also says how to make them again. They
are held against the baseline like the diagrams, and exported like them, with
these differences: they are not checked by `tools/check_drawio.py` (they hold
no model); the export puts each picture in the SVG as the SVG it is, and prints
`art/` in grey (8 bit), not black and white; and their page is the frame.

## The baselines

`baselines/2026-10-06/`, all 96 drawings as they are now, for later edits to be held against:

- `diagrams/<figure>.drawio`: the 96 drawings, byte for byte as `diagrams/` has them;
- `renders/<figure>.png`: each rendered with draw.io's own code (the pinned viewer,
  32.0.2), as `compare` draws it again (draw.io at scale 1, the browser enlarging), on
  the canvas of its original PNG (grown where the drawing grew), so that `compare` finds
  it as stored (checked 2026-10-06: all 96, pixel for pixel);
- `summary.txt`, `summary.json`: per figure, how it compares with the original
  PNG (red: ink only the PNG has; blue: only the drawing; in %, of the PNG's
  ink, within 2 px per 1480 px of width), and for the 35 figures that grew, the
  same with the space inserted in the PNG too. That comparison draws zoomed, which
  puts each line where it is to the device pixel: for the 85 of the baseline before,
  its numbers are those of 2026-10-05 within the newer draw.io (a median 0.13 points
  apart).

The 11 figures drawn after the 78 were read (Groups A, B, C) are in it too, placed on
their PNG by `history/drawio-edits/diff/one.py`: those drawn on their PNG's pixels at one
scale (Groups B and C, Ordering) are rendered at that scale (red and blue 0.2-5.4 %;
Ordering 0.69 and 0.32 %); the TC's three drawings of Group A, whose page has nothing to
do with their PNG, by their ink (the scale that makes their ink as wide as the PNG's, then
moved onto it; their render is on a canvas that holds the drawing whole): Pre-award and
Procurement 0.00 %, Business Information 3.31 and 30.18 % (its PNG draws its thin lines
too faint to count as ink).

The baselines before are kept as they were. `baselines/2026-10-05/`: the 85 then (the 78
diagrams, the 4 Fulfilment and the 3 CPFR step illustrations), its renders drawn zoomed
with the viewer 31.5.3, so that `compare` against it says "renderer changed" on every
figure, which is not a difference ("draw.io upgrades tried", below); it is `baselines/2026-09-30/`
with the 3 CPFR step figures added. `baselines/2026-09-30/`: the drawings as they were
made the source of truth (commit `3bd91c6`, all edits of `history/drawio-edits/` done;
the Fulfilment figures added on the same day).

## The export: how it is made, and what was decided

The check also fails where a drawing in `to-ubl-repo/images/` is no longer its
source in `diagrams/`: the export is out of date. An export of unchanged
drawings is the same, byte for byte, so it changes nothing in git - whether a
figure is exported alone or with others (each is drawn on a clean page; tried
2026-10-05: all 85 at once, and each CPFR step figure alone, gave the same files).
That holds in one environment. The `.drawio` and `.svg` files are the same anywhere,
but the PNGs' text is rasterised with the container's fonts and font rendering, which
nothing pins: in a newer container (2026-10-06) every PNG came out different, by
0.02-5.9 % of its pixels (median 0.75 %; the most in small web PNGs dense with text),
all at the edges of letters (a label measured: half a pixel apart, 3 % paler); every
line and shape, every `.svg` and `.drawio` the same, and `check_svg.py` passes on both.
Such PNGs are not a change: do not commit them for that alone; re-export only the
figures whose drawing changed. `--report`
writes, per figure, its size, the scale it is fitted to the page at and the
size its text prints at (kept out of `to-ubl-repo/`: it is not for UBL). The
export needs Node with playwright (as `tools/drawio_baseline.py`); the check
Python 3 with pillow.

The SVG is draw.io's own (`getSvg`, the viewer of the pinned release), with
each label made SVG text: draw.io writes a label as HTML, which the browser
lays out as draw.io does; the export reads where each line of it lands and
writes the lines as `<text>` there, turned where the label is (the IMFM phase
names), and checks that every word of the label is in them. The PNGs are
renders of that SVG. Tried on all 78 (2026-09-30): all pass the check; the
SVG's render and draw.io's own agree to 1 px everywhere in all 78 (to the
pixel but for 0.29% of the ink in the median figure: the edges of filled
shapes, half a pixel apart). The SVG rendered by librsvg agrees with Chromium's
render to 1 px but for 0.2% of the ink (tried on three).

The SVGs in `history/diagrams/<figure>/<figure>.svg`, drawn from the JSONs,
are no longer maintained.

### Decided for that export

Decided 2026-09-30, from how the [UBL repository](https://github.com/oasis-tcs/ubl)
publishes its artwork (its README, "Artwork"; `build.xml`; `realta-user-parameters.xml`):

- **What it makes:** a commit for the UBL repository that adds or replaces, per
  figure, `images/<figure>.drawio` (the source), `images/<figure>.svg` (the
  revisable vector file ISO asks for), `art/<figure>.png` (print: 600 dpi, at
  most 3425 px wide, i.e. 5.7 in / 14.5 cm; white background, no border) and
  `htmlart/<figure>.png` (web: at most 750 px wide). Both PNGs are rendered from
  the SVG, so they cannot drift from it. `UBL.xml` keeps pointing at
  `art/<figure>.png`: nothing changes in how UBL is published. Publishing the
  SVG itself: README, "Questions for the TC", B1 (answered 2026-10-06: not now;
  the SVGs go to ISO in a submission of their own). A test build with these files
  through Réalta, the UBL publishing server, is done on the UBL repository's
  side, in a test branch there, not from here.
- **It replaces what is there:** for 20 of the 78 diagrams the UBL repository
  has a source in `images/` under the same name (16 `.svg`, 4 `.drawio`); the
  commit replaces them, and removes the 3 older sources of our figures under
  other names (`UBL 2.3-Common Transportation Report-Process.drawio`,
  `UBL 2.3-ImportDeclaration-Process.drawio`, `UBL 2.3-Transit Declaration Process.drawio`).
  The UBL repository's history keeps them; the commit message names each (5 more
  files there, removed too: README, "Questions for the TC", A2, answered 2026-10-06). The 7 illustrations have no source
  there: the commit adds theirs.
- **The other 11 of the 96** (2026-10-05): the 4 of Group A had a source in `images/`
  (`UBL-2.3-Pre-awardProcess`, `UBL-2.3-ProcurementProcess`, `UBL-2.4-BusinessInformation`:
  `.drawio`; `UBL-2.3-OrderingProcess`: `.svg`, from bpmn.io): the commit replaces those too.
  Ordering's bpmn-js SVG is replaced by the export of its draw.io drawing, and the
  drawing is added (`images/UBL-2.3-OrderingProcess.drawio`): against the UBL PNG,
  0.98 % of its ink is not in the new export and 0.85 % of the export's not in it
  (within 4 px; how draw.io draws the BPMN symbols, `history/group-a/README.md`). The
  3 of Group B (IMFM Generic Intermodal Freight Process, Open-edi Overview and
  Application) and the 4 of Group C (Default Validation, Schema Dependencies, UDT-QDT,
  Model Realization) had no source, as the 78 and the 7 illustrations had none: they are
  drawn from the UBL repository's PNGs (`history/group-b/`, `history/group-c/`). The one
  other figure of the UBL repository, no longer used (`UBL-2.0-BillingwithCreditNoteProcess`),
  is not drawn: the commit removes it (README, "Questions for the TC", A5, answered 2026-10-06).
- **The PNGs:** the drawings are black and white only (`#000000`, `#ffffff`),
  and so is `art/<figure>.png`: 1 bit, a pixel black where the drawing covers
  at least half of it, as line art is printed (at 600 dpi a pixel is 0.04 mm;
  the thinnest line, 1 px at the smallest scale, is 2.4 pixels wide). Checked
  on all 78 against an antialiased render: no pixel at least 3/4 ink turned
  white, none at most 1/4 ink turned black. `htmlart/<figure>.png`, for the
  screen, is 8 bit grey, its edges smoothed. No coloured edges (LCD text) in
  either. All 78: `art/` 2.2 MB, `htmlart/` 1.5 MB, where the UBL repository's
  PNGs of these figures are 13 MB and 3 MB. The 7 illustrations have grey
  pictures, and their `art/` is 8 bit grey, as the UBL PNGs of them are; so is
  that of the 4 figures with a grey fill, marked `ubl-art="grey"` in the drawing:
  Business Information (`history/group-a/`), Schema Dependencies, UDT-QDT and Model
  Realization (`history/group-c/`). 85 print PNGs are 1 bit, 11 grey. A PNG
  is on white when the page round the drawing is (its outer band, 2 % of the
  width): the CPFR step figures are mostly grey panel, as the UBL PNGs are.
- **The SVG is real vector:** text as `<text>`, not in `<foreignObject>` (draw.io
  writes its HTML labels there by default) and not as outlines, which ISO does
  not accept; no embedded bitmap. An illustration's pictures are SVG, each put
  in as a nested `<svg>`, not as an image. A `<use>` inside a part (an Inkscape clone,
  a figure repeated) is made a copy of what it uses, as the SVG may hold no `<use>`.
- **The drawing is the truth; the SVG and PNGs are exports of it.** The SVG does
  not carry the drawing (no draw.io `content` attribute): only the picture, and
  a comment naming `<figure>.drawio` as the file to edit. An SVG edited
  elsewhere would otherwise disagree, unseen, with the drawing inside it.
- **Scale:** as now, each figure is fitted to the page width (5.7 in), or kept
  at its natural size where it is narrower. The export reports per figure the
  scale and the size its text prints at. draw.io's "12 pt" is 12 px, and the
  page is 548 px wide at 96 px/in, so at natural size it prints at 9 pt, and in
  Fulfilment Receipt Advice, the widest of the figures drawn at 12 px (scale 0.39),
  at 3.5 pt, the smallest of all (Pre-award and Procurement are wider still, but their
  text is 40-70 px: `history/group-a/README.md`). Whether to change the drawings to even
  that out: README, "Questions for the TC", B3 (answered 2026-10-06: not now).
- **draw.io's code is pinned:** the export draws with draw.io's viewer of one
  release (`tools/drawio-version.json`, now 32.0.2; the baseline's was 31.5.3), fetched from
  that release's tag in [jgraph/drawio](https://github.com/jgraph/drawio), so an
  export can be made again the same. To move to a newer one, see "Upgrading
  draw.io" in the README.
- **Font:** Helvetica, draw.io's own (no drawing sets `fontFamily`), named in the
  SVG as `Helvetica, Arial, "Liberation Sans", sans-serif`: the three have the
  same widths, so labels fit wherever one of them is present. The renders use
  Liberation Sans, as the baseline's did. No font is embedded (both Helvetica
  and Cambria are licensed).

**If ISO requires its own font** (ISO/CS asks for Cambria in graphics; whether it
does: README, "Questions for the TC", B2, answered 2026-10-06: not now, handled
if ISO requires it in the future): do it for
the ISO deliverables only, never in the drawings. Export the ISO SVGs with the
font set at export time (`fontFamily=Cambria` on every cell), render them with
Cambria or its metric-compatible stand-in Caladea, and check that every label
still fits its box: Cambria's widths differ from Helvetica's. Where one does not
fit, widen the box in the ISO export as the 12 pt edit did (`history/drawio-edits/twelve.py`),
not in the drawing. The OASIS outputs and the drawings keep Helvetica.

## One picture, one origin (2026-10-06)

**What kept coming back.** Holding a render of a drawing against another picture of it went wrong
again and again, each time by a different amount: Business Information's cells left of its page fell
off the render's canvas (fixed in `render-drawio.js` by moving it in); a comparison of the published
PNGs with the renders found them 30-92 % apart for most figures, though they are pictures of the same
drawing; Pre-award came out 1,588 px apart.

**What caused it.** Two rules for where a drawing's picture starts. The export takes draw.io's own:
`getSvg` crops to the drawing's bounds (every shape with its line, every label) and rounds their
corner down to a whole unit; an illustration it crops again, to its frame line's outer edge. The
render (`history/drawio-writer/render-drawio.js`) had a rule of its own, made for its first use, the
comparison with the UBL PNGs in `history/drawio-writer/`: the frame's `ubl-offset` (the 78), else the
page's corner, else (cells left of or above the page) the drawing's bounds. The two differ by an
amount that depends on the drawing: one unit for the 78 (the frame line's outer half: the frame at
10, its picture from 9), the page's empty margin for a drawing with no frame (Pre-award: 1,592
units), a fraction for an illustration. Every tool written since used the render as it was, beside
an export that did not.

**What was done.** Where a picture starts and how large it is, is said once,
`tools/drawio_picture.js`: draw.io's export crop, read from draw.io itself (the translation `getSvg`
draws the model with), not worked out again; an illustration's frame. The export takes its crop from
it (its output the same, byte for byte, in all 384 files of the 96 figures), and `render-drawio.js`
starts there by default (origin `picture`). The PNG coordinates are kept, by name (origin `png`), for
what compares a drawing with its UBL PNG: `history/drawio-edits/diff/` (one.py, cutpng.py) and
`history/drawio-writer/` (run.sh, sweep.sh). `tools/drawio_baseline.py` and `tools/drawio_upgrade.py`
render pictures; a baseline made before (2026-10-06 and earlier) is read as it was made, in PNG
coordinates (its renders are reproduced exactly: four drawings of four kinds, touched, came back
`same-drawing`).

**Checked.** The published PNG of every figure (`to-ubl-repo/art`) against the render of the
drawing's picture at its size: at most 1.2 % of the ink is in one only (VMI Invoicing; most below
0.3 %), within the comparison's tolerance (2 px per 1480 px), where it was 30-92 % before. What is
left is text: a few labels, made SVG text by the export, sit up to a unit from where draw.io's own
label puts them. The comparison deck now makes this check for every figure
(`history/drawio-edits/diff/one.py`, "published PNG vs render"), so that should the two ever part
again, it shows.

## draw.io upgrades tried

**Tried 2026-10-05, 31.5.3 -> 32.0.2:** the export is the same in all 85
figures (SVG, art and htmlart PNGs, pixel for pixel), and so is the render when
draw.io draws at scale 1 and the browser enlarges it (`DRAWIO_RENDER_DEVICE=1`
in `history/drawio-writer/render-drawio.js`; what `drawio_upgrade.py` does): `VERDICT: SAFE`.

**Opened and saved in the live editor (32.1.0, later 32.2.0):** all 85 come back
the same in every cell, style, geometry and stacking order, and render the same
(2026-10-06, 32.2.0: all 96, each held against the baseline 2026-10-06's render too,
`python3 tools/drawio_upgrade.py --editor`: `VERDICT: SAFE`).
What the editor writes differently is the file's form only: it pretty-prints
(ours is one line), omits `x="0"` and `y="0"` (378 attributes), drops trailing
zeros (`554.30` is `554.3`), writes the cells parent by parent, names its own
`host` and drops `type="device"`, and records its window size (`dx`, `dy`). It
adds nothing and removes no style key, even those equal to draw.io's defaults. So
the first save of a drawing in draw.io shows as a change of form in git, not of
content. So the drawings are written in the editor's form (next paragraph).

**The drawings are in the editor's form** (2026-10-05): `tools/drawio_format.py`
writes a `.drawio` as the editor does: pretty-printed, cells parent by parent,
attributes in its order, no `x="0"` or `y="0"`, numbers as JavaScript writes them,
no `type` on `<mxfile>`, `'` as `&#39;`. It reproduces the editor's file byte for
byte for all 85 drawings, but for two things the editor decides itself: the
`host` of `<mxfile>` (ours stays `UBL-TC`) and the window size `dx`, `dy` (some
of ours have none). So a drawing can be compared with the same drawing saved from
the editor by text: `python3 tools/drawio_format.py --diff <ours> <saved>`
shows what differs, and nothing if nothing does. `check_drawio.py` reports a
file that is not in this form; after a script writes one, run
`python3 tools/drawio_format.py <file>`. `drawio_upgrade.py --editor` includes
the text comparison. The rewrite changed no cell, no style, no pixel of any
export or render (`drawio_baseline.py compare`: 85 `same-drawing`); in
`to-ubl-repo/` only the copied `.drawio` files changed.

The baseline's renders (drawn zoomed in draw.io's own view, 3-5 times) differ
in 35 figures, and the reason is draw.io's, not the drawings': zoomed, 31.5.3
rounds an edge label's place along its flow, and the corners of an orthogonal
flow, to whole device pixels, 32.0.2 to whole model pixels (its `getPoint`
and `mxEdgeStyle` now `unscale`), so a label sits up to 3 px apart and a line
a fraction of a pixel. At scale 1, as the export draws, they agree. So
`drawio_baseline.py compare` now draws both drawings at scale 1 too, itself.
The baseline 2026-10-05 stays as it is: its stored renders (`renders/`) were drawn
the old way, so against it every figure carries the note "renderer changed", which
is not a difference. The baseline 2026-10-06 is drawn as `compare` draws, so against
it the note means that the renderer itself changed (a newer pin). The export is
unchanged. 32.1.0 has no tag, so it is not tried.
