# ubl-work-on-svg-images

Editable sources for the artwork of the UBL specification: the **78 UML activity
diagrams** of UBL 2.5 (of its 97 figures), as **draw.io drawings**. UBL publishes
these diagrams as PNG and most of their original sources are lost; these drawings
replace them as the figures' source.

## The source of truth: the draw.io drawings

```
diagrams/<figure>/<figure>.drawio        78 figures, e.g. diagrams/UBL-2.5-BillingwithDebitNoteProcess/
tools/ubl-library.xml                    the UBL shapes, as a draw.io library, for editing
tools/check_drawio.py                    the check, run by hand after an edit
tools/drawio_baseline.py                 holds the drawings against the baseline
tools/export_drawio.js                   exports them for the UBL repository: SVG, PNG
tools/check_svg.py                       checks an export
to-ubl-repo/                             what goes to the UBL repository: the export
baselines/2026-09-30/                    the baseline: the drawings as they are now
```

**Edit a figure by opening its `.drawio` file in draw.io** (the desktop app, or
diagrams.net) and saving it back. Nothing is generated over these files any more.

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

### The model inside each drawing

Each drawing also holds the figure's **model**: what it says, not only how it
looks. Every element carries the model's id and its kind (`ubl-kind`); what the
drawing does not show by itself is kept on the element as a custom property,
visible and editable in draw.io under **Edit Data** (Ctrl+M). A string is kept as
it is, anything else as JSON.

| property | on | what it says |
|---|---|---|
| `ubl-kind` | every element | `frame`, `lane`, `action`, `object` (a document), `decision`, `initial`, `final`, `fork`, `note`, `flow`, `off-page-flow`, `text`, `mark`, `phase-boundary`, `band-divider`, `band-title`, `lane-divider` |
| `ubl-flow` | flow | its kind: `control`, `object`, `goods`, `information`, `precondition` |
| `ubl-guard` | flow | the id of the text that is its guard (the label) |
| `ubl-between`, `ubl-lane` | node | a document passed between parties (the parties, left to right); the lane a node belongs to where it is drawn in another (`null`: none) |
| `ubl-continues`, `ubl-counterpart`, `ubl-port`, `ubl-direction` | off-page flow | the figure where it continues, the flow there, which port, in or out |
| `ubl-text`, `ubl-text-<id>` | element | the id(s) of the text(s) shown as its label; a text's own words where the label shows them otherwise |
| `ubl-label` | node, lane, phase | its own words, where its label shows a text's |
| `ubl-members` | phase | the elements in the phase |
| `ubl-question`, `ubl-unstated`, `ubl-passes-to`, `ubl-linked-process`, `ubl-reference`, `ubl-scope`, `ubl-same-as`, `ubl-trigger`, `ubl-annotates`, `ubl-also-in`, `ubl-defined-in`, `ubl-implied-choice`, `ubl-both-ends`, `ubl-title-shown`, `ubl-title-source`, `ubl-mark`, `ubl-rule`, `ubl-on`, `ubl-meaning`, `ubl-labels`, `ubl-draws`, `ubl-segments` | as the model has them | the model's other facts, as recorded with the TC (see the schema in `history/tools/schema/diagram.schema.json` for each) |
| `ubl-offset` | frame | the margin between page and drawing |

### Editing a drawing

1. Open the figure's `.drawio` file in draw.io.
2. **Open the UBL shape library once:** `tools/ubl-library.xml`, with
   *File › Open Library* in the desktop app (*File › Open Library from ›
   Device* on diagrams.net). It stays in the left panel. Its shapes carry their
   `ubl-kind` already, in the drawings' style:
   - action, document (object node), decision, start, end, fork/join bar
     (horizontal and upright), note, text;
   - a lane: drop it on the pool, and the pool places it after the last lane;
   - a control flow and an object flow: drop one, then drag its ends onto the
     two elements.
3. Draw new elements from that library, not from draw.io's own palettes: a shape
   from those has no `ubl-kind`, and the check below reports it.
4. Tell the model what the drawing cannot show, in *Edit Data* (Ctrl+M) on the
   element: for a document drawn on a lane divider, the parties it passes between
   (`ubl-between`, e.g. `["lane-buyer", "lane-seller"]`); for a new flow, its kind
   if it is neither a control nor an object flow (`ubl-flow`). The check warns
   where these are missing.
5. Save, and run the check.

Tested in the draw.io editor (web, 31.5.3) on Billing with Debit Note: a flow
reconnected to another element, an action resized, another relabelled, an action
and a flow from the library added and connected, and a lane added to the pool.
The saved file passed the check, and the model read back out of it changed
exactly as edited. Moving the pool and widening a lane were tried too: all that
belongs to the pool and its lanes moves with them.

### Checking a drawing

```sh
python3 tools/check_drawio.py diagrams/*/*.drawio
```

Run it by hand after an edit. It checks the conventions a drawing must keep:
every element has a known `ubl-kind` and a unique id; the lanes are in the pool
and every node in a lane; every flow is attached at both ends (a flow leaving
the page at one); a guard is used once. A finding makes it fail (exit status 1).
It also **warns** where the model is poorer than it should be - a flow without
its kind (`ubl-flow`), a document across a lane divider without the parties it
passes between (`ubl-between`) - and where an arrow is shorter than 3 times its
head: make room in draw.io by Ctrl+Shift+dragging on the background.

With `--against history/diagrams` it also reads the model back out of each
drawing and compares it, field by field, with the JSON model it was drawn from.
At the switch (2026-09-29) all 78 were equal - all but what records how the PNG
was read (a flow's direction confidence, the figure's source PNG), which stays
in the history. After the drawings have been edited, they will differ from the
JSONs, as they should: the JSONs are history now.

### The baseline: `baselines/2026-09-30/`

The drawings as they were made the source of truth (commit `3bd91c6`, all edits
of `history/drawio-edits/` done), for later edits to be held against:

- `diagrams/<figure>.drawio`: the 78 drawings;
- `renders/<figure>.png`: each rendered with draw.io's own code (viewer
  31.5.3), at the size of the original PNG (grown where the drawing grew);
- `summary.txt`, `summary.json`: per figure, how it compares with the original
  PNG (red: ink only the PNG has; blue: only the drawing; in %, of the PNG's
  ink), and for the 35 figures that grew, the same with the space inserted in
  the PNG too.

The PDF of that comparison is not kept: `history/drawio-edits/diff/run.sh` makes
it again from the baseline's commit.

```sh
python3 tools/drawio_baseline.py compare baselines/2026-09-30 [--out <dir>] [<figure> ...]
```

Run it by hand after an edit. Per figure it says `same` (the baseline's file,
byte for byte), `same-drawing` (the file differs, not the model, not a pixel),
`model` (the model differs; what, is listed) or `DRAWING` (pixels differ;
with `--out`, a picture shows where: red only in the baseline, blue only in the
drawing). Both are rendered afresh, the same way, and compared with no
tolerance; where the baseline no longer renders as it did, it says so.
A new baseline is made with `tools/drawio_baseline.py make <baseline dir> <diff
dir>`, from a run of `history/drawio-edits/diff/run.sh` on the same drawings.

### Images made from the drawings: `to-ubl-repo/`

`to-ubl-repo/` holds everything that is to be committed to the UBL repository,
and nothing else, laid out as there: copied over a clone of it (branch
`ubl-2.5`), it adds or replaces, per figure, `images/<figure>.drawio` and
`images/<figure>.svg`, `art/<figure>.png` and `htmlart/<figure>.png`. Nothing
in it is edited by hand: after an edit of a drawing, export it again and check.

```sh
NODE_PATH=$(npm root -g) node tools/export_drawio.js [--report <file.json>] to-ubl-repo diagrams/*/*.drawio
python3 tools/check_svg.py to-ubl-repo
```

The check also fails where a drawing in `to-ubl-repo/images/` is no longer its
source in `diagrams/`: the export is out of date. An export of unchanged
drawings is the same, byte for byte, so it changes nothing in git. `--report`
writes, per figure, its size, the scale it is fitted to the page at and the
size its text prints at (kept out of `to-ubl-repo/`: it is not for UBL). The
export needs Node with playwright (as `tools/drawio_baseline.py`); the check
Python 3 with pillow.

**The commit to the UBL repository also removes** 3 older sources of our
figures, under other names, which a folder of files cannot say:
`images/UBL 2.3-Common Transportation Report-Process.drawio`,
`images/UBL 2.3-ImportDeclaration-Process.drawio`,
`images/UBL 2.3-Transit Declaration Process.drawio`.

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

Decided for that export (2026-09-30), from how the [UBL repository](https://github.com/oasis-tcs/ubl)
publishes its artwork (its README, "Artwork"; `build.xml`; `realta-user-parameters.xml`):

- **What it makes:** a commit for the UBL repository that adds or replaces, per
  figure, `images/<figure>.drawio` (the source), `images/<figure>.svg` (the
  revisable vector file ISO asks for), `art/<figure>.png` (print: 600 dpi, at
  most 3425 px wide, i.e. 5.7 in / 14.5 cm; white background, no border) and
  `htmlart/<figure>.png` (web: at most 750 px wide). Both PNGs are rendered from
  the SVG, so they cannot drift from it. `UBL.xml` keeps pointing at
  `art/<figure>.png`: nothing changes in how UBL is published. Publishing the
  SVG itself (as `ubl-2.4-os-iso-pub` did, with SVGs that only wrapped the
  PNGs) is for a wider discussion with the TC.
- **It replaces what is there:** for 20 of the 78 figures the UBL repository
  has a source in `images/` under the same name (16 `.svg`, 4 `.drawio`); the
  commit replaces them, and removes the 3 older sources of our figures under
  other names (`UBL 2.3-Common Transportation Report-Process.drawio`,
  `UBL 2.3-ImportDeclaration-Process.drawio`, `UBL 2.3-Transit Declaration Process.drawio`).
  The UBL repository's history keeps them; the commit message names each.
- **Only the 78:** the other 19 figures of the UBL repository are left as they
  are, for a later session. One is no longer used (`UBL-2.0-BillingwithCreditNoteProcess`);
  4 have a source in `images/` (`UBL-2.3-Pre-awardProcess`, `UBL-2.3-ProcurementProcess`,
  `UBL-2.4-BusinessInformation`: `.drawio`; `UBL-2.3-OrderingProcess`: `.svg`);
  14 have none, and most are not activity diagrams (Fulfilment 1-4, CPFR Steps
  1-2, 3-4-5 and 6-9, IMFM Generic Intermodal Freight Process, Open-edi
  Application and Overview, Default Validation, Schema Dependencies, UDT-QDT,
  Model Realization).
- **The PNGs:** the drawings are black and white only (`#000000`, `#ffffff`),
  and so is `art/<figure>.png`: 1 bit, a pixel black where the drawing covers
  at least half of it, as line art is printed (at 600 dpi a pixel is 0.04 mm;
  the thinnest line, 1 px at the smallest scale, is 2.4 pixels wide). Checked
  on all 78 against an antialiased render: no pixel at least 3/4 ink turned
  white, none at most 1/4 ink turned black. `htmlart/<figure>.png`, for the
  screen, is 8 bit grey, its edges smoothed. No coloured edges (LCD text) in
  either. All 78: `art/` 2.2 MB, `htmlart/` 1.5 MB, where the UBL repository's
  PNGs of these figures are 13 MB and 3 MB.
- **The SVG is real vector:** text as `<text>`, not in `<foreignObject>` (draw.io
  writes its HTML labels there by default) and not as outlines, which ISO does
  not accept; no embedded bitmap.
- **The drawing is the truth; the SVG and PNGs are exports of it.** The SVG does
  not carry the drawing (no draw.io `content` attribute): only the picture, and
  a comment naming `<figure>.drawio` as the file to edit. An SVG edited
  elsewhere would otherwise disagree, unseen, with the drawing inside it.
- **Scale:** as now, each figure is fitted to the page width (5.7 in), or kept
  at its natural size where it is narrower. The export reports per figure the
  scale and the size its text prints at. draw.io's "12 pt" is 12 px, and the
  page is 548 px wide at 96 px/in, so at natural size it prints at 9 pt, and in
  the widest figure (Fulfilment Receipt Advice, scale 0.39) at 3.5 pt. Changing
  the drawings to even that out is for later.
- **draw.io's code is pinned:** the export draws with draw.io's viewer of one
  release (31.5.3, the baseline's), fetched from that release's tag in
  [jgraph/drawio](https://github.com/jgraph/drawio), so an export can be made
  again the same. **Maintenance, for a separate session:** from time to time
  move to a newer release. Export all 78 with both releases, compare the SVGs
  and the renders, and check with `tools/drawio_baseline.py` that the drawings
  still render as the baseline. Then change the pin, and make a new baseline
  if the renders changed.
- **Font:** Helvetica, draw.io's own (no drawing sets `fontFamily`), named in the
  SVG as `Helvetica, Arial, "Liberation Sans", sans-serif`: the three have the
  same widths, so labels fit wherever one of them is present. The renders use
  Liberation Sans, as the baseline's did. No font is embedded (both Helvetica
  and Cambria are licensed).

**If ISO requires its own font** (ISO/CS asks for Cambria in graphics): do it for
the ISO deliverables only, never in the drawings. Export the ISO SVGs with the
font set at export time (`fontFamily=Cambria` on every cell), render them with
Cambria or its metric-compatible stand-in Caladea, and check that every label
still fits its box: Cambria's widths differ from Helvetica's. Where one does not
fit, widen the box in the ISO export as the 12 pt edit did (`history/drawio-edits/twelve.py`),
not in the drawing. The OASIS outputs and the drawings keep Helvetica.

## How we got here: `history/`

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

`history/README.md` is the repository's former README, describing steps 1-4.
