# The Fulfilment illustrations: how they were made

Four figures of UBL are not UML diagrams but pictures for the reader, showing
how shipments and consignments relate: `UBL-2.2-Fulfilment-1simple`,
`-2split`, `-3intermediary` and `-4consolidated`. UBL publishes them as PNG
(`art/` in the [UBL repository](https://github.com/oasis-tcs/ubl), branch
`ubl-2.5`), and had no source for them. They are now draw.io drawings, in
`diagrams/` like the 78 diagrams, made of pictures kept as SVG files in
`illustrations/parts/`. This folder is how they were made; the drawings are
the source now, edited in draw.io (see the repository's README).

## The source: Tim McGrath's deck

The figures are slides 2-5 of a deck by Tim McGrath, "Shipment and
Consignment" (title "Understanding the Universal Business Language",
(c) Port Community Systems 2007), which he posted to the UBL Transportation SC
on 2012-07-04, in the thread "Question about consignments and shipments":

- the thread: <https://groups.oasis-open.org/viewthread?MessageKey=29212124-416B-4961-A531-01B0FDD41EDC>
- the deck, ShipmentConsignment-2.ppt (631 296 bytes, SHA-256
  `0d5c0fd5c4a426bdd24c9fe2267c2d88d5ae361f14b241f119eb683cecff0d4c`):
  <https://groups.oasis-open.org/HigherLogic/System/DownloadDocumentFile.ashx?DocumentFileKey=f01809ee-5273-41ac-8e1d-85ac620bc43a>

"here is my slides describing the 'split' and 'consolidation' options for
shipments and consignments. we struggled a long time on these definitions and
actually got them approved by experts so we have to be careful changing
them." The deck is not kept here; `run.sh` fetches it and checks it is this
one.

The UBL PNGs are these slides in grey, a frame drawn round each, but not as
the deck has them: pictures moved and resized (the Supplier a third larger),
the Split pallets squashed, arrows shorter, and in Consolidated a second
shipment (its box, arrow and document) that the slide does not have. The
slides are also animated: they carry pictures a figure does not show (parcels
under the pallets, pallets and parcels of later steps). So **the PNGs are the
reference**, and the deck gave the parts: the pictures, the texts, the styles.

## The parts (`illustrations/parts/`)

| part | where it is used | how it was made |
|---|---|---|
| `supplier`, `buyer` | all four | the deck's clip art (WMF, vector), `wmf2svg.py` |
| `forwarder` | Intermediary, Consolidated | idem |
| `supplier-b`, `buyer-b`, `parcel-box`, `parcel-wrapped` | Consolidated | idem |
| `document` | all four, with each shipment | the deck's PNG (black ink, 468 x 595 px) traced into curves, `document.py` (potrace); a white page added under the ink |
| `pallet` | all four, with each consignment | drawn, `pallet.py`: the deck has a stock photo (400 x 361 px, with a dreamstime.com watermark) |

The clip art is in the UBL PNGs' own greys (`tones.py`): each colour the median
grey of the PNG's pixels it covers, where the drawings place it; they are
darker than a plain luminance (Buyer B's shadow 120 for 142). The document and
the pallet were drawn in grey.

**The pallet of boxes** is drawn in 3D, not traced: a camera is fitted to 11
points measured on the photo (`camera.py`, two-point perspective, 0.9 px rms),
with the pallet an EPAL Euro pallet of EN 13698-1 (`epal.py`: 1200 x 800 x 144
mm, 5 deck boards, 3 cross boards, 9 blocks, 3 bottom boards, as EPAL and its
suppliers give them), drawn layer by layer from the floor up; the stack of
2 x 2 x 2 boxes (about 597 x 421 x 428 mm each, 41 mm in from the pallet's
edges) on it. The print on the boxes was measured once, in mm on a box face,
by taking the photo back onto the faces through the camera (`backproject.py`),
and every box carries the same: the address label (256 x 74 mm), the handling
marks of ISO 780 (this way up, fragile, keep dry; 82 x 88 mm frames), and on
the sides the flap tape and the recycling symbol, Wikipedia's
[Recycle001.svg](https://commons.wikimedia.org/wiki/File:Recycle001.svg)
(public domain; its six outlines joined into the three arrows).

## The drawings: the slide's shapes, where the PNG has them

`fit.py`, per figure: the slide's shapes are read from the deck (`pptshapes.py`:
anchors, lines with their arrowheads and dashes, text boxes with their fills,
borders, text and sizes; `build.py` draws them in draw.io), and each is found
in the PNG and put where it is there:

- the slide's scale and place in the PNG, from its Supplier, Buyer and
  document (`register.py`);
- each shape rendered on its own and found near where the slide puts it
  (template matching: a picture at 50-140 % of its size and 80-125 % of its
  aspect, found with the pallet photo for a pallet; a text at 85-115 %; the
  title at 60-160 %); a picture not found is one the figure does not show;
- a label box on its border lines in the PNG, its text where the PNG has it
  in the box; a solid arrow's tip (and its direction and tail where most of it
  shows) from the PNG's ink; any other arrow slid to where it overlaps the
  PNG's ink best;
- in Consolidated, the second shipment: copies of the slide's SHIPMENT box,
  dotted arrow and document, placed where the PNG has them.

The texts are Helvetica (Arial's widths) at the slide's sizes, the label boxes
sized to their text as PowerPoint sizes them; the arrows 6 pt, their heads
0.75 of the line's width (fitted), the dotted ones in PowerPoint's dots.

Each drawing's frame is an element of `ubl-kind` `illustration`, with
`ubl-png-scale`, the PNG's px per the drawing's: the drawing's origin is the
frame's outer corner, so a point of the drawing lands at that multiple in the
PNG, and the scripts that compare with the PNGs render it so.

How close they are, against the PNGs (`history/drawio-edits/diff/one.py`, red:
ink only the PNG has; blue: only the drawing; % of the PNG's ink): see the
baseline's `summary.txt`. What remains is mostly the pallet (drawn, not the
photo), some arrowheads, and in Consolidated a label box that is wider in the
PNG than its text.

## Making them again

```sh
UBL=<clone of oasis-tcs/ubl, branch ubl-2.5> history/illustrations/run.sh
```

writes `illustrations/parts/` and the four drawings in `diagrams/` (working
files in `work/`, not kept). The fit is run twice: once with the clip art in
plain greys, then, after `tones.py` has taken the PNGs' greys, again with the
parts. A run with the parts already there starts from them, so it can end a
pixel or so from a clean run.

| script | does |
|---|---|
| `paths.py` | where the deck, the UBL clone, the working files and the parts are |
| `extract.py` | the deck's pictures (WMF and PNG) |
| `wmf2svg.py` | WMF to SVG (polygons, polylines, pens, brushes) |
| `parts_grey.py` | the clip art in plain greys, for the first fit |
| `document.py` | the document, traced |
| `camera.py`, `epal.py`, `backproject.py`, `pallet.py` | the pallet of boxes |
| `Recycle001.svg` | the recycling symbol (Wikimedia Commons, public domain) |
| `pptshapes.py` | the slides' shapes, text and styles, read from the deck |
| `build.py` | a slide, or a fitted figure, as a draw.io drawing (not in the editor's form: run `python3 tools/drawio_format.py <file>` after, as `tools/check_drawio.py` says) |
| `register.py`, `fit.py` | the figures fitted to the PNGs |
| `tones.py` | the PNGs' greys for the clip art |
| `render.js`, `render_many.js` | draw.io's own rendering, with the viewer 31.5.3, the pin when the illustrations were fitted; not moved with the pin (tools/drawio-version.json), so that fitting them again gives what it gave |
