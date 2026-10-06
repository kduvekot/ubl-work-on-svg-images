# Edits to the draw.io drawings, after the switch

Since the switch (2026-09-29) the drawings in `diagrams/` are the source of
truth. Most changes to them are made by hand in draw.io, but some went over
all 78 at once. This folder has the scripts that made those changes, and the
scripts that compared the result with the original PNGs. They are kept to show
how the drawings came to be as they are, not to be run again over the current
drawings. Each one was written for the state it was run on.

## The edits, in order

Each script edits a folder of drawings in place (`<dir>/<figure>/<figure>.drawio`).
Run in this order on the drawings at `db5f324` (the state before the first
edit), they give the drawings at `26ec6d5` exactly: every file the same, byte
for byte.

| commit | script | what it did |
|---|---|---|
| `2dc02d7`, `ad68c06` | `twelve.py` | One text size, draw.io's own 12 pt: every label loses its `fontSize`. A box whose words no longer fit at 12 pt is made wider or taller about its centre (83 boxes). Where that would take it out of its lane, its label is broken over one more line (10 labels). Words beside a shape (a decision's question) and guards keep their gap. Two two-line questions are moved up 6 px by hand afterwards; the script records this too. (`2dc02d7` was a first run; `ad68c06` is the run shown here.) |
| `f438cc7` | `arrowheads.py` | One arrowhead everywhere: UML's open head, 10 px (1,045 flows in 58 figures). |
| `0c0bc93`, `26ec6d5` | `insert_space.py` | Every arrow at least 3 times its head long (30 px): where one is shorter, space is inserted across the whole figure, as draw.io's own "insert space" does (109 insertions in 35 figures). `0c0bc93` grew 13 shapes that the space ran through. `26ec6d5` keeps their size: they stay, or move whole past the space, and only one still grows by 2 px. The script also records one contact that was moved back onto its document by hand. |

```sh
python3 history/drawio-edits/twelve.py <dir>
python3 history/drawio-edits/arrowheads.py <dir>
python3 history/drawio-edits/insert_space.py <dir>
```

`twelve.py` measures text with the Liberation Sans fonts, which draw.io's
render also uses here.

`library.py` builds the shape library `tools/ubl-library.xml` (commit
`db5f324`); it still writes the committed file unchanged.

## The comparison with the original PNGs: `diff/`

These scripts hold each drawing against the PNG that OASIS publishes. The
result is one PDF: an introduction with a table of all figures, then one
page per figure with the PNG, the drawing, and the diff (grey where both have
ink, red for the PNG only, blue for draw.io only), in the order and with the
titles of the UBL 2.5 specification. It covers the 4 illustrations too (the
Fulfilment figures, `history/illustrations/`), made after these edits: they
had no space inserted, and are drawn at the scale they were matched to their
PNG at (their frame's `ubl-png-scale`).

```sh
UBL=<clone of oasis-tcs/ubl, branch ubl-2.5> history/drawio-edits/diff/run.sh <out dir>
```

The clone is needed for its `art/` (the PNGs) and `UBL.xml` (the order and
titles). The scripts write only to `<out dir>`. They need Python 3 with numpy,
scipy and pillow, Node with playwright, and `pdfunite`.

- `common.py`: shared locations, each figure's natural width (as
  `history/drawio-writer/run.sh` builds it; an illustration's: its PNG's width
  at its `ubl-png-scale`), and the figures in the specification's order.
- `one.py`: compares one figure. It uses the PNG at its own pixel size, and
  renders the drawing onto exactly that canvas with draw.io's own code, in the
  PNG's coordinates (`render-drawio.js`, origin `png`). The
  tolerance is 2 px per 1480 px of width. Where the drawing grew, the PNG gets
  white at its right and bottom. It also holds the published PNG
  (`to-ubl-repo/art`) against the drawing's picture rendered at its size (the
  deck's last column: they are one picture, `tools/drawio_picture.js`).
- `insertions.py`: records where `insert_space.py` inserted space, by
  replaying it on the drawings as they were before (`f438cc7`).
- `cutpng.py`: for a figure that grew, inserts the same space in the PNG, so
  that both are compared with the same things moved.
  - At each cut, a line of pixels next to it is repeated to fill the space, so
    lines across it run on unbroken.
  - Where the drawing kept a shape whole, the cut steps round it.

  This took the 35 figures that grew from about 45% red to about 8%.
- `pdf.py` and `print.js`: write the pages and print them to PDF.

The comparison holds for the drawings as `insert_space.py` left them. After a
drawing is edited by hand, `one.py` still compares it as it is. `cutpng.py`
inserts the space where it was inserted then, not where later edits may have
moved things.
