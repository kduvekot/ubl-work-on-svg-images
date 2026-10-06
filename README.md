# ubl-work-on-svg-images

Editable sources for the artwork of the UBL specification, for all **96 figures** UBL 2.5
uses: the **78 UML activity diagrams**, **7 illustrations** (the 4 Fulfilment figures:
shipments and consignments; the 3 CPFR step figures), **4 figures of other notations**
(2 BPMN-style drawings, 2 phase maps: `history/group-a/`), **3 phase and overview
figures** (`history/group-b/`) and **4 reference figures** (`history/group-c/`), the last
two groups drawn from the UBL PNGs: all of them **draw.io drawings**, one set of the same
kind (the Ordering Process since 2026-10-06, redrawn as a draw.io BPMN diagram from the
TC's bpmn-js SVG). UBL publishes these figures as PNG and most of their original sources
are lost; these drawings replace them as the figures' source.

Checked 2026-10-06 against the UBL repository: the `UBL.xml` of the OASIS Standard
(`ubl-2.5-os`, published 2026-08-12), of `ubl-2.5-iso` and of `ubl-2.6` cites these 96 and no
other, as at `3d81e8a` (CSD03), which this work was read from; `art/`, `htmlart/` and
`images/` have not changed since. `art/` has a 97th PNG, no longer used
(`history/remaining-figures.md`); two more figures, `UBL-2.2-UseCase` and
`UBL-2.2-UseCaseOverview`, are named only inside an XML comment and have no PNG.

What the TC still has to decide is in one place, near the end: "Questions for the TC"
(questions A1-A5 before the commit to the UBL repository).

## The source of truth: the draw.io drawings

```
diagrams/<figure>/<figure>.drawio        96 figures, e.g. diagrams/UBL-2.5-BillingwithDebitNoteProcess/
                                         (78 diagrams, 7 illustrations: UBL-2.2-Fulfilment-1simple ...,
                                         4 of BPMN or phase maps: UBL-2.3-OrderingProcess ...,
                                         3 phase or overview figures: UBL-2.2-Open-edi-Overview ...,
                                         and 4 reference figures: UBL-2.2-UDT-QDT ...)
illustrations/parts/*.svg                the pictures the illustrations are made of, to edit
tools/embed_parts.py                     puts an edited picture into the illustrations
tools/ubl-library.xml                    the UBL shapes, as a draw.io library, for editing
tools/check_drawio.py                    the check, run by hand after an edit
tools/drawio_baseline.py                 holds the drawings against the baseline
tools/drawio_format.py                   writes a drawing as draw.io's editor does (a text diff against the editor's)
tools/export_drawio.js                   exports them for the UBL repository: SVG, PNG
tools/check_svg.py                       checks an export
tools/drawio_upgrade.py                  is there a newer draw.io, and does it change anything
tools/drawio_editor_roundtrip.js         opens and saves drawings in the live editor (for drawio_upgrade.py --editor)
tools/drawio-version.json                the pinned draw.io release (the one place)
to-ubl-repo/                             what goes to the UBL repository: the export
baselines/2026-10-06/                    the baseline: all 96 drawings as they are now (2026-10-05, 2026-09-30: the ones before)
```

**Edit a figure by opening its `.drawio` file in draw.io** (the desktop app, or
diagrams.net) and saving it back. Nothing is generated over these files any more.

The rest of this section is about the 78 diagrams. The 7 illustrations are
pictures, not diagrams, and have sections of their own (below). The 11 figures of
other notations, which have no pool of lanes, are described in their own READMEs:
the 4 of Group A (`history/group-a/README.md`: BPMN, Ordering and Business Information;
phase maps, Pre-award and Procurement), three of them **the TC's own files, adopted as
they are**, and Ordering, whose source in the UBL repository is a bpmn-js SVG, redrawn
from that SVG as a draw.io BPMN diagram (2026-10-06; "Ordering, a BPMN drawing", below);
the 3 phase and overview figures of Group B (`history/group-b/README.md`) and the 4
reference figures of Group C (`history/group-c/README.md`), drawn from the UBL PNGs.
Real BPMN 2.0 files for the BPMN figures are a future session (`history/group-a/README.md`).
`tools/check_drawio.py` checks them for the form, their ids, attached flows and their
kinds (they carry `ubl-notation`); the TC's three have no kinds, which it says.

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

Tested by editing Billing with Debit Note in the draw.io editor (web, 31.5.3): a flow
reconnected to another element, an action resized, another relabelled, an action
and a flow from the library added and connected, and a lane added to the pool.
The saved file passed the check, and the model read back out of it changed
exactly as edited. Moving the pool and widening a lane were tried too: all that
belongs to the pool and its lanes moves with them. (Since then all 96 drawings have
been opened and saved again, unchanged, in the live web editor 32.x: the 85 in
"Upgrading draw.io", the 11 of Groups A, B and C in their READMEs. The desktop app is
not tried yet: "Open work".)

### Ordering, a BPMN drawing

`UBL-2.3-OrderingProcess` is drawn with draw.io's BPMN shapes, and holds its BPMN model
as the 78 hold theirs (`history/group-a/README.md`, "Ordering as a draw.io BPMN
diagram"): every element's id is its BPMN id (`Task_1bnlp2b`, `MessageFlow_0w3w0y5`, ...),
its kind is `ubl-kind` (`pool`, `task`, `gateway`, `event`, `flow`, `message-flow`) and its
BPMN type `ubl-bpmn-type` (`participant`, `task`, `exclusiveGateway`, `startEvent`,
`endEvent`, `sequenceFlow`, `messageFlow`; an end event also `ubl-bpmn-event-definition`,
`terminateEventDefinition`). Edit it with draw.io's BPMN palette (*More Shapes › BPMN*):
put a new task, gateway or event in its pool, attach a flow at both ends, and give a
flow its name as its own label; then give the new element, in *Edit Data* (Ctrl+M), its
`ubl-kind` and `ubl-bpmn-type`. `tools/check_drawio.py` reports an element without them,
and a flow not attached. This model is what an official `.bpmn` will be written from
("Questions for the TC", C3).

### The illustrations: the Fulfilment figures

`UBL-2.2-Fulfilment-1simple`, `-2split`, `-3intermediary` and `-4consolidated`
are not UML diagrams but pictures for the reader: parties, documents and
consignments, with the shipments and consignments between them. Their drawings
are made of

- **pictures**: SVG parts, embedded in the drawing as images, each element
  naming its part (`ubl-part`, under Edit Data): the Supplier, the Buyer, the
  forwarder, Supplier B, Buyer B, two parcels (the clip art of the deck they
  come from), the document and the pallet of boxes; the parts are kept as files
  in `illustrations/parts/`;
- **arrows**: draw.io lines, 6 pt, solid (a consignment) or dotted (a shipment);
- **labels**: the grey SHIPMENT and CONSIGNMENT boxes, and the texts, in
  Helvetica at the sizes the figure has them (not 12 pt);
- **the frame**, an element of `ubl-kind` `illustration`: this is what tells
  the tools a figure is an illustration. Its `ubl-png-scale` is the PNG's px per
  the drawing's: the drawing's origin is the frame's outer corner, so that the
  drawing lands on the UBL PNG at that multiple.

**Edit** in draw.io: move, resize, relabel, add an arrow or a label. A picture
is one image in draw.io; **to change a picture**, edit its part in
`illustrations/parts/` with an SVG editor (Inkscape, say), then put it into
every drawing that uses it:

```sh
python3 tools/embed_parts.py
```

They were made from Tim McGrath's deck, placed where the UBL PNGs have them, and
match those PNGs within 0.5-2.5 % (the baseline's `summary.txt`): see
`history/illustrations/README.md`, which also says how to make them again. They
are held against the baseline like the diagrams, and exported like them, with
these differences: they are not checked by `tools/check_drawio.py` (they hold
no model); the export puts each picture in the SVG as the SVG it is, and prints
`art/` in grey (8 bit), not black and white; and their page is the frame.

### The CPFR step illustrations

`UBL-2.2-CPFR-Steps1-2`, `-Steps3-4-5` and `-Steps6-9` are drawn the same way:
illustrations (frame of `ubl-kind` `illustration`), their flowcharts in
draw.io's shapes, their pictures the parts `illustrations/parts/cpfr-*.svg`:
the CPFR figures' clip art, redrawn (the originals are Visio stencil art, and
lost). How the parts and the drawings were made:
`history/illustrations/cpfr/README.md`.

### Checking a drawing

```sh
python3 tools/check_drawio.py diagrams/*/*.drawio
```

(An illustration is not checked: it says so.)

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

### The baseline: `baselines/2026-10-06/`

All 96 drawings as they are now, for later edits to be held against:

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
figure, which is not a difference ("Upgrading draw.io"); it is `baselines/2026-09-30/`
with the 3 CPFR step figures added. `baselines/2026-09-30/`: the drawings as they were
made the source of truth (commit `3bd91c6`, all edits of `history/drawio-edits/` done;
the Fulfilment figures added on the same day).

```sh
python3 tools/drawio_baseline.py compare baselines/2026-10-06 [--out <dir>] [<figure> ...]
```

Run it by hand after an edit. Per figure it says `same` (the baseline's file,
byte for byte), `same-drawing` (the file differs, not the model, not a pixel),
`model` (the model differs; what, is listed) or `DRAWING` (pixels differ;
with `--out`, a picture shows where: red only in the baseline, blue only in the
drawing). Both are rendered afresh, the same way, and compared with no
tolerance; where the baseline no longer renders as it did (a newer pin), it says so.
A figure that is not in the baseline says `new` and is not compared: it is not a
difference (none in 2026-10-06; against 2026-10-05, the 11 of Groups A, B and C).

A new baseline is a new dated folder, made only when asked for, from a run of the
comparison of the drawings with the original PNGs (it also makes the PDF of it, which
is not kept, about 36 MB):

```sh
UBL=<clone of the UBL repository at 3d81e8a> history/drawio-edits/diff/run.sh <diff dir>
python3 tools/drawio_baseline.py make <baseline dir> <diff dir> [<figure> ...]
```

With figures named, only those are added to (or replaced in) the baseline, and a run of
`history/drawio-edits/diff/one.py` on those figures is enough.

### Images made from the drawings: `to-ubl-repo/`

`to-ubl-repo/` holds everything that is to be committed to the UBL repository,
and nothing else, laid out as there: copied over a clone of it, it adds or
replaces, per figure, `images/<figure>.drawio` and
`images/<figure>.svg`, `art/<figure>.png` and `htmlart/<figure>.png`. Nothing
in it is edited by hand: after an edit of a drawing, export it again and check.

Which branch it goes to is for the TC ("Questions for the TC", A1); the artwork is
the same on all of them, so `to-ubl-repo/` applies to any as it is.

```sh
NODE_PATH=$(npm root -g) node tools/export_drawio.js [--report <file.json>] to-ubl-repo diagrams/*/*.drawio
python3 tools/check_svg.py to-ubl-repo
```

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

**The commit to the UBL repository also removes** 3 older sources of our
figures, under other names, which a folder of files cannot say:
`images/UBL 2.3-Common Transportation Report-Process.drawio`,
`images/UBL 2.3-ImportDeclaration-Process.drawio`,
`images/UBL 2.3-Transit Declaration Process.drawio`.

Its `images/` has **5 more files** that are none of the 96 and that `UBL.xml` does not
use: whether the commit removes them too is "Questions for the TC", A2.

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

#### Decided for that export

Decided 2026-09-30, from how the [UBL repository](https://github.com/oasis-tcs/ubl)
publishes its artwork (its README, "Artwork"; `build.xml`; `realta-user-parameters.xml`):

- **What it makes:** a commit for the UBL repository that adds or replaces, per
  figure, `images/<figure>.drawio` (the source), `images/<figure>.svg` (the
  revisable vector file ISO asks for), `art/<figure>.png` (print: 600 dpi, at
  most 3425 px wide, i.e. 5.7 in / 14.5 cm; white background, no border) and
  `htmlart/<figure>.png` (web: at most 750 px wide). Both PNGs are rendered from
  the SVG, so they cannot drift from it. `UBL.xml` keeps pointing at
  `art/<figure>.png`: nothing changes in how UBL is published. Publishing the
  SVG itself: "Questions for the TC", B1. A test build with these files
  through Réalta, the UBL publishing server, is done on the UBL repository's
  side, in a test branch there, not from here.
- **It replaces what is there:** for 20 of the 78 diagrams the UBL repository
  has a source in `images/` under the same name (16 `.svg`, 4 `.drawio`); the
  commit replaces them, and removes the 3 older sources of our figures under
  other names (`UBL 2.3-Common Transportation Report-Process.drawio`,
  `UBL 2.3-ImportDeclaration-Process.drawio`, `UBL 2.3-Transit Declaration Process.drawio`).
  The UBL repository's history keeps them; the commit message names each (5 more
  files there: "Questions for the TC", A2). The 7 illustrations have no source
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
  is left as it is: whether it stays is "Questions for the TC", A5.
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
  that out: "Questions for the TC", B3.
- **draw.io's code is pinned:** the export draws with draw.io's viewer of one
  release (`tools/drawio-version.json`, now 32.0.2; the baseline's was 31.5.3), fetched from
  that release's tag in [jgraph/drawio](https://github.com/jgraph/drawio), so an
  export can be made again the same. To move to a newer one, see "Upgrading
  draw.io" below.
- **Font:** Helvetica, draw.io's own (no drawing sets `fontFamily`), named in the
  SVG as `Helvetica, Arial, "Liberation Sans", sans-serif`: the three have the
  same widths, so labels fit wherever one of them is present. The renders use
  Liberation Sans, as the baseline's did. No font is embedded (both Helvetica
  and Cambria are licensed).

**If ISO requires its own font** (ISO/CS asks for Cambria in graphics; whether it
does: "Questions for the TC", B2): do it for
the ISO deliverables only, never in the drawings. Export the ISO SVGs with the
font set at export time (`fontFamily=Cambria` on every cell), render them with
Cambria or its metric-compatible stand-in Caladea, and check that every label
still fits its box: Cambria's widths differ from Helvetica's. Where one does not
fit, widen the box in the ISO export as the 12 pt edit did (`history/drawio-edits/twelve.py`),
not in the drawing. The OASIS outputs and the drawings keep Helvetica.

## Upgrading draw.io

`python3 tools/drawio_upgrade.py --check` says where draw.io is: the pin
(`tools/drawio-version.json`), the newest release that can be pinned (the
`VERSION` on jgraph/drawio's `dev` branch, if its tag has a viewer; the GitHub
API is not needed), and the live version of app.diagrams.net, the editor people
use, which can be ahead of every tag. Exit 1: a newer release can be pinned.

`python3 tools/drawio_upgrade.py [--to <version>] [--out <dir>]` then exports
all 96 drawings with the pin and with the candidate and compares, per figure,
the SVG (but for the version in its comment), both PNGs and the viewer render
at the baseline's canvas, pixel for pixel; where pixels differ it writes a
red/blue image. It ends in `VERDICT: SAFE` (nothing changed, exit 0) or
`VERDICT: REVIEW` (exit 1, with what differs). It takes about 4 minutes, needs
Node with playwright and Python with numpy and Pillow, and never changes the pin
or the baseline. Run it from a session as it is; the report says what to do.

`python3 tools/drawio_upgrade.py --editor` is the other half: what the editor does
to a drawing. It opens each drawing in the live editor (embed.diagrams.net in
headless Chromium, through `tools/drawio_editor_roundtrip.js`: the newest
version, which can be ahead of every tag), saves it again, and compares what
came back with what went in: every cell (attributes, style, geometry as numbers,
place in its parent's stacking order) and the render. About 5 minutes. It needs
the proxy's CA in the browser's trust store, once per environment. The environment may have
put it there already: `certutil -d sql:$HOME/.pki/nssdb -L` then lists `ccr-agent-proxy` and
`ccr-agent-proxy-2`. If not (`apt-get install libnss3-tools` for `certutil`), import both
certificates of `/root/.ccr/agent-proxy-ca.crt` (`certutil -A` takes only the first of a
file; do not run `-N` on an existing database, it hangs):

```sh
csplit -s -z -f /tmp/proxy-ca- /root/.ccr/agent-proxy-ca.crt '/BEGIN CERTIFICATE/' '{*}'
i=0; for f in /tmp/proxy-ca-*; do i=$((i + 1))
  certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n ccr-agent-proxy$([ $i -gt 1 ] && echo -$i) -i $f; done
```

To move: change `version` in `tools/drawio-version.json`; export all again
(`to-ubl-repo/`: every SVG changes by the version in its comment, which names
the release it was made with); `python3 tools/check_svg.py to-ubl-repo`; and,
if the renders changed, make a new baseline from them, so that
`drawio_baseline.py compare` does not report the version as a change of every
drawing.

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

### Before a pull request

Whatever changed (a drawing, a tool, the pin), in this order, from the repository's
root (Node with playwright, Python with numpy and Pillow, and Chromium as
`tools/export_drawio.js` says):

1. **A drawing edited, or written by a script:** it is in the editor's form (saved
   from draw.io it is; a script's file: `python3 tools/drawio_format.py <file>`).
2. `python3 tools/check_drawio.py diagrams/*/*.drawio`: conventions, and the form.
3. `python3 tools/drawio_baseline.py compare baselines/2026-10-06`: only the
   drawings edited may differ, and each says how. The baseline itself is history:
   it is never edited; a new baseline is a new dated folder, made only when
   asked for.
4. `NODE_PATH=$(npm root -g) node tools/export_drawio.js to-ubl-repo diagrams/*/*.drawio`
   and `python3 tools/check_svg.py to-ubl-repo`: every figure `ok`. In another
   container than the one the PNGs were made in, export only the figures edited (see
   "Images made from the drawings"). The export goes
   in the same commit as the drawing (the check fails on a stale one), and
   nothing in `to-ubl-repo/` is edited by hand.
5. `python3 tools/drawio_upgrade.py --check`: the pin is the newest tag, or it
   says so. Do this at the start of a session and before anything goes to the UBL
   repository. A newer tag: `python3 tools/drawio_upgrade.py` (exports and renders
   with both, ends in `SAFE` or `REVIEW`), then `python3 tools/drawio_upgrade.py --editor`
   (the live editor opens and saves every drawing; needs the proxy's CA in the
   browser's trust store, above). `SAFE` twice: change `version` in
   `tools/drawio-version.json`, export all again (step 4), and expect only the
   version in each SVG's comment to change. `REVIEW`: look at the diff images, and
   do not move the pin until what differs is understood.
6. A pin move is a pull request of its own, with the report's numbers in it, and
   the README's account ("Tried ...") brought up to date. The live editor can be
   ahead of every tag: that is said by `--check`, and is not a reason to wait.

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

`history/README.md` is the repository's former README, describing steps 1-4.

## Questions for the TC

Every question this work leaves for the TC, in one place (collected 2026-10-06). Elsewhere
in this repository a question is only pointed to, by its number here. A is to be settled
before the commit to the UBL repository; B is how UBL publishes the figures; C is BPMN and
the lost originals; D is what the diagrams say, for when they are next revised.

### A. Before the commit to the UBL repository

**A1. Which branch?** This work was read from `ubl-2.5` at `3d81e8a` (CSD03). Since then
UBL 2.5 has become an OASIS Standard (`ubl-2.5-os`, published 2026-08-12; `ubl-2.5-iso` for ISO) and
the work goes on in `ubl-2.6` (2.6 CSD01). `art/`, `htmlart/` and `images/` are the same on
all of them as at `3d81e8a` (checked 2026-10-06), so `to-ubl-repo/` applies to any of them
as it is. Suggested: `ubl-2.6`, unless the SVGs are wanted for the ISO submission of 2.5.

**A2. Remove 5 more files from `images/`?** Found 2026-10-06: none is a source of the 96
under its name, and `UBL.xml` uses none; all came with the TC's initial load of 2021-05-15.
Two are older sources of our figures, as the 3 the commit removes ("Images made from the
drawings"): `UBL-2.3-GoodsCertificateProcess.svg` (Goods Certificate Export, under its
former name: the same words) and `UBL-2.3-RequestForProofOfReexportationProcess-old.svg` (an
earlier, smaller version of that figure). Three are of figures UBL does not have, none ever
with a PNG in `art/` on any branch: `UBL-2.2-Tender-Contract.svg` (an earlier, smaller Tender
Contract, 7 labels; `-Pre` and `-Post` have its place), and
`UBL-2.2-Tender-TenderingProcess.svg` with `UBL-2.3-Tender-TenderingProcess.drawio` (one
overview of the tendering process, in both). Suggested: remove all five; the UBL
repository's history keeps them.

**A3. How is a figure edited once it is in the UBL repository?** Its README's "Artwork"
still says to export the PNG from draw.io by hand (600 dpi) and scale the `htmlart/` copy in
GIMP. Done that way to one of these figures, its SVG goes stale unseen and its PNGs are
unlike the others (not 1 bit, not rendered from the SVG). The section should change in the
same commit: edit `images/<figure>.drawio`, then export as here. To decide: where the tools
are (here, or moved to the UBL repository), and which copy of the drawings is edited from
then on (`diagrams/` here, or `images/` there), so that a figure has one source.

**A4. May the illustrations' clip art be published as it is?** The published SVGs carry it
as vector art.

- *The CPFR step figures:* the people were traced from copies of the Visio stencil's own
  pictures (the originals are lost); they are drawn anew, but follow those drawings
  closely. If that is not acceptable, the people would have to be drawn freely
  (pictograms). The document, the clipboard, the desk's things and the stack of documents
  are this work's own drawing (`history/illustrations/cpfr/README.md`).
- *The Fulfilment figures:* 7 parts (the Supplier, the Buyer, the forwarder, Supplier B,
  Buyer B, two parcels) are the clip art of Tim McGrath's deck, converted (WMF to SVG), and
  the document is traced from the deck's picture; the pallet is this work's own drawing
  (the deck has a stock photo) (`history/illustrations/README.md`).

**A5. Remove `art/UBL-2.0-BillingwithCreditNoteProcess.png`?** It is in the UBL repository's
`art/` (not in `htmlart/`) and not used: `UBL.xml` does not cite it. If the TC keeps it, it
is a UML activity diagram and would be the 79th drawing: the pipeline of `history/` does
not need to be run again for it, the drawing is made like the others
(`history/drawio-writer/README.md`; `history/remaining-figures.md`).

### B. How UBL publishes the figures (after the commit)

**B1. Publish the SVG itself?** `UBL.xml` keeps pointing at `art/<figure>.png`: the commit
changes nothing in how UBL is published. Publishing the SVG (as `ubl-2.4-os-iso-pub` did,
with SVGs that only wrapped the PNGs) is for a wider discussion.

**B2. Does ISO require its own font in graphics?** ISO/CS asks for Cambria. If it does, it
is done for the ISO deliverables only, at export time, never in the drawings ("Decided for
that export", "If ISO requires its own font").

**B3. Even out the printed text size?** Each figure is fitted to the page width, so
draw.io's 12 px text prints at 9 pt at natural size and at 3.5 pt in Fulfilment Receipt
Advice, the widest of the figures drawn at 12 px (scale 0.39); the export reports it per
figure. Evening it out means changing the drawings. A related question: Pre-award and
Procurement are the TC's drawings at
3425 px wide (text 40-70 px, 8 px lines), not at the others' 12 px convention; a version
rescaled to 0.3 exists as an experiment and could be adopted (`history/group-a/README.md`,
"`redrawn/`").

### C. BPMN, and the lost originals

**C1. Should the 78 UML activity diagrams become BPMN too?** Their drawings use BPMN pools
and lanes. Official BPMN 2.0 files are required (by the UBL editor, Kees Duvekot) for the two BPMN figures,
Ordering and Business Information: a session of its own (`history/group-a/README.md`,
"Future session"). The two phase maps stay draw.io.

**C2. Business Information's envelopes, in its BPMN version.** A message flow joins two
elements directly; the envelope can become a message event or a send/receive task (which
changes what the figure says) or be dropped. Its message flows that end at an end event (not
a message end event) need the same decision.

**C3. If Ordering's `.bpmn` stays lost, is a reconstruction acceptable?** The original,
`UBL-2.3-OrderingProcess.bpmn`, is attached to the `ubl` list's mail of 2019-05-07
("UBL-171 - BPMN diagram + SVG") and is not found yet (`history/group-a/README.md`). The
reconstruction would be written from the figure's draw.io BPMN drawing
(`diagrams/UBL-2.3-OrderingProcess/`, made 2026-10-06 from the bpmn-js SVG, which came
from the model): the original's BPMN ids, places and bends, with every flow's `sourceRef`
and `targetRef` and every element's participant made explicit. Little would be lost, and
the file would say it is a reconstruction. The drawing is the source now: an edit made to
it before then becomes part of the reconstruction.

**C4. Can someone with a browser search the `ubl` list's archive?** The archives
(`lists.oasis-open.org`, `lists-archive.oasis-open.org`) refuse a script. Wanted: the
2019-05-07 attachment above, and the posts of 2016-2020 around the figures' creation (UBL
2.2: the IMFM, Open-edi, Schema Dependencies and UDT/QDT figures; UBL 2.3: Model
Realization), where an attachment may be a source. Worth an hour: search for `svg`,
`visio`, `vsd`, `png`, `bpmn` and the figure names. A find goes in
`history/<group>/sources/` (`history/remaining-figures.md`, `history/group-a/README.md`).

### D. What the diagrams say, for their next revision

The drawings stay faithful to the artwork. These are the points where the artwork itself may
be wrong, raised in the review of the figures with the TC (2026-09, the questions `q7` to
`q15`: `history/docs/artwork-conversion-notes.md`, §11 and §16), kept for when the diagrams
themselves are next revised. Figure numbers are as in that review.

- **D1. Billing with Debit Note: the supplier's guards** (decided: to be fixed in UBL 2.6; to
  confirm: the new guard). The supplier's Reconcile Charges sends [initial charges or under
  charged] to *Raise Invoice* and [under charged] to *Raise Debit Note*: the two guards
  overlap, so "under charged" does not say which way to go (on the credit-note twin the
  second branch is [over charged]). The fault is new in 2.5: UBL 2.0 to 2.4 draw a different
  process, the Customer raising the Debit Note when [over charged] (os-UBL-2.4
  `art/UBL-2.0-BillingwithDebitNoteProcess.png`, the same drawing since 2.1, and in 2.0 as a
  JPEG), with the Supplier's diamond sending only [initial charges or under charged] to
  *Raise Invoice*. The 2.5 figure moves the Debit Note to the Supplier (the text after it now
  says the Supplier specifies the tax requirements) and was redrawn from the credit-note
  figure, keeping that guard; most likely the invoice branch should read [initial charges].
  The figure is published unchanged in the OASIS Standard (os-UBL-2.5, 12 August 2026, the
  same guards; the file there is a different export of the same drawing). The TC
  (2026-09-28): to be fixed in UBL 2.6. (Approved Errata, TC Process
  2.9, are limited to corrections that are not a Material Change, which a changed guard in a
  process diagram arguably is.)
- **D2. Update Catalogue Pricing, Create Catalogue, Update Catalogue Item Specification:** on
  all three a document runs straight into an end with no step that receives it, and the
  preparing step has two ways in (a start or a loop, and the fork) where "either" is meant -
  in UML two ways into a step mean "both"; a merge diamond would say it.
- **D3. Certification of Origin:** *Receive Response* has two ways out with no decision; the
  accepted outcomes (*Endorse CoO*) never reach the Exporter.
- **D4. Fig 37, Punch-out Sourcing** (`q7`, raised 2026-09-27):
  - *Who builds the basket?* The artwork puts *Build shopping basket* in the Seller Supplier
    Party's column. But in punch-out it is the Originator who browses the catalogue and
    fills the basket, on the Seller's system. UBL.xml says so itself: "The Originators leave
    ... their system and interact with the Seller's catalogue to locate and order products".
    The column may be showing whose system it is rather than who acts. A revised diagram
    could say this plainly, for instance with the action in the Originator's column and the
    Seller's catalogue application named as where it happens.
  - *UBL.xml's text reads "Seller" where "Originator" seems meant.* It says punch-out lets an
    Originator access a Seller's catalogue application "from within the Seller's own
    procurement application", which by the rest of the paragraph should be the Originator's
    own. Whose procurement application "transparently gathers pertinent information" is
    unclear for the same reason.
- **D5. Fig 14, CPFR Exception Monitor** (`q9`): redraw the connector from the Buyer's *Send
  Exception* to *Exception Notification (positive)* like its mirror on the Seller's side. A
  layout matter, for the session that re-lays diagrams.
- **D6. Goods Item Passport figures** (found 2026-09-27): the artwork writes the name both "GoodsItem" and
  "Goodsitem". The model follows the artwork in each place; a revision could make them all
  "GoodsItem".
- **D7. Utility Billing** (`q12`): drop "(from Business Processes)" in a redraw: the package
  means nothing to a reader of the specification; if the link matters, refer to the billing
  section instead.
- **D8. Documents across an intermediate lane** (`q14`): the artwork puts such a box next to
  the receiver 5 times and next to the sender 4 times. A redraw could agree a convention -
  simplest, always on the divider next to the receiver.
- **D9. Freight Status Reporting** (`q15`): "Receiver Party" is a questionable name for a
  party that both receives a request and sends the status report; and the divider marking
  off the self-initiated start could go - in BPMN it would be a timer start inside the
  Receiver Party's lane.
- **D10. Waste Movement and Waste Notification** (`q15`): the column titles read
  "Senderparty" and "ReceiverParty"; UBL.xml says "Sender Party" and "Receiver Party".
- **D11. CPFR phase boxes:** size each to its steps and the words that belong to it, with the
  same margin on every figure (Fig 9 is far too wide; Fig 7's "Retail Event Accepted ?"
  pokes out of its box).
- **D12. Decisions** (completeness sweep): guard every branch and give every diamond its question. Fig C.1,
  Certification of Origin and Fulfilment Despatch Advice can take their guards from the step
  each branch leads to; Create Catalogue's diamond can say "Respond to Request" as its Update
  Catalogue siblings do; the 2.5 billing figures' unlabelled branch out of *Reconcile
  Charges* can read [otherwise] or [dispute charges].
- **D13. Intermodal Freight Management:** split *Provide Transportation Network Information*
  into one step per phase (Planning, Execution).
- **D14. Party names:** one style across the figures, and one name per role (Buyer / Buyer
  Party / Originator Customer Party ...), checked against the party roles UBL.xml gives for
  each document.
- **D15. Self Billing** (text sweep): the choice after *Raise Self Billed Invoice* - accepted, or a reply
  comes - drawn as a branch, in BPMN an event-based gateway: an Application Response, a
  Credit Note, or no reply meaning the charges are accepted.
- **D16. Tender Contract Information Preparation** (text sweep): "Publish Official Journal" would read
  "Publish in Official Journal"; and the box says *Prior Information Notice* where both
  steps call it a *Simplified Notice*.
- **D17. Ends and starts** (actions sweep): an end after each of the 19 steps a path stops at, and a start
  before the 4 it begins at. On Fulfilment Despatch Advice a goods flow from *Despatch Order
  Item(s)* to *Receive Order Item(s)* (as in the notes' §11.6), and on Fig C.1 one into
  *receive goods*; on Utility Billing connect *Report usage*, for instance alongside *Raise
  Invoice*.
- **D18. Fulfilment with Despatch Advice:** the Despatch Party lane has a start event labelled
  "From Order", the Delivery Party lane has none. The TC: this diagram needs proper cleaning
  up (notes §11.4).
- **D19. Tender Award Notification** (documents sweep): draw the two notifications as two exchanges, or with a
  decision (won / not won), rather than two boxes on one line (the TC: a decision diamond,
  and arguably an extra lane for the awarded/unawarded split; notes §11.4).
- **D20. Tender Contract Pre and Post:** *Prior exchange of public keys* appears in both lanes,
  joined by a dashed line with an arrowhead at each end: a mutual precondition, not a flow.
  It needs additional work in the BPMN conversion (notes §11.4).
- **D21. CPFR two-way documents** (documents sweep): draw one box per direction, or say plainly that either
  party may send it to the other.
- **D22. Document names** (documents sweep): use UBL's document type names as they are ("Import Customs
  Declaration", "Proof Of Reexportation Request", "Digital Capability", "Trade Item Location
  Profile"), one spelling of "GoodsItem"; and on Initiate Freight Management "Send Bill of
  Lading to Consignor" and "Send Waybill to Consignor" send to the Consignee as well.
- **D23. Export Customs Declaration** (documents sweep): the stamped declaration is returned from the Customs
  Party to the Exporter; UBL lists the document as sent by the Exporter only. Either the
  roles in UBL.xml grow a second direction, or the return is drawn as a different document.
- **D24. Tender Guarantee Deposit** (`q8`): obtaining the guarantee from a financial
  institution is shown as one step with no document. Should UBL ever cover that exchange,
  the financial institution would become a party with its own column.

## Open work

- **The TC's answers** ("Questions for the TC"): questions A1-A5 before the commit to
  the UBL repository, the rest after it.
- **The commit to the UBL repository**, once A1-A5 are answered: `to-ubl-repo/` copied
  over a clone of the branch chosen (A1), the 3 older sources removed and the 5 more files
  if the TC so decides (A2), and its README's "Artwork" changed with it (A3). Its message
  names each file removed and what it was, and says that Group A's three drawings change
  only in form, that Ordering's bpmn-js SVG is replaced by its draw.io drawing and that
  drawing's export, and that the PNGs are replaced by print PNGs in black and white (grey:
  the illustrations, Business Information and three of Group C) ("Images made from the
  drawings"; `history/remaining-figures.md`, "Before the UBL repository gets any of it").
  A test build through Réalta is done on the UBL repository's side.
- **Official BPMN 2.0 files for the BPMN figures** (Ordering, Business Information): the
  UBL editor, Kees Duvekot, requires them as the sources of BPMN diagrams; what is needed
  is in `history/group-a/README.md` ("Future session"), the decisions it takes are C1-C3.
- **The BPMN 2.0 XML of the Ordering Process** (`UBL-2.3-OrderingProcess.bpmn`, attached to
  the `ubl` list's mail of 2019-05-07, UBL-171): not found yet (not by the UBL editor either,
  2026-10-05). Still to look in: the Sent folder of that mail, other list members' mailboxes
  (Ken Holman, Kenneth Bengtsson), the 2019 download folders and backups, bpmn.io's local
  storage in a browser profile of 2019, and the list archive, which refuses a script (C4).
  Until then Ordering's source is its draw.io BPMN drawing, made from the bpmn-js SVG
  (2026-10-06), every element linked as in a BPMN model ("Ordering, a BPMN drawing"). If the
  `.bpmn` is found, it is held against that drawing; if it stays lost, the BPMN session
  writes it from the drawing as a reconstruction, if the TC agrees (C3;
  `history/group-a/README.md`, "Ordering as a draw.io BPMN diagram").
- **The draw.io desktop app:** this README says to edit in it or in diagrams.net, but
  the drawings are tried in the web editor only (all 96 opened and saved again in the
  live editor, unchanged). Open and save one in the desktop app, and hold the file
  against the drawing with `python3 tools/drawio_format.py --diff` and
  `tools/check_drawio.py`: that shows whether the desktop app writes them the same.
- **Smaller:** the export's report of the size text prints at assumes 12 px text, which
  is wrong for Pre-award and Procurement (`history/group-a/README.md`);
  `history/group-c/lib_c.py` does not allow for draw.io multiplying `dashPattern` by the
  stroke width: fix it before a fifth figure is drawn with it (`history/group-c/README.md`).
- **The CPFR step figures:** what is still open on them (the shading of the handshake
  people) is in `history/illustrations/cpfr/README.md` ("Open work").
