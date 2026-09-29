# The UBL figures' look: census, house style, and what uniform can mean

For the TC. The 78 activity diagrams are drawn faithful to their artwork, and
the artwork was made over many years, by different hands, in different tools.
The same element does not look the same from figure to figure. This page:

1. measures how far they differ;
2. proposes one house style;
3. shows what "uniform" can mean on paper, with a demonstration PDF:
   [`house-style-demo.pdf`](house-style-demo.pdf).

Nothing here is decided. The committed SVGs and the draw.io drawings that
follow them (`sweep.md`) stay faithful until the TC chooses otherwise.

## 1. The census: how the 78 figures differ

Each figure is measured against its own label size (the median size of its
actions' and documents' lines). That makes the figures comparable however
large each artwork was drawn.

| element | smallest | a quarter below | median | a quarter above | largest |
|---|---:|---:|---:|---:|---:|
| line weight (× label size) | 0.07 | 0.08 | 0.10 | 0.12 | 0.22 |
| document outline | 0.07 | 0.12 | 0.16 | 0.20 | 0.39 |
| lane divider | 0.02 | 0.08 | 0.11 | 0.14 | 0.27 |
| frame | | | 0.18 | | |
| arrowhead length | 0.77 | 1.18 | 1.35 | 1.70 | 2.21 |
| one-line action, height | 2.26 | 2.54 | 2.83 | 3.48 | 5.46 |
| action corner (× its height) | 0.13 | 0.37 | 0.45 | 0.49 | 0.72 |
| document height | 2.52 | 3.76 | 4.83 | 5.16 | 6.56 |
| guard size | 0.74 | 0.92 | 0.98 | 1.00 | 1.17 |
| lane title size | 0.80 | 0.98 | 1.00 | 1.02 | 1.65 |
| start disc, across | 0.89 | 1.54 | 1.83 | 2.01 | 3.24 |
| end, inner disc (× ring) | 0.42 | 0.44 | 0.48 | 0.71 | 0.79 |
| fork bar, thickness | 0.27 | 0.45 | 0.52 | 0.61 | 0.63 |

And the choices that are not sizes:

| | what the figures do |
|---|---|
| action labels | bold in 47 figures, plain in 30, both in 1 |
| document labels | bold in 217 of 228, italic in 208 |
| lane titles | plain in 144 of 170, bold in 26; Title Case 110, CAPITALS 36, other 24 |
| arrowheads | open V in 68 figures, filled and notched in 10 (the 2.3 transport figures) |
| grey rules | two thin extra rules beside one divider, in two figures |

So the same thing is drawn up to 2 to 5 times heavier or larger in one figure
than in another, and titles and labels switch between bold and plain.

## 2. The house style proposed

The median of each measure above, and the majority of each choice. In draw.io
units, with a 12 px label (draw.io's own default):

| element | house style |
|---|---|
| labels | 12 px Helvetica. Actions bold, documents bold italic; decisions, guards and lane titles plain. The words as the figure has them (no change of case). |
| lines | flows and action outlines 1.2 px (0.10); document outlines 1.9 px (0.16); dividers 1.3 px (0.11); frame 2.2 px (0.18) |
| arrowheads | one head everywhere: open, 16 px long (1.35) |
| action | **its measured size**, grown only where its words would not fit (words + 6 px each side, 5 px above and below) |
| action corners | **one radius in every action: 16 px** (1.3 label sizes, the median), at most half the action's height |
| document | its measured size, grown only where its words would not fit (words + 6 px each side, 7 px above and below) |
| document on a divider | **centred exactly on the divider** |
| decision | its measured size, grown only around its question; 24 px across when the question stands beside it |
| start, end | draw.io's UML start and end states, 22 px across |
| fork bar | 6 px thick |
| lane titles | **centred 16 px below the frame's top in every figure**, plain, at the label size, with **no rule under them** |
| bands | a band that divides the figure (IMFM's planning, execution, completion) stays, drawn as a divider |
| grey rules | none: one line per divider |
| phase title (CPFR) | bold, on a white ground where a lane divider runs through it |

**Boxes keep their measured size.** A first version sized every box to its
words. That broke figures that draw their actions large on purpose: IMFM
Intermodal draws its actions as tall columns, 200 by up to 800 px, with many
flows arriving along their sides, and shrunk to their words those flows all
crowded into one small box. What makes the same element look the same is its
corners, outline, type and heads, not its size. So a box now keeps its size,
and only grows where the house type would not fit in it.

It settles two of the open questions of the faithful drawings (README, open
decisions 1 and 2). The end state becomes draw.io's own, and text is set at
its natural width: both are then the standard, not a departure from an
artwork.

Each figure keeps its layout. It is scaled so its labels come out at 12 px,
and every element stays at its measured centre. `house_style.py` does this
from the same JSONs; the draw.io writer draws the result like any other
figure.

**Flows made exactly level or upright.** In the artwork, 432 flows in 71
figures run *almost* level or upright: a few pixels off, so they print very
slightly slanted. Only 437 are exactly so. The house style makes every flow
within 0.75 label sizes of level or upright exactly so, by sliding one end
along the side of its box. After that, 867 flows are exactly level or upright,
2 could not be moved (their box's side is too short), and 99 run at an angle
on purpose.

**Making room.** A box grown to fit the house type can come too close to
another. Its flow may become too short to show its arrowhead, a guard or lane
title may touch it, or it may run out of its lane (the Tender figures' long
actions ran past the frame). Where that happens, the figure is opened up at a
line between the two: widened or lengthened there, with everything beyond
moving along. So rows, columns and lanes stay aligned, and a lane that needs
room grows. The largest need is met first, until nothing is too close or out
of its lane:

- the checks are: at least 1.5 arrowheads plus half a label size of flow
  between two boxes; half a label size between boxes that face each other or
  a box and its lane's edge; a little room around guards and lane titles;
- **all 78 figures end with nothing too close and every box in its lane;**
- after the grid below, 37 need no opening, and the median figure one.

Together with the grid, the figures grow: compared with the figure as
scaled, the median by 5 % in width and 0 % in height; 16 figures grow more
than 20 % wider, the most CertificationOfOriginOfGoods (44 %), and one more
than 20 % taller (Procurement, 22 %).

The demonstration shows two figures before and after (section 5 of the PDF).

### Asked of the house style

- **Are all arrowheads the same?** In the house style, yes: one open head, one
  size, on every flow in every figure. (A flow that runs off the page without
  a head in the artwork stays without one.) In the faithful drawings they are
  not. 68 figures draw an open head and 10 a filled, notched one, from 0.8 to
  2.2 label sizes long and 0.75 to 1.05 as wide as long.
- **Are all documents centred on the lane dividers?** In the faithful drawings
  almost, not exactly. 223 documents sit on a divider; the median is 0.11 label
  sizes off centre, the furthest about one (CPFR Create Joint Business Plan,
  Tender Award Publication, the Catalogue figures). In the house style every
  one is centred exactly. The flows to and from a document keep meeting it
  level: a line into its side keeps its height, and one into its top or bottom
  moves with it.
- **Are the lane headers the same?** Not in the artwork. The title sits from
  0.7 to 2.9 label sizes below the top, and 7 figures (IMFM and six 2.3
  customs figures) draw a rule under the titles that the other 71 do not. The
  house style puts every title at the same place, with no rule.
- **Is the routing of flows consistent?** Not in the artwork. In the house
  style every flow runs across and down: see section 2a.

## 2a. The routing of flows: for the TC to choose

Of the 1,033 flows in the 78 figures:

- 831 are one straight line across or down;
- 138 run at an angle, straight from one element to another;
- 64 bend at right angles.

By figure:

| the figure's flows | figures |
|---|---:|
| only straight across or down | 39 |
| also at an angle | 14 |
| also bent at right angles | 14 |
| all three | 11 |

So half the figures mix routing styles. The families differ: Procurement (Fig
C.1) and the billing figures use angled lines, the CPFR figures right-angled
bends, and most of the Tender, VMI and CRP figures only straight lines.

**Right angles, done properly.** Every flow runs across and down, in three
steps (`house_style.py --avoid`):

1. **Boxes on a grid: rows and columns** (`grid()` in `house_style.py`).
   - *Rows.* Boxes joined by a flow across (from a side to a side) are put
     level with each other: a document, the action that sends it and the
     action that receives it. Procurement's *decision if item(s) rejected* is
     now level with the ReceiptAdvice it receives, and with *advise receipt*
     that sends it. A row is not formed where it would put two boxes that
     overlap across in one row, a box between two boxes joined by a flow, or
     one row both above and below another. A box much taller than the one it
     is joined to (IMFM's actions) is not lined up by its middle: the flow
     meets it level, where along its side the other box is.
   - *Columns.* In each lane, boxes one above the other (joined by a flow
     down, or overlapping across) are stacked in one column: Procurement's
     *reject order*, *change order* and *cancel order* in the Seller's lane.
     A column is not formed where a box would stand between two boxes of it
     joined by a flow, or in the way of an off-page flow leaving one of them.
   - *Even spacing.* The columns of a lane are spaced evenly: the same gap
     between them and at the lane's edges, clear of the documents on its
     dividers. A lane is widened where they do not fit with at least 3 label
     sizes between.
   - *Order kept.* Each row keeps the boxes above and below it in their
     order, at least a flow's length apart (more at a decision, see below);
     the figure grows down where a row needs room. A band's rule is put back
     between its rows; a phase box grows to hold what it held.

   Over all 78: 321 columns and 203 rows of more than one box; 50 figures
   have a lane widened. (`--no-grid` gives the earlier, smaller step: a
   document level with its sender, and boxes lined up where a move of at
   most 1.5 label sizes does it.)
2. **Room made**, as above, and flows straightened once more.
3. **Flows routed by libavoid**, the orthogonal connector router of the
   adaptagrams project (Wybrow, Marriott and Stuckey; the router in Inkscape
   and Dunnart). It is used through its WebAssembly build `libavoid-js`
   (LGPL-2.1), from `avoid_route.mjs`. All flows of a figure are routed
   together. It keeps a margin round every box, charges for bends and
   crossings, and spaces parallel stretches apart. Flows that already run
   straight keep their contact points. A flow that ran at an angle may meet
   a box at the middle, a third or a quarter of any side, and libavoid
   chooses. Diamonds, discs and fork bars are met where the writer decides,
   since libavoid cannot tell a flow in from a flow out:
   - a flow in and a flow out never share a corner of a diamond; flows in
     may merge at one, and flows out may split from one;
   - a diamond's flows use its four corners; only a diamond with more flows
     than corners (five or more) also uses the middles of its slanted sides,
     at 45 degrees (7 flows in 5 figures). Each branch out of a decision
     leaves by its own corner where it can, and not by a way out that runs
     into another box first;
   - every flow leaves or meets a diamond straight for a lead of an
     arrowhead and a label size more (at a corner square, at a slanted side
     at 45 degrees) before it may turn, so an arrowhead is never pressed
     into the first bend; a lead is shortened only where the next box is
     too close, and left out where the flow runs straight on. Rows around a
     decision are kept that far apart;
   - where a route's last stretch into a box is shorter than its arrowhead
     needs, the stretch before it is moved out, where that runs clear;
   - a fork bar takes its flows in on one side and its flows out on the
     other;
   - a document on a lane divider is not met at the middle of its top or
     bottom, so no flow runs along the divider;
   - guards are not obstacles: a guard a route then runs through is put
     beside the start of its flow, in free space.

   Where libavoid finds no way, the flow is tried again, free to meet both
   boxes anywhere; if there is still none, it is drawn as before.

Result over all 78: 167 flows are routed anew across and down. No route runs
through a box, every route ends on its boxes' outline, no off-page flow runs
through a box, and none is left unrouted. Every flow at a diamond has its full
lead (before: 35 in 20 figures turned within an arrowhead's length of it); 3
flows into an ordinary box still turn close to it, where there was no room to
move the stretch before. 71 figures end with nothing too close; in 7 a guard
is still close to a box, to be looked at one by one.

Two simpler ways were tried first and set aside:

- each angled flow as an L or a Z between its measured contact points;
- draw.io's own router.

Both ran routes through boxes and over each other (section 4 of the
demonstration shows the result that replaced them).

The choices are:

1. **Across and down, routed as above** (proposed): uniform routing, the
   layout kept in its order, boxes on a grid of rows and columns.
2. **Keep each figure's routing**, flows almost level or upright made exactly
   so: a uniform look, but not uniform routing.
3. **Across and down with each figure laid out anew**, by hand: the most
   regular result, and the most work.

## 3. Is a draw.io page a fixed size?

**No.** A draw.io drawing is made in its own units (pixels at 100 %), on an
unbounded canvas. The page is a print and export setting of each diagram: any
size (A4, A3, letter, custom), portrait or landscape, and a drawing can run
over several pages. Printing and exporting take a scale, or "fit to N pages".

So a simple diagram with a few boxes and a complex one with many can have
**exactly the same boxes, the same size, in draw.io**. The page and the export
scale then decide how large each prints. The house style above works that way:
every action is the same size in every drawing.

**How the specification shows figures today.** `UBL.xml` gives its figures no
size (`<imagedata fileref="art/…png"/>`), and the HTML stylesheet shrinks every
image to the column (`img { max-width: 100% }`). 71 of the 78 PNGs are
3425 px wide, which at 600 dpi is exactly the 145 mm column. **So every figure
is shown at the column's full width, whatever it holds.** A figure with a few
boxes gets large boxes, and one with many gets small ones. Labels print
between about 3.5 and 10 pt, 6.9 pt in the median figure.

That leaves the TC two meanings of "uniform" on paper:

1. **The same look.** Every element drawn alike, each figure still fitted to
   the column. Its labels then print at exactly the size they do today: the
   house style keeps each figure's layout and scales it as a whole. A simple
   figure still prints large, and a complex one small.
2. **The same size as well.** Every figure printed at one scale, so a label
   is, say, 7 pt on paper in every figure. A simple figure is then small on
   the page. At 7 pt, only 16 of the 78 fit the column as laid out now; the
   others need a landscape or A3 page, or a new layout that fits the column
   (taller and narrower, or split into parts).

| | printed today and fitted in the house style | at one scale (7 pt labels) |
|---|---:|---|
| Tender Guarantee Deposit (6 nodes) | 9.7 pt | 104 × 48 mm, within the column |
| Billing with Debit Note (17) | 4.5 pt | 224 × 119 mm, A4 landscape |
| CPFR Create Order Forecast (18) | 5.4 pt | 189 × 221 mm, A3 landscape |
| Procurement, Fig C.1 (34) | 3.9 pt | 263 × 124 mm, A4 landscape |
| IMFM Intermodal Freight Management (28) | 3.7 pt | 275 × 258 mm, A3 |

## The demonstration

[`house-style-demo.pdf`](house-style-demo.pdf) shows these five figures three
ways, on A4, the column at 145 mm as in the specification:

1. as published today;
2. in the house style, fitted to the column;
3. in the house style at one scale, each on the page it needs;
4. the routing of flows: Procurement with its angled flows kept, and routed
   across and down;
5. making room: Tender Qualification Application and Goods Certificate Export,
   before and after.

Rebuild it with:

```sh
poc-drawio/house-demo.sh poc-drawio/house-style-demo.pdf [<figure> ...]
```

## For the TC to decide

1. **A house style at all?** If yes: the values above, or others. It is one
   list, applied by the writer to every figure; changing it later changes
   one list, not 78 drawings.
2. **The routing of flows:** across and down, routed by libavoid (proposed),
   kept per figure, or laid out anew by hand (section 2a).
3. **Which uniform:** the same look (1), or the same size on paper as well (2)?
   The second means new layouts for most figures, or larger pages.
4. **The faithful drawings** stay as the record of the artwork (and the
   baseline), with the house style as a clearly marked new stage. Or the house
   style replaces them.
