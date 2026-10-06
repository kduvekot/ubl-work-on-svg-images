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

They edit as draw.io diagrams: each step panel is a container, and what is in
it is its child, so dragging the panel takes its contents along; every flow is
attached to the shapes at its two ends, at the points the PNG has (`exitX/Y`,
`entryX/Y`), so it follows a shape that is moved; a guard (Yes, No) is its
flow's own label. Flows run straight between their bends (`edgeStyle=none`,
as in the UML diagrams), so a bend may want tidying after a move. Tried in the
draw.io editor (embed.diagrams.net, 32.1.0, 2026-10-05) on all three: a
document dragged (its flows followed), a step panel dragged (its contents came
along, the flows from outside followed), a decision relabelled; draw.io's Save
kept every cell, id, picture and `ubl-part`, and changed only what was edited.

Against the PNGs (`history/drawio-edits/diff/one.py`; red: ink only the PNG
has, blue: only the drawing, % of the PNG's ink):

| figure | red | blue |
|---|---|---|
| Steps1-2 | 2.0 | 3.6 |
| Steps3-4-5 | 2.6 | 3.7 |
| Steps6-9 | 1.7 | 2.6 |

What remains is mostly the text's own shapes and the clip art, drawn with
crisper lines than the PNGs' blurred ones.

## How it was found, and decided (2026-10-03 to 05)

So that none of it has to be searched or decided again.

**The sources.** A dossier on the CPFR figures was put together before this
work, from primary sources only (outside this repository, not to be kept in
it). What it found:

- The figures were first published in Mehmet Olduz's METU MSc thesis
  (September 2008, figures 3.1-3.4), then in iSURF deliverable D6.1.1
  (2008-2009), where they are embedded as PNGs of 613-950 px. They reached UBL
  2.1 through iSURF (FP7 ICT-213031).
- Every copy in UBL is that PNG enlarged: prd1
  (`docs.oasis-open.org/ubl/prd1-UBL-2.1/art/`, 600 dpi, colour) is the D6.1.1
  figure times 5.09 (Steps3-4-5, 6-9) or 6.25 (Steps1-2); UBL 2.2 to 2.5
  (`art/` in the UBL repository) are greyscale copies, 1712 px wide.
- **So a picture is judged at its real size**, as it is in the D6.1.1 figure
  (the person at a desk is 74 x 68 px there, the meeting 93 x 100), not on the
  enlarged crops: at that size the outlines of the original are about 1 px,
  which is why the parts' outer lines are heavy (5 px at a part's own scale).

**What was searched, and not found.**

- No Visio (or other) source of the figures: not in any UBL distribution, not in
  the OASIS archives. The UBL TC's minutes of May-June 2010 show the CPFR
  artwork sources went privately to Peter Borresen and Jon Bosak:
  <https://lists.oasis-open.org/archives/ubl/201005/msg00022.html>,
  [201005/msg00028](https://lists.oasis-open.org/archives/ubl/201005/msg00028.html),
  [201006/msg00001](https://lists.oasis-open.org/archives/ubl/201006/msg00001.html),
  [201006/msg00016](https://lists.oasis-open.org/archives/ubl/201006/msg00016.html),
  [201006/msg00018](https://lists.oasis-open.org/archives/ubl/201006/msg00018.html),
  [201006/msg00028](https://lists.oasis-open.org/archives/ubl/201006/msg00028.html),
  [201006/msg00029](https://lists.oasis-open.org/archives/ubl/201006/msg00029.html),
  [201008/msg00014](https://lists.oasis-open.org/archives/ubl/201008/msg00014.html).
  Peter Borresen looked for them (October 2026): they are not there any more.
- The clip art is the shapes of Visio's *Work Flow Diagram* template: the
  stencils *Work Flow Steps* (`WFSTEP_M.VSS`: meeting, agreement, issue) and
  *Work Flow Objects* (`WFOBJ`: document; the person at a desk). Microsoft's,
  and not to be republished; no free copy of the stencils was found.
- **Higher-resolution copies of the shapes**, by reverse image search on crops
  of the prd1 PNGs (Yandex: upload the crop to
  `yandex.com/images/search?rpt=imageview&format=json`, then fetch the result's
  `cbir_page=similar` and `cbir_page=sites` pages; TinEye was blocked, Google
  asks for a captcha):
  - the meeting, 730 x 792:
    <https://i.pinimg.com/originals/17/29/4a/17294a135d317eb66ad2760e1900367a.png>;
  - the agreement (two people shaking hands), 551 x 763:
    <https://i.pinimg.com/originals/b8/6c/e6/b86ce626dfe8dd2bca2ff0ef311edf9d.png>;
  - the person at a desk, 196 x 191: an image in a PDF of the Pontificia
    Universidad Javeriana, *Guía de usuario radicación PQRSFD*
    (<https://www.javeriana.edu.co/recursosdb/d/institucional/guia-de-usuario-radicacion-pqrsfd>);
  - the document and the clipboard: none found; drawn from the prd1 master.

  These copies were used to trace from, and are not kept.

**Tried and dropped.** Pictograms drawn freely (not like the original); a 3D
model of the person (over-fitted); a plain automatic trace of the renders (1.4
MB, and the people's open lines leave whole bodies one area). What worked: the
person's lines traced and numbered, corrected line by line, his hidden side
completed by his symmetry, and only then the areas filled.

**Decided on the way** (with the repository's owner, in the sessions that made them):

- grey, as the UBL 2.2 PNGs; isometric, as the stencil;
- the people are one person throughout (seated, standing, from behind,
  mirrored), in the same pose where the original has it;
- at the desk: the chair is the back of it behind him, across his back; the
  paper an open book (two pages, the fold across), near him and the edge he
  sits at; the calculator a printing calculator (keys towards him, the roll and
  tape at the back);
- the documents of the agreement: the top sheet's corner folded over as on a
  UML note, standing up a little (165 degrees, `made/hs/docs.py`, `FOLD`);
- the Resolve Exception box over the people at their desks, see-through, as in
  the PNG;
- the drawings edit as draw.io diagrams (panels as containers, flows attached),
  not as loose shapes;
- the shading of the handshake people left for later (below); the greys of
  the five parts accepted as they are (2026-10-06): at their real size in the
  figures they are a little paler than the UBL PNGs' pictures, which is good
  enough.

**Tools changed for these figures** (they hold for all figures):
`tools/check_svg.py` judges "on white" by the page round the drawing, not the
commonest grey; `tools/export_drawio.js` makes a part's own `<use>` a copy, and
draws each figure on a clean page (an export is the same alone or in a batch);
`history/drawio-writer/render-drawio.js` follows the same pin as the export
(`tools/drawio-version.json`: 31.5.3 then, 32.0.2 since 2026-10-05, 32.2.0 since 2026-10-06).

**How the editor was tried.** draw.io's editor (embed.diagrams.net) in
Chromium (playwright), the drawing sent to it with draw.io's embed protocol
from a page that frames it (opened directly with `setFileData` its labels
stayed hidden), edited with the mouse and keys as a person would, and saved
with its own Save; the saved file compared cell by cell with the one written.
In that environment the browser reached the web only through node
(`context.route` with `route.fetch()`), as the proxy's certificate was not in
the browser (how to put it there: README, "Upgrading draw.io").

## Open work

- **Shading of the handshake people** (`cpfr-agreement`): the render's
  darker upper arm of the person on the left and the darker strips on both
  people's legs are not there yet; each larger area of them has one gradient.
  The way to do it is the one used for the person at the head of the meeting
  table (`made/lines/`): their lines traced one by one, so that they split the
  bodies into the areas the render shades. A future improvement; the figures
  are complete without it.
- **The clip art's origin:** decided 2026-10-06 (README, "Questions for the
  TC", A4): the traced people are published as they are.
- **The draw.io desktop app:** these drawings, as all 96, were tried in the web
  editor only (README, "Open work").

**`made/` cannot be run as it is** (a limitation, not work): its scripts read the
renders traced from and the prd1 crops from a working folder that is not kept. They
are the record of how the parts were made; the parts themselves are the source.

The three drawings are in the baselines `baselines/2026-10-05/` (the numbers above are its) and
`baselines/2026-10-06/` (with all 96).
