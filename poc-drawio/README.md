# draw.io proof of concept

**Proper draw.io drawings** (README, open work item 2) for all 78 figures. The
aims:

- a native draw.io model of each figure, structurally complete;
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

## Where it stands

**All 78 figures are drawn completely**, with every kind of element the SVGs
have. Held against their SVGs ([`sweep.md`](sweep.md)):

| | median | worst |
|---|---:|---:|
| the SVG's ink draw.io lacks (red) | 1.6 % | 6.0 % |
| draw.io's ink the SVG lacks (blue) | 3.2 % | 7.8 % |

By red:

- 21 figures are under 1 %;
- 43 are under 2 %;
- 54 are under 3 %.

In 72 of the 78, the largest difference is text or an end state, open
decisions 1 and 2 below. The worst figures are the small ones drawn large
(Tender, Manifest, Waste Notification: letters 25-30 px high), where the same
difference in letter width covers more pixels. In the other six it is the
arrowheads on thin lines, and one note and one guard.

Two figures were done first, and are kept in this directory with their renders:

- **UBL-2.5-BillingwithDebitNoteProcess**, chosen for having the most of the
  kinds of element the old output got wrong, in a small figure;
- **UBL-1.0-ProcurementProcess**, Fig C.1, the densest (34 nodes, 43 flows).

| | Billing with Debit Note | Fig C.1, Procurement |
|---|---|---|
| elements of the model present, with their ids | all: 2 lanes, 17 nodes, 20 flows, 7 guards (each on its flow) | all: 3 lanes, 34 nodes, 43 flows |
| SVG ink draw.io lacks (red) | 0.71 % | 0.53 % |
| draw.io ink the SVG lacks (blue) | 2.82 %, of which 742 px are the two end-state discs | 0.34 % |

## How to run

```sh
poc-drawio/sweep.sh <out-dir>              # all 78: about 1.5 minutes, 4 at a time (JOBS)
poc-drawio/run-poc.sh [<figure> ...]       # one or more, into poc-drawio/<figure>/
```

For each figure:

| file | what it is |
|---|---|
| `<figure>.drawio` | the native draw.io model, drawn from the JSONs: the spec from `tools/spec_from_model.py`, plus the diagram JSON for where flows leaving the page continue |
| `-svg.png` | the committed SVG rendered by `tools/render-svg.js` |
| `-drawio.png` | the `.drawio` rendered by draw.io's own drawing code (`render-drawio.js`: `viewer-static.min.js`, draw.io 31.5.3, in the same Chromium) |
| `-overlay.png` | both together: grey where they agree, **red** where the SVG has ink and draw.io none, **blue** where draw.io has ink and the SVG none |
| `-compare.txt` | the same in numbers, per kind of element |

`sweep.sh` writes the same files into `<out-dir>/<figure>/`, which is not
committed, plus the table `sweep.md`, kept here.

Both renders are at the figure's own size and scale 1, so they line up pixel
for pixel. Ink with ink of the other render within 2 px (the pipeline's radius)
counts as agreeing. The draw.io viewer is fetched once from viewer.diagrams.net
into `~/.cache/ubl-drawio-viewer`, and is not committed.

## Element by element: the native construct, and what differs

| element | in draw.io | difference from the SVG, and why |
|---|---|---|
| **page** | the figure's size plus a margin of about one arrowhead all round; the drawing sits that far in. The frame records the offset (`ubl-offset`), and a reader takes it off. | none in the drawing. draw.io grows an edge's bounds by its arrowhead's size on every side, so a flow running off the page with a head on it (CPFR) reached past the page, and draw.io opened the figure among a ring of extra pages. |
| **frame** | draw.io's pool: the "Vertical Pool 1" style of its BPMN palette (a `swimlane` with `childLayout=stackLayout`, which lays its lanes out side by side), at the measured weight, with no title bar of its own (`startSize=0`) and `collapsible=0`. Tested in the editor: widening a lane moves the lanes to its right along and grows the pool, as in a pool drawn by hand. | none |
| **lanes** | the pool's lanes: `swimlane` containers edge to edge from the frame's left to its right, with `collapsible=0` and `expand=0`. An action inside a lane is its child, so moving it between lanes changes its party. Title at the measured size and weight, with its measured centre (`startSize`, `spacingLeft/Right`), and no rule under it (`swimlaneLine=0`), as the artwork has none. Nothing but lanes goes into the pool, which would lay it out as one more lane. | none measurable |
| **lane dividers** | the lanes' own border (draw.io's lane divider), when every divider lies on a lane boundary (within 1.5 px: the two are measured apart), runs frame to frame, has one weight, at least 1 px and no heavier than the frame; the lanes then take the dividers' measured places. Otherwise a line cell of its own, as measured (weight and span), with the lanes' borders hidden; it is a child of the lane to its right, so it moves with that lane. So in 51 figures; the other 27 keep a line of their own: 13 whose dividers are heavier than the frame (a lane's border would also run heavy along the frame), 5 whose dividers differ in weight (two lanes share one border), 6 CPFR figures with a 0.4 px hairline (two lanes draw their shared border twice, which darkens a hairline; 2 of them also stop short of the frame), 2 with a line inside a lane, 1 stopping short. | none |
| **documents on a divider** | a child of the lane to the divider's right, reaching over the divider: drawn after that lane, so the divider runs under it, as in the SVG, and moved with that lane when a lane to its left is widened. (A document passed between two parties belongs to neither party; the model says so, draw.io only needs it to go with the divider.) | none |
| **action** | rounded rectangle, measured weight, `absoluteArcSize` | draw.io's corners are circular; the artwork's are a little elliptical (e.g. rx 21.6, ry 19.0). The mean radius is used. |
| **document (object node)** | rectangle, measured weight, bold italic as measured | text only (below) |
| **decision** | `rhombus`, its question inside or beside it as the artwork has it | text only |
| **note** | draw.io's `note` shape, the fold at its measured size | text only |
| **start** | `startState` from draw.io's UML palette | none. draw.io insets the disc by 4 px, so its box is grown by 4 px and the contact points are recalculated. The disc is exactly the one measured. |
| **end** | `endState` from draw.io's UML palette | **Visible.** draw.io always insets the inner disc by at most 4 px, so the disc is larger and the ring thinner than the artwork's (inner disc 45-61 % of the ring there). Open decision 1. |
| **fork bar** | the fork/join bar of the UML palette, horizontal or upright, at the measured size, filled black | none. The palette fills it with "strokeColor"; inside a lane with no stroke of its own, draw.io resolved that to nothing and the bar vanished (the CPFR figures), so it is filled black outright. |
| **flows** | edges with `source` and `target`. Exit and entry at the measured contact points (`exitX/Y`, `entryX/Y` to 4 places, `exitPerimeter=0`). A straight flow is `edgeStyle=none`; a bent one carries its corners as waypoints. | none on the lines |
| **arrowheads** | draw.io's `open` head; the 2.3 transport figures' filled, notched head is draw.io's `classic`, filled | draw.io's heads are as wide as they are long; the measured heads are longer than they are wide. The SVG draws its barbs 0.8 of the length long and, each side, 0.4 of the width less half a stroke across. draw.io draws them `endSize` + stroke long and half that across. The size that fits both best is taken: `endSize = 0.4·(length + width) − 1.5·stroke`. What remains is at the barbs' ends: the SVG rounds them, draw.io cuts them square. |
| **dashed flows** | `dashed=1`, `dashPattern` in stroke widths, from the measured dash and gap. Never jumped (`noJump=1`). | Same dash and gap. The SVG also starts the pattern where the artwork's first dash begins (`stroke-dashoffset`), which draw.io cannot say, so the dashes can fall in the gaps. |
| **line hops** | draw.io's own line jump, `jumpStyle=arc`, set only on the flows the TC's rule hops. draw.io jumps an edge only over edges drawn before it, so those flows are drawn last. `jumpSize` gives the SVG's radius. | none |
| **guards** | the flow's own label, so it moves with the flow. Placed where the SVG has it: at the nearest point of the line (`x`) plus an `offset`, including where the TC's rule moved it off its line. | White ground (`labelBackgroundColor`) only where the SVG draws one, i.e. where the flow's line runs through the words. Alignment is read from the measurements (flush left where the artwork sets it so). |
| **free texts** | text cells: a decision's question beside its diamond, a remark, a guard the reading took for a title; each a child of the lane it stands in, so it moves with it | text only |
| **flows leaving the page** | an edge attached at one end to its node (so it follows the node), the other end free where the artwork runs it off the page. Its guard is its label. Where it continues is kept as custom properties: `ubl-continues` (the figure), `ubl-counterpart` (the flow there), `ubl-port`, `ubl-direction`. | none. An arrow tip the artwork stops a few pixels short of its node (5.9 px on CPFR Exception Handling) still counts as meeting it, and draw.io runs the line on to the outline. |
| **phase boxes** (CPFR) | a dashed rounded rectangle at the measured dash, gap, corner and weight; the phase's title is its own label, at the measured place. Drawn under the lanes, with `pointerEvents=0`. | none. On top of the lanes it had caught a drag meant for an action inside it, and was dropped into a lane. |
| **bands** (2.3 customs, IMFM) | line cells across the lanes, where and as heavy as measured; on the page, under the pool, so under the actions | none. They run across all lanes, so no lane can carry them: widening a lane in draw.io leaves them, and the phase boxes, as they are. |
| **band titles** (IMFM) | text cells with draw.io's vertical text (`horizontal=0`), reading upwards as the SVG's | text only |
| **grey rules** | a line cell of its own, black at its measured width (the TC: no grey). The artwork's tone is kept as `ubl-artwork-tone`. | none |
| **break marks** (Business Card, Digital Capability) | plain lines, both ends free | none |
| **text (all labels)** | html labels, Helvetica, the measured size (the median of its lines), bold and italic as measured, `whiteSpace=nowrap`: lines break only where the artwork breaks them. The block is placed at the lines' measured left edge or centre, and at their middle. | draw.io cannot fit a line to a measured width, which the SVG does (`textLength`), so letters come out at their natural width, a few pixels longer or shorter at the ends. Over all 1,526 measured lines, draw.io's Helvetica (Liberation Sans in Chromium) is 2.7 % wider than the artwork's (median), between 10 % narrower and 30 % wider. draw.io also sets one size and one line spacing per label (1.2), where the SVG sets each line at its measured place (about 1.25 apart). Open decision 2. |
| **ids and kinds** | each cell is draw.io's `<object>` with the model's id, and the kind as a custom property (`ubl-kind`, shown in draw.io's Edit Data). A flow with a guard also carries the guard's id (`ubl-guard`). | none. The SVG carries the same data in its `data-` attributes. Needed to read a draw.io file back into the JSONs. |

## Editing in draw.io: tested in the editor itself

Figures were opened in the draw.io editor (embed.diagrams.net, 31.5.3, in
Chromium), and elements were moved as a person would move them: by dragging
with the mouse, or by selecting with a click and moving with Shift + the
arrow keys. What draw.io saved was then compared with the file as written.

**Standard elements only.** The files use nothing but draw.io's own shapes:

- rectangles, rounded or not;
- `rhombus`;
- `note`;
- `startState` and `endState`;
- the fork/join bar of the UML palette;
- `swimlane`;
- `line`;
- text;
- plain edges with `open` or `classic` heads, `dashed` lines and `jumpStyle`
  hops.

Style values that equal draw.io's own defaults are left out, as its palettes
leave them out: a vertex's white fill, black line and Helvetica type. The
drawings then also follow draw.io's dark theme on screen; print is black on
white either way.

There are no custom stencils and no embedded images. The model's ids and
kinds are draw.io custom properties (`<object>`, Edit Data).

**Moving an element moves its flows.**

- *Billing:* Raise Debit Note, the fork bar, the Validate Response decision
  and the Debit Note document were dragged.
- *C.1:* the fork bar, DespatchAdvice, add detail and the Buyer decision
  were moved.
- *CPFR Exception Handling:* an action with a flow coming in from the
  previous figure, and a decision with a flow going on to the next one, were
  moved.

In each case every flow kept its `source` and `target` and was redrawn to
the element's new place, and the flows leaving the page kept their free end
at the page's edge. The saved file held the same cells, none added or lost;
only the moved elements' positions differed. A flow keeps meeting the
element at the same point of its outline (`exitX/Y`). A bent flow keeps its
waypoints where they were, as draw.io always does, so its bend may want
tidying after a move.

**Guards move with their flow, but only as a fixed offset.** A guard stays at
the same fraction along its flow, at the same offset from it. When the flow
changes a lot, the guard can land on something else. On Billing, after
Validate Response was moved, `[incorrect information]` lay over *Receive
Account Response*. draw.io does not keep labels clear of other shapes; they
are moved by hand.

**Hops are redrawn where the hopping flow now crosses.** But draw.io hops only
the flows the TC's rule marked when the file was written. A new crossing
between two other solid flows gets no hop until `jumpStyle=arc` is set on one
of them.

**Faults the editor showed, fixed in the writer:**

1. *A document dropped over a lane widened the lane* over its neighbour.
   Lanes now have `expand=0`.
2. *C.1 opened at 25 % among nine pages.* Half a lane border reached past the
   page. Lanes and grey rules now run from frame to frame.
3. *CPFR opened at 55 %.* The flows leaving the page grew the bounds past
   it. The page now has a margin.
4. *A drag meant for an action moved the CPFR phase box.* The box is now
   under the lanes, and clicks inside it go through.

**One thing to know when editing.** C.1's decision diamonds are tiny
(15.6 px, about 12 px on screen at 80 %). Pressing on one grabs a connection
point, and dragging draws a new, unconnected arrow instead of moving the
diamond. Zoom in first, or click the diamond and move it with the arrow keys.
This is how draw.io treats small shapes, not a fault in the file.

## Found by the sweep, fixed in the writer

1. *Free texts* (a decision's question beside its diamond) were not written
   at all: a setting was given twice. 26 figures.
2. *Labels wrapped where the artwork does not.* Placing an off-centre label
   narrows the box draw.io wraps in, and a line that nearly fills its box went
   onto two ("Synchronize stock information", CRP Synchronizing). Labels are
   now `whiteSpace=nowrap`.
3. *Lane borders heavier than the frame showed beside it* (the Tender
   figures). See lane dividers above.
4. *Fork bars vanished* inside lanes with no stroke (the CPFR figures). See
   fork bar above.

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
4. **Where the draw.io files go.** Should they replace `diagrams/<figure>/<figure>.drawio`
   once the decisions above are taken? The writer would then move into
   `tools/` and `draw-from-json.sh --check` would hold them too.

## Not tried yet

- In the editor: reconnecting a flow to another element, resizing an action,
  adding a new action or lane, editing a label. Moving has been tried, and
  widening a lane.
- Reading a draw.io file back into the JSONs, the step toward draw.io as the
  source of truth.
