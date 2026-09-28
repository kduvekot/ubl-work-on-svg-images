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
| arrowheads | open, 16 px long (1.35) |
| action | its words, plus 12 px each side and 10 px above and below; corners rounded to 0.45 of its height |
| document | its words, plus 12 px each side and 14 px above and below |
| decision | large enough for its question inside; 24 px across when the question stands beside it |
| start, end | draw.io's UML start and end states, 22 px across |
| fork bar | 6 px thick |
| grey rules | none: one line per divider |
| phase title (CPFR) | bold, on a white ground where a lane divider runs through it |

It settles two of the open questions of the faithful drawings (README, open
decisions 1 and 2). The end state becomes draw.io's own, and text is set at
its natural width: both are then the standard, not a departure from an
artwork.

Each figure keeps its layout. It is scaled so its labels come out at 12 px,
every element stays at its measured centre, and only the element's own size,
weights and type change. `house_style.py` does this from the same JSONs; the
draw.io writer draws the result like any other figure.

**Over all 78, 66 take the house style with nothing overlapping.** In 12, a
larger box or diamond now touches a neighbour or a guard, and the layout has to
give way a little. Most need one move:

| figure | overlaps |
|---|---:|
| UBL-2.2-DigitalAgreement | 7 |
| UBL-2.2-Tender-QualificationApplication | 5 |
| UBL-2.2-Tender-ContractInfoPrep | 4 |
| UBL-2.2-Tender-ContractInfoNotify | 2 |
| UBL-2.2-Tender-AwardPublication | 2 |
| UBL-2.0-CreateCatalogueProcess | 1 |
| UBL-2.0-DeleteCatalogueProcess | 1 |
| UBL-2.5-BillingwithCreditNoteProcess | 1 |
| UBL-2.5-BillingwithDebitNoteProcess | 1 |
| UBL-2.3-RequestForProofOfReexportationProcess | 1 |
| UBL-2.2-Tender-UnsubscribeFromProcedure | 1 |
| UBL-2.2-Tender-AwardNotification | 1 |

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
3. in the house style at one scale, each on the page it needs.

Rebuild it with:

```sh
poc-drawio/house-demo.sh poc-drawio/house-style-demo.pdf [<figure> ...]
```

## For the TC to decide

1. **A house style at all?** If yes: the values above, or others. It is one
   list, applied by the writer to every figure; changing it later changes
   one list, not 78 drawings.
2. **Which uniform:** the same look (1), or the same size on paper as well (2)?
   The second means new layouts for most figures, or larger pages.
3. **The faithful drawings** stay as the record of the artwork (and the
   baseline), with the house style as a clearly marked new stage. Or the house
   style replaces them.
