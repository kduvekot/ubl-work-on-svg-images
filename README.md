# ubl-work-on-svg-images

Editable sources for the artwork of the UBL specification: the **78 UML activity
diagrams** of UBL 2.5 (of its 97 figures), as **draw.io drawings**. UBL publishes
these diagrams as PNG and most of their original sources are lost; these drawings
replace them as the figures' source.

## The source of truth: the draw.io drawings

```
diagrams/<figure>/<figure>.drawio        78 figures, e.g. diagrams/UBL-2.5-BillingwithDebitNoteProcess/
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
- drawn at the figures' **natural scale** (labels about 12 pt), with **whole
  pixels** only and **fixed line weights** (1, and 2 for documents and the frame);
  flows that the artwork draws almost level or upright are exactly so.

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

### Checking a drawing

```sh
python3 tools/check_drawio.py diagrams/*/*.drawio
```

checks the conventions a drawing must keep after an edit: every element has a
known `ubl-kind` and a unique id; the lanes are in the pool and every node in a
lane; every flow is attached at both ends (a flow leaving the page at one); a
guard is used once. When you add an element in draw.io, give it an id and a
`ubl-kind` (Edit Data).

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
5. **JSON to draw.io** - `history/poc-drawio/`: the writer that drew the drawings
   in `diagrams/` from the JSONs, with its README (every element, the draw.io
   construct chosen for it, and what differs from the SVG) and its comparison
   against the SVGs (`sweep.md`).
6. **draw.io as the source** - `diagrams/` (2026-09-29).

`history/README.md` is the repository's former README, describing steps 1-4.
