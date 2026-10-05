# The CPFR step illustrations: how they were made

Three figures of UBL are flowcharts with clip art, not UML diagrams:
`UBL-2.2-CPFR-Steps1-2`, `-Steps3-4-5` and `-Steps6-9`. They come from the
iSURF project (Mehmet Olduz's METU MSc thesis, 2008; iSURF deliverable D6.1.1),
drawn in Visio. No source for them survives: not in the UBL distributions, the
mailing-list archives, the iSURF archives, or with the people involved. The
clip art is Visio's Work Flow stencil (meeting, agreement, document, exception,
person at a desk), which is Microsoft's, not ours to republish. So the clip art was
**redrawn**, and the figures are drawn again in draw.io from the UBL PNGs, as
the Fulfilment illustrations were (`../README.md`).

The drawings: `diagrams/UBL-2.2-CPFR-Steps1-2/`, `-Steps3-4-5/` (the pilot) and `-Steps6-9/`.

## The parts (`illustrations/parts/cpfr-*.svg`)

| part | used in | the shape it redraws |
|---|---|---|
| `cpfr-meeting` | Steps1-2 | people meeting at a table |
| `cpfr-agreement` | Steps1-2 | two people shaking hands over a stack of documents |
| `cpfr-document` | all three | a document |
| `cpfr-exception` | Steps3-4-5, Steps6-9 | a clipboard with an exclamation mark |
| `cpfr-person-at-desk` | Steps3-4-5, Steps6-9 (in pairs, one mirrored) | a person writing at a desk, a printing calculator beside |

All in grey, isometric (30 degrees), each in the frame of its crop of the
prd1 master (`docs.oasis-open.org/ubl/prd1-UBL-2.1/art/UBL-2.1-CPFR-*.png`,
600 dpi colour), against which it was compared (`made/clipdiff.py`: the part's
outline and its dark ink against the crop's, tolerance 2 px per 1480).

**One person.** The people are one figure, as the stencil drew them. The
person at the head of the meeting table was traced from a clean 730 px render
of the meeting shape, line by line, his hidden side completed by his symmetry
(the near arm is the far arm moved along the shoulder line), then split into
areas by his lines, each filled with a grey gradient fitted to the render
(`made/lines/`). From him:

- **at the desk** (`made/lines/desk10.py`): the same person, at 0.68, at a desk
  with an open book (two pages, the fold across) and a printing calculator
  (`made/lines/calc.py`: keys towards him, display, roll and tape at the back);
  the back of his chair behind him;
- **the far side of the meeting table**: the same person mirrored, without his
  forearms (under the table top), `made/meet/farperson.py`; the table, the chairs
  and the people seen from behind are the areas of the render
  (`made/meet/build.py`, `regions.py`);
- **shaking hands** (`made/hs/`): the person on the right is the same person
  mirrored at 1.26 (fitted on head, neck and shoulders to 0.5 px); his reaching
  arm is the forearm that lay on the table, and fits the render as it is. His
  other arm, the legs and feet, and the person on the left (from behind, the
  same head, neck and hands) from the render of the agreement shape. The stack
  of documents is measured on the prd1 master: three sheets, five lines of
  text, the top sheet's corner folded over as on a note, standing up a little.

**The document** and **the exception** were drawn from the prd1 master.

The renders the people were traced from are the stencil's own pictures, found
by reverse image search (Yandex), and are not kept here: the meeting shape at
730 x 792 px and the agreement shape at 551 x 763 (both on Pinterest), the
person at a desk at 196 x 191 (in a PDF of the Pontificia Universidad
Javeriana). `made/` holds the scripts as they were run, for the record; they
read those renders and the prd1 crops (`made/ref.py`) from a working folder.
**The parts are the source now**: edit one in an SVG editor, then
`python3 tools/embed_parts.py`.

## The drawings

```sh
UBL=<clone of oasis-tcs/ubl, branch ubl-2.5> python3 history/illustrations/cpfr/parts_fit.py   # parts_fit.json
cd history/illustrations/cpfr && python3 steps12.py && python3 steps345.py && python3 steps69.py
```

Each `steps*.py` writes its drawing from shapes measured on the UBL 2.2 PNG
(`art/UBL-2.2-CPFR-<figure>.png`, grey), with what they share in `cpfr.py`:
the step panels (grey, rounded; the next step dashed), the block arrows with
their documents (each label centred on the flow), the decisions, the flows and
their guards, the Manual marks, the Resolve Exception boxes (over the people
at their desks, see-through, as the PNG has it), the final node. A drawing is
the figure at its source's size (iSURF's, framed): the PNG is it times
`ubl-png-scale` with a frame of 4.5-6 px. The pictures are where
`parts_fit.py` found them in the PNG. Text is Helvetica at the sizes the PNG
has. Steps3-4-5 was the pilot; the other two were drawn the same way.

Against the PNGs (`history/drawio-edits/diff/one.py`; red: ink only the PNG
has, blue: only the drawing, % of the PNG's ink):

| figure | red | blue |
|---|---|---|
| Steps1-2 | 2.0 | 3.7 |
| Steps3-4-5 | 2.6 | 3.6 |
| Steps6-9 | 1.7 | 2.6 |

What remains is mostly the text's own shapes and the clip art, drawn with
crisper lines than the PNGs' blurred ones.
