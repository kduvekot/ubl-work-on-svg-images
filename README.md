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

### Not yet: images made from the drawings

SVG, PNG and PDF exports of the drawings are the work of a later session. Until
then, the latest images are the SVGs in `history/diagrams/<figure>/<figure>.svg`,
drawn from the JSONs; they are no longer maintained.

## How we got here: `history/`

The drawings are the end of a path, kept whole in `history/`, which is the
repository as it was before the switch and still runs from there:

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
6. **draw.io as the source** - `diagrams/` (2026-09-29).

`history/README.md` is the repository's former README, describing steps 1-4.
