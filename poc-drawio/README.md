# draw.io proof of concept

A first try at **proper draw.io drawings** (README, open work item 2). The aims:

- a native draw.io model of a figure, structurally complete;
- as close to the figure's SVG as draw.io allows;
- every remaining difference explained.

It is kept apart from the pipeline. Nothing in `diagrams/`, `tools/` or
`baselines/` is changed or written. The committed SVGs, and the JSON → SVG
drawing, stay exactly as they are. `tools/draw-from-json.sh --check diagrams`
still passes for all 78.

The settings for this work (2026-09-28):

- **Notation:** UML, in the dialect the SVGs use now. BPMN is not a target for now.
- **Structure:** complete, with the drawing as close to the SVG as possible and
  every difference explained.
- **draw.io:** its native constructs, again as close to the SVG as possible,
  with every difference explained.
- **Source of truth:** the JSONs, with the SVG drawn from them. Whether draw.io
  can become the source of truth is what this work is to find out.

## The figures

Two figures so far:

- **UBL-2.5-BillingwithDebitNoteProcess**, the first proof of concept;
- **UBL-1.0-ProcurementProcess**, Fig C.1, asked for next.

### Billing with Debit Note

It was chosen for having the most of the kinds of element the old draw.io
output got wrong, in a small figure (17 nodes, 20 flows):

- lanes with a measured divider;
- three decisions with their question in the diamond;
- seven guards, one of them moved off its line by the TC's rule;
- the TC's one line hop;
- a horizontal fork bar;
- bold and plain actions side by side.

### Fig C.1, Procurement

It is the densest of the two (34 nodes, 43 flows) and tests what Billing does
not have:

- three lanes;
- 19 dashed object flows, 4 of them with a measured dash offset;
- two hops among 43 diagonal flows;
- two fork bars;
- two grey rules beside the first divider;
- heavier strokes throughout (3 px lines, 4.8 px documents);
- no guards, no start node (the process begins with the Buyer's *place
  order*).

The grey rules were new to the writer; it now draws them.

Not in either figure, and not yet drawn: phase boxes, flows leaving the page,
bands and their titles, break marks, free captions and notes.
`drawio_from_spec.py` says so when a figure has any of them. The next
candidates are CPFR Create Order Forecast (phase box, flows leaving the page),
a 2.3 customs figure (bands) and Business Card (break marks).

## All 78: the sweep

`poc-drawio/sweep.sh <out-dir>` draws every figure and holds each against its
SVG, as `run-poc.sh` does for one. Four at a time, it takes about 1.5
minutes. The table it writes is kept as [`sweep.md`](sweep.md); the per-figure
files stay in `<out-dir>` and are not committed.

At this commit:

- **62 of 78 figures are drawn completely.** Their red (the SVG's ink draw.io
  lacks) has a median of 1.4 % and a maximum of 6.0 %. In every one of them
  the largest difference is text (actions, lane titles, documents) or the end
  state: open decisions 1 and 2 below.
- **16 figures still have kinds of element not drawn:**
  - phase boxes and flows leaving the page: the 7 CPFR figures;
  - bands: the 2.3 customs figures and IMFM Intermodal;
  - break marks: Business Card and Digital Capability;
  - captions.

  Their red has a median of 9 % and a maximum of 15 %.

The first sweep found three faults in the writer, now fixed:

1. *Free texts* (a decision's question beside its diamond) failed to be
   written at all: a setting was given twice. 26 figures.
2. *Labels wrapped where the artwork does not.* Placing an off-centre label
   narrows the box draw.io wraps in, and a line that nearly fills its box
   went onto two ("Synchronize stock information", CRP Synchronizing). Labels
   are now `whiteSpace=nowrap`: they break only at their own line breaks, as
   in the artwork.
3. *Lane borders heavier than the frame showed beside it* (the Tender figures:
   9.5 px dividers in a 4.3 px frame). A lane's border now stands in for the
   divider only when it is no heavier than the frame. Otherwise the divider is
   a line of its own, as measured, and the lanes' borders are hidden.

Bent flows are drawn right: the 25 figures with them include IMFM Basic
Transport Execution Plan, whose loop back to *Create/Update* matches the SVG.
Natural text width is not the cause of the text differences: over all 1,526
measured lines, draw.io's Helvetica (Liberation Sans in Chromium) comes out
only 2.7 % wider than the artwork's (median).

## How to run

```sh
poc-drawio/run-poc.sh                      # Billing with Debit Note
poc-drawio/run-poc.sh <figure> [...]       # any other
```

For each figure the script writes into `poc-drawio/<figure>/`:

| file | what it is |
|---|---|
| `<figure>.drawio` | the native draw.io model, drawn from the JSONs (through `tools/spec_from_model.py`) |
| `-svg.png` | the committed SVG rendered by `tools/render-svg.js` |
| `-drawio.png` | the `.drawio` rendered by draw.io's own drawing code (`render-drawio.js`: `viewer-static.min.js`, draw.io 31.5.3, in the same Chromium) |
| `-overlay.png` | both together: grey where they agree, **red** where the SVG has ink and draw.io none, **blue** where draw.io has ink and the SVG none |
| `-compare.txt` | the same in numbers, per kind of element |

Both renders are at the figure's own size and scale 1, so they line up pixel
for pixel. Ink with ink of the other render within 2 px (the pipeline's radius)
counts as agreeing. The draw.io viewer is fetched once from viewer.diagrams.net
into `~/.cache/ubl-drawio-viewer`, and is not committed.

## The result

| | Billing with Debit Note | Fig C.1, Procurement |
|---|---|---|
| elements of the model present, with their ids | all: 2 lanes, 17 nodes, 20 flows, 7 guards (each on its flow) | all: 3 lanes, 34 nodes, 43 flows |
| SVG ink draw.io lacks (red) | **389 px, 0.72 %** of the SVG's ink | **479 px, 0.50 %** |
| draw.io ink the SVG lacks (blue) | **1,515 px, 2.80 %**, of which 742 are the two end-state discs | **293 px, 0.30 %** |

The old draw.io output (`diagrams/…drawio`) was never measured. Its guards
were edge text without their ids, and it lacked the rest listed in the main
README.

On both figures, draw.io and the SVG agree on:

- every box, diamond and bar;
- every line, the hops and the arrowheads;
- the lane titles, the dividers and the grey rules.

What is left:

- Billing's end states;
- the letters, which draw.io sets at their natural width. On Billing they
  come out a little wider than measured, on C.1 up to 9 % narrower (*despatch
  order item(s)*: 138 px against 151);
- on C.1, where dashed flows cross, the place of the dashes.

## Element by element: the native construct, and what differs

| element | in draw.io | difference from the SVG, and why |
|---|---|---|
| **frame** | a plain rectangle, measured weight (4.3 on Billing, 5.2 on C.1), `connectable=0` | none |
| **lanes** | real `swimlane` containers with `collapsible=0` and `expand=0`, from frame to frame. An action inside a lane is its child, so moving it between lanes changes its party. Title at the measured size and weight (plain on Billing, bold on C.1), with its measured centre (`startSize`, `spacingLeft/Right`). | The shared border is drawn once by each lane. Same place and width, but its anti-aliased edge is a shade darker. |
| **lane divider** | the lanes' own border, when every measured divider runs frame to frame on a lane boundary (it does on both figures). Otherwise it would be a line of its own, with the lanes' borders hidden. | none measurable |
| **documents on the divider** | top-level cells, above both lanes: a document passed between two parties belongs to neither. So the divider runs under the document, as in the SVG. | none. The first try made them children of the left lane, and the right lane's border then ran through them. |
| **action** | rounded rectangle, measured weight, `absoluteArcSize` | draw.io's corners are circular; the artwork's are a little elliptical (e.g. rx 21.6, ry 19.0). The mean radius is used. |
| **document (object node)** | rectangle, measured weight (3.5), bold italic | text only (below) |
| **decision** | `rhombus`, question inside, plain | text only |
| **start** | `startState` from draw.io's UML palette | none. draw.io insets the disc by 4 px, so its box is grown by 4 px and the contact points are recalculated. The disc is exactly the one measured. |
| **end** | `endState` from draw.io's UML palette | **Visible.** draw.io always insets the inner disc by at most 4 px, so the disc is larger and the ring thinner than the artwork's (inner disc 45-61 % of the ring there). 742 px of blue, two fifths of all of it. Open decision 1. |
| **fork bar** | the fork/join bar of draw.io's UML palette (a box filled with its stroke colour), horizontal, at the measured size | none. The old output drew a vertical stub. |
| **flows** | edges with `source` and `target`, straight (`edgeStyle=none`). Exit and entry at the measured contact points (`exitX/Y`, `entryX/Y` to 4 places, `exitPerimeter=0`). | none on the lines |
| **arrowheads** | draw.io's `open` head | draw.io's open head is as wide as it is long; the measured heads are longer than they are wide (Billing 28.1 × 21.9, C.1 23.0 × 20.6). The SVG draws its barbs 0.8 of the length long and, each side, 0.4 of the width less half a stroke across. draw.io draws them `endSize` + stroke long and half that across. The size that fits both best is taken: `endSize = 0.4·(length + width) − 1.5·stroke`. On both figures the heads now lie on the SVG's. The first try, the mean less one stroke, drew them visibly too wide on C.1's 3 px lines. What remains is at the barbs' ends: the SVG rounds them, draw.io cuts them square. |
| **dashed flows** | `dashed=1`, `dashPattern` in stroke widths, from the measured dash and gap. Never jumped (`noJump=1`). | Same dash and gap. The SVG also starts the pattern where the artwork's first dash begins (`stroke-dashoffset`, 4 of C.1's 19 dashed flows), which draw.io cannot say. So the dashes can fall in the gaps: the red and blue dots along *cancel order → OrderCancellation*. |
| **grey rules** | a line cell of its own (`shape=line`), black at its measured width, the full height, as the SVG draws it (the TC: no grey). The artwork's tone is kept as a custom property (`ubl-artwork-tone`). | none |
| **line hop** | draw.io's own line jump, `jumpStyle=arc` | none: same place, radius and bow. It is set only on the flow the TC's rule hops. draw.io jumps an edge only over edges drawn before it, so that flow is drawn last. A dashed flow would get `noJump=1`: it is never hopped. `jumpSize` gives the SVG's radius, half the arrowhead's length. |
| **guards** | the flow's own label, so it moves with the flow. Placed where the SVG has it: at the nearest point of the line (`x`) plus an `offset`. `[incorrect information]` stands where the TC's rule moved it. | White ground (`labelBackgroundColor`) only where the SVG draws one, i.e. where the flow's line runs through the words. Alignment is read from the measurements. These guards are set flush left in the artwork, and so they are here. |
| **text (all labels)** | html labels, Helvetica, the measured size (the median of its lines), bold and italic as measured. The block is placed at the lines' measured left edge or centre, and at their middle. | draw.io cannot fit a line to a measured width, which the SVG does (`textLength`), so letters come out at their natural width. They are within about 1-3 px at the ends. draw.io also sets one size and one line spacing per label (1.2), where the SVG sets each line at its measured place (about 1.25 apart). Together, the red/blue fringes on the letters. |
| **ids and kinds** | each cell is draw.io's `<object>` with the model's id, and the kind as a custom property (`ubl-kind`, shown in draw.io's Edit Data). A flow with a guard also carries the guard's id (`ubl-guard`). | none. The SVG carries the same data in its `data-` attributes. Needed to read a draw.io file back into the JSONs. |

## Editing in draw.io: tested in the editor itself

Both files were opened in the draw.io editor (embed.diagrams.net, 31.5.3, in
Chromium), and elements were moved as a person would move them: by dragging
with the mouse, or by selecting with a click and moving with Shift + the
arrow keys. What draw.io saved was then compared with the file as written.

**Standard elements only.** The files use nothing but draw.io's own shapes:

- rectangles, rounded or not;
- `rhombus`;
- `startState` and `endState`;
- the fork/join bar of the UML palette;
- `swimlane`;
- `line`;
- plain edges with `open` arrowheads, `dashed` lines and `jumpStyle` hops.

There are no custom stencils and no embedded images. The model's ids and
kinds are draw.io custom properties (`<object>`, Edit Data).

**Moving an element moves its flows.**

- *Billing:* Raise Debit Note, the fork bar, the Validate Response decision
  and the Debit Note document were dragged. Every one of the 20 flows kept
  its `source` and `target`, and was redrawn to the element's new place.
- *C.1:* the fork bar, DespatchAdvice, add detail and the Buyer decision
  were moved. Afterwards the file held the same 86 cells, none added or
  lost; only the four moved elements' positions differed.
- No flow has waypoints, so no bend is left behind where the element was.
- A flow keeps meeting the element at the same point of its outline (the
  measured contact point, `exitX/Y`).

**Guards move with their flow, but only as a fixed offset.** A guard is its
flow's own label: it stays at the same fraction along the flow, at the same
offset from it. When the flow changes a lot, the guard can land on something
else. On Billing, after Validate Response was moved, `[incorrect information]`
lay over *Receive Account Response*, and `[no action required]` over the end
node. draw.io does not keep labels clear of other shapes; they are moved by
hand.

**Hops are redrawn where the hopping flow now crosses.** A moved fork bar
took its hop to the new crossing. But draw.io hops only the flows the TC's
rule marked when the file was written. A new crossing between two other solid
flows gets no hop until `jumpStyle=arc` is set on one of them.

**Two problems found and fixed in the writer:**

1. *A document dropped over a lane widened the lane.* On Billing, dragging
   Debit Note (a top-level cell on the divider) made it a child of the left
   lane, and draw.io widened that lane from 783.4 to 844.8, over the right
   lane. Every lane now has `expand=0`: a lane keeps its size whatever is
   dropped across its edge. A document dropped inside a lane still becomes
   that lane's child, which is draw.io's way.
2. *C.1 opened at 25 % among nine pages.* The lanes ran from the page's edge,
   so half their 3.5 px border stuck out past the page, and draw.io added a
   ring of pages round the drawing. The lanes and grey rules now run from
   frame to frame, under the frame's heavier line. Both figures open on one
   page, at 80 %. The renders did not change.

**One thing to know when editing.** C.1's decision diamonds are tiny
(15.6 px, about 12 px on screen at 80 %). Pressing on one grabs a connection
point, and dragging draws a new, unconnected arrow instead of moving the
diamond. Zoom in first, or click the diamond and move it with the arrow keys.
This is how draw.io treats small shapes, not a fault in the file.

## Open decisions

1. **The end state.** Choices:
   - keep draw.io's own UML `endState`: native and recognisable, but the disc
     is larger than the artwork's;
   - an embedded custom shape (a draw.io stencil kept in the file) drawn at
     the measured ring. It matches the SVG, but it is no longer the palette's
     shape.
2. **Text width.** Keep the measured size, with letters at their natural
   width (as now)? Or choose each label's size so its width matches? That
   would be closer to the SVG, but the sizes would no longer be the ones
   measured.
3. **Embedding.** Should the SVG carry this model in its `content` attribute
   in place of the old one, so that opening the SVG in draw.io gives this
   drawing? That changes every SVG's bytes, though not its drawing, against
   `baselines/2026-09-28/`.

## Not tried yet

- The remaining kinds of element, on the candidates named above.
- Orthogonal flows with bends: every flow in both figures is straight. The writer
  passes the routed corners as waypoints, which is untested.
- In the editor: reconnecting a flow to another element, resizing, and
  adding a new action or lane. Only moving has been tried.
- All 78 figures.
