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

**Natural scale.** The drawing is built at its natural scale: the size at
which the labels of its actions and documents (their median) are 12 px,
draw.io's own font size. That is the scale the artwork was drawn at before it
was scaled up to its 1480-px-wide render. The figures come out 483-1410 px
wide (median 728), with labels about 12 pt and lines 1.3-2 pt, as a drawing
made in draw.io would have them; draw.io's fixed sizes (the end state's 4 px
inset, for one) then fit as they do in its palettes. The writer's tolerances
(1.5 px, 2 px, 8 px, ...) are for a 1480-px figure and scale with it.

The comparison stays at 1480 px: the SVG is rendered at 1480 px wide and the
drawing at 1480 / its width, so they line up pixel for pixel. Text drawn at
about 12 px and scaled up lands 1-3 px from the SVG's (font rounding at the
small size), which the comparison counts; mean red rose from 4.08 % to
4.57 %. The end states improved (Tender Award Notification: blue 870 to 179
px). Ink with ink of the other render within 2 px (the pipeline's radius)
counts as agreeing. The draw.io viewer is fetched once from viewer.diagrams.net
into `~/.cache/ubl-drawio-viewer`, and is not committed.

## Element by element: the native construct, and what differs

| element | in draw.io | difference from the SVG, and why |
|---|---|---|
| **page** | the figure's size plus a margin of about one arrowhead all round; the drawing sits that far in. The frame records the offset (`ubl-offset`), and a reader takes it off. | none in the drawing. draw.io grows an edge's bounds by its arrowhead's size on every side, so a flow running off the page with a head on it (CPFR) reached past the page, and draw.io opened the figure among a ring of extra pages. |
| **frame** | draw.io's pool: the "Vertical Pool 1" style of its BPMN palette (a `swimlane` with `childLayout=stackLayout`, which lays its lanes out side by side), at the measured weight, with no title bar of its own (`startSize=0`) and `collapsible=0`. Tested in the editor: widening a lane moves the lanes to its right along and grows the pool, as in a pool drawn by hand. | none |
| **lanes** | the pool's lanes: `swimlane` containers edge to edge from the frame's left to its right, with `collapsible=0` and `expand=0`. An action inside a lane is its child, so moving it between lanes changes its party. Title at the measured size and weight, with its measured centre (`startSize`, `spacingLeft/Right`), and no rule under it (`swimlaneLine=0`) where the artwork has none. Nothing but lanes goes into the pool, which would lay it out as one more lane. A lane's name is its own label, also where the reading kept it as a loose text (WasteMovement, FreightStatusReporting; bold where the SVG has it). A rule under the lane names across the whole frame (the 2.3 customs figures, IMFM's top rule) is the lanes' own header line (`swimlaneLine=1`), the header as deep as the rule is low. | none measurable |
| **lane dividers** | the lanes' own border (draw.io's lane divider), in all 78 figures: a divider in the artwork on a lane boundary (within 1.5 px: the two are measured apart) is that boundary's border, and so is a grey rule within 3 px of one. Full height, and one weight per figure: the median of its dividers, no heavier than the frame (a lane's outer borders lie on the frame). The artwork's heavier (the Tender figures' 5-9.5 px), hairline (CPFR's 0.4 px), uneven or short dividers are how it was rendered and scaled, not lines of their own. The lanes take the dividers' measured places. Only a line that is not on a lane boundary stays a line cell of its own, a child of the lane it stands in: FreightStatusReporting's rule in the Receiver lane and IMFM's left edge of its first lane. | none |
| **documents on a divider** | a child of the lane to the divider's right, reaching over the divider: drawn after that lane, so the divider runs under it, as in the SVG, and moved with that lane when a lane to its left is widened. (A document passed between two parties belongs to neither party; the model says so, draw.io only needs it to go with the divider.) | none |
| **action** | rounded rectangle, measured weight, `absoluteArcSize` | draw.io's corners are circular; the artwork's are a little elliptical (e.g. rx 21.6, ry 19.0). The mean radius is used. |
| **document (object node)** | rectangle, measured weight, bold italic as measured | text only (below) |
| **decision** | `rhombus`, its question inside or beside it as the artwork has it | text only |
| **note** | draw.io's `note` shape, the fold at its measured size | text only |
| **start** | `startState` from draw.io's UML palette | none. draw.io insets the disc by 4 px, so its box is grown by 4 px and the contact points are recalculated. The disc is exactly the one measured. |
| **end** | `endState` from draw.io's UML palette | Small. draw.io always insets the inner disc by at most 4 px; at the natural scale that is close to the artwork's ring (at 1480 px wide the disc was larger and the ring thinner, inner disc 45-61 % of the ring). |
| **fork bar** | the fork/join bar of the UML palette, horizontal or upright, at the measured size, filled black | none. The palette fills it with "strokeColor"; inside a lane with no stroke of its own, draw.io resolved that to nothing and the bar vanished (the CPFR figures), so it is filled black outright. |
| **flows** | edges with `source` and `target`, filed in the container their two ends share (the lane, or the pool between lanes), as draw.io files a line drawn by hand; waypoints and free ends are relative to it, so moving the pool or a lane takes them along. Exit and entry at the measured contact points (`exitX/Y`, `entryX/Y` to 4 places, `exitPerimeter=0`); on a straight flow, a point within 2 px of one of draw.io's own connection points (a quarter, the middle or three quarters of a box's side, a diamond's tip) is that point (798 of 4180), unless that would tilt a level or upright line. A straight flow is `edgeStyle=none`; a bent one carries its corners as waypoints. | at most 2 px at a snapped contact point |
| **almost-straight flows** | a flow without bends that the artwork draws almost level or upright (off by 0.05-8 px; 631 in 78 figures) is made exactly so by moving its elements, never its contact points: up or down for a level flow, left or right for an upright one. Elements tied by such flows move together; in each group the element with the most of them (mostly a document) stays put. 550 elements move: 165 by less than 0.5 px, 209 by 0.5-2, 150 by 2-4, 26 by 4-7 px. A bend or free end next to a moved element moves with it, so its stretch stays square. No element comes to overlap another or leaves its lane. 8 flows in loops (7 in IMFM, 1 in Fulfilment Receipt Advice) cannot be straightened this way: there the end on the element with the most flows moves by the loop's mismatch (0.6-2.9 px), and that point becomes one of the element's own connection points (`points=` in its style: draw.io's sixteen points of a box plus this one; draw.io shows it and snaps to it). | **by design:** the moved elements are up to 7 px from the SVG, which the comparison (radius 2 px) counts as difference; mean red rose from 2.13 % to 4.08 % |
| **arrowheads** | draw.io's `open` head; the 2.3 transport figures' filled, notched head is draw.io's `classic`, filled | draw.io's heads are as wide as they are long; the measured heads are longer than they are wide. The SVG draws its barbs 0.8 of the length long and, each side, 0.4 of the width less half a stroke across. draw.io draws them `endSize` + stroke long and half that across. The size that fits both best is taken: `endSize = 0.4·(length + width) − 1.5·stroke`. What remains is at the barbs' ends: the SVG rounds them, draw.io cuts them square. |
| **dashed flows** | `dashed=1`, `dashPattern` in stroke widths, from the measured dash and gap. Never jumped (`noJump=1`). | Same dash and gap. The SVG also starts the pattern where the artwork's first dash begins (`stroke-dashoffset`), which draw.io cannot say, so the dashes can fall in the gaps. |
| **line hops** | draw.io's own line jump, `jumpStyle=arc`, set only on the flows the TC's rule hops. draw.io jumps an edge only over edges drawn before it, so those flows are drawn last. `jumpSize` gives the SVG's radius. | none |
| **guards** | the flow's own label, so it moves with the flow. Placed where the SVG has it: at the nearest point of the line (`x`) plus an `offset`, including where the TC's rule moved it off its line. | White ground (`labelBackgroundColor`) only where the SVG draws one, i.e. where the flow's line runs through the words. Alignment is read from the measurements (flush left where the artwork sets it so). |
| **free texts** | a text beside a decision, a start or an end (the decision's question, "From Order", "End of CoO Process") is that node's own label, placed beside it where the SVG has it, so it moves with the node: the nearest such node within 60 px, one text per node (40 texts in 24 figures). draw.io sets a left- or right-aligned label on a start or end state in by the disc's inset, which is allowed for. Only UtilityBilling's two "(from Business Processes)" remain text cells, children of their lane. | text only |
| **flows leaving the page** | an edge attached at one end to its node (so it follows the node), the other end free where the artwork runs it off the page. Its guard is its label. Where it continues is kept as custom properties: `ubl-continues` (the figure), `ubl-counterpart` (the flow there), `ubl-port`, `ubl-direction`. | none. An arrow tip the artwork stops a few pixels short of its node (5.9 px on CPFR Exception Handling) still counts as meeting it, and draw.io runs the line on to the outline. |
| **phase boxes** (CPFR) | a dashed rounded rectangle at the measured dash, gap, corner and weight; the phase's title is its own label, at the measured place and weight, also where the reading kept it as a loose text (CPFR Establishing Collaborative Relationships, Exception Monitor; that text also had the box's id, which made the file invalid). Drawn under the lanes, with `pointerEvents=0`. | none. On top of the lanes it had caught a drag meant for an action inside it, and was dropped into a lane. |
| **bands** (2.3 customs, IMFM) | IMFM's two phase rules: line cells across the lanes (the rule under the lane names is the lanes' header line, see lanes), where and as heavy as measured; on the page, under the pool, so under the actions | none. They run across all lanes, so no lane can carry them: widening a lane in draw.io leaves them, and the phase boxes, as they are. |
| **band titles** (IMFM) | text cells with draw.io's vertical text (`horizontal=0`), reading upwards as the SVG's | text only |
| **grey rules** | on a lane boundary: that boundary's lane border (see lane dividers). Otherwise a line cell of its own, black at its measured width (the TC: no grey). The artwork's tone is kept as `ubl-artwork-tone`. | none |
| **break marks** (Business Card, Digital Capability) | the `//` across the document's flow: two short lines, each a child of that flow (as a label is), a fraction along it, so they go where the flow goes. The flow itself runs from the document down the lane divider to the action, attached at both ends (the reading had found only its last stretch, as a loose line). | none |
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
   figures). Lane borders are now capped at the frame's weight; see lane
   dividers above.
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
