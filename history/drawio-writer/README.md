# The draw.io writer: from the JSONs to draw.io

This writer drew the **78 draw.io drawings in `diagrams/`**, the figures'
source of truth since 2026-09-29 (see the [README](../../README.md) at the top of
the repository). From then on the drawings are edited directly in draw.io and
nothing is drawn over them; the writer is kept here, with the other steps of the
path, to show how each drawing was made and why each element is drawn the way it
is.

It drew each figure from its JSONs (in `history/diagrams/`), with these aims:

- a native draw.io drawing, structurally complete, holding the figure's whole
  model;
- as close to the figure's SVG as draw.io allows;
- every remaining difference explained.

The settings of the work (2026-09-28/29):

- **Notation:** UML, in the dialect the SVGs use. BPMN is not a target.
- **draw.io:** its native constructs (the UML palette's shapes, a BPMN pool with
  lanes), at the figures' natural scale, in whole pixels, with fixed line weights.
- **The model:** every element carries the model's id and kind, and the rest of
  the model as custom properties, so that the drawing can be the source of truth.
  `tools/check_drawio.py --against history/diagrams` read all 78 back equal to
  their diagram JSON when the switch was made.

## Where it stood at the switch

**All 78 figures are drawn completely**, with every kind of element the SVGs
have. Held against their SVGs ([`sweep.md`](sweep.md)):

| | median | mean | worst |
|---|---:|---:|---:|
| the SVG's ink draw.io lacks (red) | 5.0 % | 5.8 % | 15.5 % (Tender Invitation) |
| draw.io's ink the SVG lacks (blue) | 5.7 % | | 15.1 % |

By red: 9 figures are under 2 %, 28 under 4 %, 50 under 6 %, 59 under 8 %.
In 47 of the 78 the largest difference is in the actions, in 14 in the lines,
in the rest documents, lane titles, guards and a note. Most of it is by design:

- **fixed line weights** (1, and 2 for documents and the frame) where the SVG has
  the measured ones - the Tender figures, drawn with heavy lines, differ most;
- **straightened flows:** elements moved up to 7 px to make flows that the
  artwork draws almost level or upright exactly so;
- **text width:** the SVG fits each line to its measured width, draw.io cannot
  (open decision 1).

Against the original PNGs, at each PNG's own size, the drawings differ by 4.1 %
of the PNG's ink on average (red; blue 3.9 %), worst 11.2 % (IMFM). Part of that
is the artwork's own faults, which the drawings do not copy: a divider drawn in
two pieces that do not line up (Transfer of Base Item Catalogue), or leaning
(Initial Stocking by Retailer).

Two figures were done first, and are kept in this directory with their renders:

- **UBL-2.5-BillingwithDebitNoteProcess**, chosen for having the most of the
  kinds of element the old output got wrong, in a small figure;
- **UBL-1.0-ProcurementProcess**, Fig C.1, the densest (34 nodes, 43 flows).

| | Billing with Debit Note | Fig C.1, Procurement |
|---|---|---|
| elements of the model present, with their ids | all: 2 lanes, 17 nodes, 20 flows, 7 guards (each on its flow) | all: 3 lanes, 34 nodes, 43 flows |
| SVG ink draw.io lacks (red) | 8.1 % | 5.9 % |
| draw.io ink the SVG lacks (blue) | 6.6 % | 0.7 % |

## How to run

From the top of the repository:

```sh
history/drawio-writer/sweep.sh <out-dir>          # all 78: a few minutes, 4 at a time (JOBS)
history/drawio-writer/run.sh [<figure> ...]       # one or more, into history/drawio-writer/<figure>/
```

To draw a figure's drawing again from its JSONs - which would overwrite any
edit made to it since, so only for a figure whose drawing is lost:

```sh
python3 history/tools/spec_from_model.py history/diagrams/<f>/<f>-diagram.json /tmp/<f>-spec.json <natural width>
python3 history/drawio-writer/drawio_from_spec.py /tmp/<f>-spec.json diagrams/<f>/<f>.drawio history/diagrams/<f>/<f>-diagram.json
```

(`run.sh` shows how the natural width is found.)

For each figure, `run.sh` and `sweep.sh` write:

| file | what it is |
|---|---|
| `<figure>.drawio` | the drawing, drawn from the JSONs: the spec from `tools/spec_from_model.py`, plus the diagram JSON for the rest of the model |
| `-svg.png` | the figure's SVG (`history/diagrams/`) rendered by `tools/render-svg.js` |
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

**Whole numbers and fixed weights.** As in a drawing made in draw.io, every
value is whole: each element's edges lie on whole pixels (rounded where they
lie on the page, so the lanes still tile the pool edge to edge), and so do
bends and free ends; font sizes are whole points; arrowheads, corner radii,
header depths and label offsets whole pixels. A flow that was level or
upright stays so: where rounding put its ends a pixel apart, the end that is
not on one of draw.io's connection points of its side moves to the other's
level, and a bent flow's end meets its bend's whole pixel. Line weights are
fixed, not measured: draw.io's own 1 (left out of the style) for every line,
2 for a document and the frame (`WEIGHT` in the writer). The Tender figures,
drawn with heavy lines, change most; mean red rose from 4.57 % to 5.82 %.

The comparison stays at 1480 px: the SVG is rendered at 1480 px wide, and the
drawing onto exactly that render's canvas (its width and height, as
`tools/render-svg.js` rounds them), at the SVG's width / its own, so they are
the same size and line up: the frame lines within 1.5 px in every figure
(whole natural pixels, scaled up). Text drawn at
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
| **frame** | draw.io's pool: the "Vertical Pool 1" style of its BPMN palette (a `swimlane` with `childLayout=stackLayout`, which lays its lanes out side by side), at weight 2, with no title bar of its own (`startSize=0`) and `collapsible=0`. Tested in the editor: widening a lane moves the lanes to its right along and grows the pool, as in a pool drawn by hand. | none |
| **lanes** | the pool's lanes: `swimlane` containers edge to edge from the frame's left to its right, with `collapsible=0` and `expand=0`. An action inside a lane is its child, so moving it between lanes changes its party. Title at the measured size and weight, with its measured centre (`startSize`, `spacingLeft/Right`), and no rule under it (`swimlaneLine=0`) where the artwork has none. Nothing but lanes goes into the pool, which would lay it out as one more lane. A lane's name is its own label, also where the reading kept it as a loose text (WasteMovement, FreightStatusReporting; bold where the SVG has it). A rule under the lane names across the whole frame (the 2.3 customs figures, IMFM's top rule) is the lanes' own header line (`swimlaneLine=1`), the header as deep as the rule is low. | none measurable |
| **lane dividers** | the lanes' own border (draw.io's lane divider), in all 78 figures: a divider in the artwork on a lane boundary (within 1.5 px: the two are measured apart) is that boundary's border, and so is a grey rule within 3 px of one. Full height, and one weight per figure: the median of its dividers, no heavier than the frame (a lane's outer borders lie on the frame). The artwork's heavier (the Tender figures' 5-9.5 px), hairline (CPFR's 0.4 px), uneven or short dividers are how it was rendered and scaled, not lines of their own. The lanes take the dividers' measured places. Only a line that is not on a lane boundary stays a line cell of its own, a child of the lane it stands in: FreightStatusReporting's rule in the Receiver lane and IMFM's left edge of its first lane. | none |
| **documents on a divider** | a child of the lane to the divider's right, reaching over the divider: drawn after that lane, so the divider runs under it, as in the SVG, and moved with that lane when a lane to its left is widened. (A document passed between two parties belongs to neither party; the model says so, draw.io only needs it to go with the divider.) | none |
| **action** | rounded rectangle, weight 1, `absoluteArcSize` | draw.io's corners are circular; the artwork's are a little elliptical (e.g. rx 21.6, ry 19.0). The mean radius is used. |
| **document (object node)** | rectangle, weight 2, bold italic as measured | text only (below) |
| **decision** | `rhombus`, its question inside or beside it as the artwork has it | text only |
| **note** | draw.io's `note` shape, the fold at its measured size | text only |
| **start** | `startState` from draw.io's UML palette | none. draw.io insets the disc by 4 px, so its box is grown by 4 px and the contact points are recalculated. The disc is exactly the one measured. |
| **end** | `endState` from draw.io's UML palette | Small. draw.io always insets the inner disc by at most 4 px; at the natural scale that is close to the artwork's ring (at 1480 px wide the disc was larger and the ring thinner, inner disc 45-61 % of the ring). |
| **fork bar** | the fork/join bar of the UML palette, horizontal or upright, at the measured size, filled black. Its own connection points (`points=`) are where its flows meet it: the palette gives it none (`points=[]`), so a flow could not be reattached to it in draw.io (21 bars) | none. The palette fills it with "strokeColor"; inside a lane with no stroke of its own, draw.io resolved that to nothing and the bar vanished (the CPFR figures), so it is filled black outright. |
| **flows** | edges with `source` and `target`, filed in the container their two ends share (the lane, or the pool between lanes), as draw.io files a line drawn by hand; waypoints and free ends are relative to it, so moving the pool or a lane takes them along. Exit and entry at the measured contact points (`exitX/Y`, `entryX/Y`, `exitPerimeter=0`); on a straight flow, a point within 2 px of one of draw.io's own connection points (a quarter, the middle or three quarters of a box's side, a diamond's tip) is that point (798 of 4180), unless that would tilt a level or upright line. A straight flow is `edgeStyle=none`; a bent one carries its corners as waypoints. | at most 2 px at a snapped contact point |
| **almost-straight flows** | a flow without bends that the artwork draws almost level or upright (off by 0.05-8 px; 631 in 78 figures) is made exactly so by moving its elements, never its contact points: up or down for a level flow, left or right for an upright one. Elements tied by such flows move together; in each group the element with the most of them (mostly a document) stays put. 550 elements move: 165 by less than 0.5 px, 209 by 0.5-2, 150 by 2-4, 26 by 4-7 px. A bend or free end next to a moved element moves with it, so its stretch stays square. No element comes to overlap another or leaves its lane. 8 flows in loops (7 in IMFM, 1 in Fulfilment Receipt Advice) cannot be straightened this way: there the end on the element with the most flows moves by the loop's mismatch (0.6-2.9 px), and that point becomes one of the element's own connection points (`points=` in its style: draw.io's sixteen points of a box plus this one; draw.io shows it and snaps to it). | **by design:** the moved elements are up to 7 px from the SVG, which the comparison (radius 2 px) counts as difference; mean red rose from 2.13 % to 4.08 % |
| **arrowheads** | draw.io's `open` head; the 2.3 transport figures' filled, notched head is draw.io's `classic`, filled | draw.io's heads are as wide as they are long; the measured heads are longer than they are wide. The SVG draws its barbs 0.8 of the length long and, each side, 0.4 of the width less half a stroke across. draw.io draws them `endSize` + stroke long and half that across. The size that fits both best is taken: `endSize = 0.4·(length + width) − 1.5·stroke`. What remains is at the barbs' ends: the SVG rounds them, draw.io cuts them square. |
| **dashed flows** | `dashed=1`, `dashPattern` in stroke widths, from the measured dash and gap. Never jumped (`noJump=1`). | Same dash and gap. The SVG also starts the pattern where the artwork's first dash begins (`stroke-dashoffset`), which draw.io cannot say, so the dashes can fall in the gaps. |
| **line hops** | draw.io's own line jump, `jumpStyle=arc`, set only on the flows the TC's rule hops. draw.io jumps an edge only over edges drawn before it, so those flows are drawn last. `jumpSize` gives the SVG's radius. | none |
| **guards** | the flow's own label, so it moves with the flow. Placed where the SVG has it: at the nearest point of the line (`x`) plus an `offset`, including where the TC's rule moved it off its line. | White ground (`labelBackgroundColor`) only where the SVG draws one, i.e. where the flow's line runs through the words. Alignment is read from the measurements (flush left where the artwork sets it so). |
| **free texts** | a text beside a decision, a start or an end (the decision's question, "From Order", "End of CoO Process") is that node's own label, placed beside it where the SVG has it, so it moves with the node: the nearest such node within 60 px, one text per node (40 texts in 24 figures). draw.io sets a left- or right-aligned label on a start or end state in by the disc's inset, which is allowed for. Only UtilityBilling's two "(from Business Processes)" remain text cells, children of their lane. | text only |
| **flows leaving the page** | an edge attached at one end to its node (so it follows the node), the other end free where the artwork runs it off the page. Its guard is its label. Where it continues is kept as custom properties: `ubl-continues` (the figure), `ubl-counterpart` (the flow there), `ubl-port`, `ubl-direction`. | none. An arrow tip the artwork stops a few pixels short of its node (5.9 px on CPFR Exception Handling) still counts as meeting it, and draw.io runs the line on to the outline. |
| **phase boxes** (CPFR) | a dashed rounded rectangle at the measured dash, gap, corner and weight; the phase's title is its own label, at the measured place and weight, also where the reading kept it as a loose text (CPFR Establishing Collaborative Relationships, Exception Monitor; that text also had the box's id, which made the file invalid). A child of the pool, under the lanes, with `pointerEvents=0` and `movable=0` (so the pool's stack layout leaves it alone): moving the pool takes it along. | none. On top of the lanes it had caught a drag meant for an action inside it, and was dropped into a lane. |
| **bands** (2.3 customs, IMFM) | IMFM's two phase rules: line cells across the lanes (the rule under the lane names is the lanes' header line, see lanes), where measured, at weight 1; children of the pool, under the lanes, so under the actions, with `movable=0` (see phase boxes): moving the pool takes them along | none. They run across all lanes, so no lane can carry them: widening a lane in draw.io leaves their width, and the phase boxes', as it is. |
| **band titles** (IMFM) | text cells with draw.io's vertical text (`horizontal=0`), reading upwards as the SVG's; children of the pool, as the bands | text only |
| **grey rules** | on a lane boundary: that boundary's lane border (see lane dividers); all of them are. (Otherwise a line cell of its own, black (the TC: no grey), with the artwork's tone kept as `ubl-artwork-tone`.) | none |
| **break marks** (Business Card, Digital Capability) | the `//` across the document's flow: two short lines, each a child of that flow (as a label is), a fraction along it, so they go where the flow goes. The flow itself runs from the document down the lane divider to the action, attached at both ends (the reading had found only its last stretch, as a loose line). | none |
| **text (all labels)** | html labels, Helvetica, the measured size (the median of its lines) in whole points, bold and italic as measured, `whiteSpace=nowrap`: lines break only where the artwork breaks them. The block is placed at the lines' measured left edge or centre, and at their middle. | draw.io cannot fit a line to a measured width, which the SVG does (`textLength`), so letters come out at their natural width, a few pixels longer or shorter at the ends. Over all 1,526 measured lines, draw.io's Helvetica (Liberation Sans in Chromium) is 2.7 % wider than the artwork's (median), between 10 % narrower and 30 % wider. draw.io also sets one size and one line spacing per label (1.2), where the SVG sets each line at its measured place (about 1.25 apart). Open decision 1. |
| **ids, kinds and the model** | each cell is draw.io's `<object>` with the model's id, and the kind as a custom property (`ubl-kind`, shown in draw.io's Edit Data). Everything else the diagram JSON says that the drawing does not show by itself is kept on the element as `ubl-` properties (`carry_model`; the list is in the top README): a flow's kind and guard, a document between parties, linked processes, references, phase members, a text's own words, the flows one drawn line stands for. Not kept: how the PNG was read (a flow's direction confidence, the source PNG). | none. `tools/check_drawio.py --against history/diagrams` reads the model back out of the drawing: all 78 equal to their JSON. |

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

## Decisions taken

- **The end state:** draw.io's own UML `endState` (decided 2026-09-29: "end
  nodes are OK"). At the natural scale its fixed 4 px inset is close to the
  artwork's ring.
- **Where the drawings go:** `diagrams/<figure>/<figure>.drawio`, as the
  figures' source of truth, replacing the old incomplete draw.io files (which
  stay in `history/diagrams/`). The writer stays here, in the history.
- **Embedding in the SVG:** not taken up here. Images made from the drawings
  (SVG, PNG, PDF) are the work of a later session.

## Open decisions

1. **Text width.** Keep the measured size, with letters at their natural
   width (as now)? Or choose each label's size so its width matches? That
   would be closer to the SVG, but the sizes would no longer be the ones
   measured.

## Tried in the editor since

- Moving the pool: flows, their bends and free ends, the phase boxes and IMFM's
  phase rules and names all move with it.
- Widening a lane: the pool grows and the lanes stay edge to edge; the phase
  parts are not taken for lanes.
- A decision's question moves with its diamond; the break marks with their flow.
- Opening, editing and saving a drawing keeps its whole model (the check above).

## Not tried yet

- In the editor: reconnecting a flow to another element, resizing an action,
  adding a new action or lane, editing a label.
