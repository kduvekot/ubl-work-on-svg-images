# ubl-work-on-svg-images

Editable sources for the artwork of the UBL specification: all **96 figures** UBL 2.5 uses, as
**draw.io drawings** in `diagrams/`, and their export for the UBL repository in `to-ubl-repo/`
(an SVG and two PNGs per figure). UBL publishes these figures as PNG and most of their original
sources are lost; these drawings are now the figures' source. They are:

- the **78 UML activity diagrams**;
- **7 illustrations**: the 4 Fulfilment figures and the 3 CPFR step figures;
- **11 figures of other notations**: the 4 of Group A (BPMN: Ordering and Business
  Information; phase maps: Pre-award and Procurement), the 3 phase and overview figures of
  Group B and the 4 reference figures of Group C.

How they came to be, and the measurements behind the rules below: `history/README.md`. What the
TC still has to decide is in one place, near the end: "Questions for the TC" (the questions to
settle before the commit to the UBL repository, A1-A5, are answered, and so are B and C; D is for
the diagrams' next revision).

**Once committed to the UBL repository, its drawings are the figures' source** (A3, answered
2026-10-06): `images/<figure>.drawio` there, which its build renders into the SVG and the PNGs, so
that the build goes on from `art/` and `htmlart/` as it always has ("In the UBL repository: the
build renders the drawings").

## The source of truth: the draw.io drawings

```
diagrams/<figure>/<figure>.drawio        96 figures, e.g. diagrams/UBL-2.5-BillingwithDebitNoteProcess/
                                         (78 diagrams, 7 illustrations: UBL-2.2-Fulfilment-1simple ...,
                                         4 of BPMN or phase maps: UBL-2.3-OrderingProcess ...,
                                         3 phase or overview figures: UBL-2.2-Open-edi-Overview ...,
                                         and 4 reference figures: UBL-2.2-UDT-QDT ...)
illustrations/parts/*.svg                the pictures the illustrations are made of, to edit
tools/embed_parts.py                     puts an edited picture into the illustrations
tools/ubl-library.xml                    the UBL shapes, as a draw.io library, for editing
tools/check_drawio.py                    the check, run by hand after an edit
tools/drawio_baseline.py                 holds the drawings against the baseline
tools/drawio_format.py                   writes a drawing as draw.io's editor does (a text diff against the editor's)
tools/export_drawio.js                   exports them for the UBL repository: SVG, PNG
tools/drawio_picture.js                  a drawing's picture, where it starts and how large: the export's and every render's
tools/check_svg.py                       checks an export
tools/drawio_upgrade.py                  is there a newer draw.io, and does it change anything
tools/drawio_editor_roundtrip.js         opens and saves drawings in the live editor (for drawio_upgrade.py --editor)
tools/drawio-version.json                the pinned draw.io release (the one place)
to-ubl-repo/                             what goes to the UBL repository: the export, and the
                                         tools that render it there (utilities/artwork/)
baselines/2026-10-06/                    the baseline: all 96 drawings as they are now (2026-10-05, 2026-09-30: the ones before)
```

**Edit a figure by opening its `.drawio` file in draw.io** (the desktop app, or
diagrams.net) and saving it back. Nothing is generated over these files any more.

### The 78 UML activity diagrams

Each is built from draw.io's own parts, and an edit keeps them so:

- the frame is a **pool** (BPMN palette, "Vertical Pool 1") and each party a **lane** in it:
  widening a lane moves the lanes beside it and grows the pool;
- actions, documents, decisions, starts, ends, fork/join bars and notes are the shapes of
  draw.io's **UML palette**, standing in their lane (a child of it);
- **flows** are attached to their elements at both ends; a guard is the flow's own label, a
  decision's question the diamond's own label;
- CPFR's dashed phase boxes and IMFM's phase rules and names are part of the pool, so they
  move with it;
- **whole pixels** only and **fixed line weights** (1, and 2 for documents and the frame); a
  flow drawn almost level or upright is exactly so;
- **one arrowhead everywhere:** UML's open head, 10 px (`endArrow=open;endSize=10`), and every
  arrow at least **3 times its head long** (30 px, the stretch after its last bend): where one
  is shorter, make room as draw.io's "insert space" does (Ctrl+Shift+drag on the background);
- **one text size: draw.io's own 12 pt** for every label (no `fontSize` in the style), each
  box holding its words at that size.

What keeping these took when they were set (the space inserted, the boxes widened):
`history/README.md`, "How the 78 were drawn".

### The model inside each drawing

Each drawing also holds the figure's **model**: what it says, not only how it
looks. Every element carries the model's id and its kind (`ubl-kind`); what the
drawing does not show by itself is kept on the element as a custom property,
visible and editable in draw.io under **Edit Data** (Ctrl+M). A string is kept as
it is, anything else as JSON.

| property | on | what it says |
|---|---|---|
| `ubl-kind` | every element | `frame`, `lane`, `action`, `object` (a document), `decision`, `initial`, `final`, `fork`, `note`, `flow`, `off-page-flow`, `text`, `mark`, `phase-boundary`, `band-divider`, `band-title`, `lane-divider` |
| `ubl-flow` | flow | its kind: `control`, `object`, `goods`, `information`, `precondition` |
| `ubl-guard` | flow | the id of the text that is its guard (the label) |
| `ubl-between`, `ubl-lane` | node | a document passed between parties (the parties, left to right); the lane a node belongs to where it is drawn in another (`null`: none) |
| `ubl-continues`, `ubl-counterpart`, `ubl-port`, `ubl-direction` | off-page flow | the figure where it continues, the flow there, which port, in or out |
| `ubl-text`, `ubl-text-<id>` | element | the id(s) of the text(s) shown as its label; a text's own words where the label shows them otherwise |
| `ubl-label` | node, lane, phase | its own words, where its label shows a text's |
| `ubl-members` | phase | the elements in the phase |
| `ubl-question`, `ubl-unstated`, `ubl-passes-to`, `ubl-linked-process`, `ubl-reference`, `ubl-scope`, `ubl-same-as`, `ubl-trigger`, `ubl-annotates`, `ubl-also-in`, `ubl-defined-in`, `ubl-implied-choice`, `ubl-both-ends`, `ubl-title-shown`, `ubl-title-source`, `ubl-mark`, `ubl-rule`, `ubl-on`, `ubl-meaning`, `ubl-labels`, `ubl-draws`, `ubl-segments` | as the model has them | the model's other facts, as recorded with the TC (see the schema in `history/tools/schema/diagram.schema.json` for each) |
| `ubl-offset` | frame | the margin between page and drawing |

### Editing a drawing

1. Open the figure's `.drawio` file in draw.io.
2. **Open the UBL shape library once:** `tools/ubl-library.xml`, with
   *File › Open Library* in the desktop app (*File › Open Library from ›
   Device* on diagrams.net). It stays in the left panel. Its shapes carry their
   `ubl-kind` already, in the drawings' style:
   - action, document (object node), decision, start, end, fork/join bar
     (horizontal and upright), note, text;
   - a lane: drop it on the pool, and the pool places it after the last lane;
   - a control flow and an object flow: drop one, then drag its ends onto the
     two elements.
3. Draw new elements from that library, not from draw.io's own palettes: a shape
   from those has no `ubl-kind`, and the check below reports it.
4. Tell the model what the drawing cannot show, in *Edit Data* (Ctrl+M) on the
   element: for a document drawn on a lane divider, the parties it passes between
   (`ubl-between`, e.g. `["lane-buyer", "lane-seller"]`); for a new flow, its kind
   if it is neither a control nor an object flow (`ubl-flow`). The check warns
   where these are missing.
5. Save, and run the check.

(Tried by editing in the web editor; all 96 drawings opened and saved again, unchanged, in the
live editor: `history/README.md`, "The editor, tried". The desktop app is not tried yet: "Open work".)

### Ordering, a BPMN drawing

`UBL-2.3-OrderingProcess` is drawn with draw.io's BPMN shapes, and holds its BPMN model
as the 78 hold theirs (`history/group-a/README.md`, "Ordering as a draw.io BPMN
diagram"): every element's id is its BPMN id (`Task_1bnlp2b`, `MessageFlow_0w3w0y5`, ...),
its kind is `ubl-kind` (`pool`, `task`, `gateway`, `event`, `flow`, `message-flow`) and its
BPMN type `ubl-bpmn-type` (`participant`, `task`, `exclusiveGateway`, `startEvent`,
`endEvent`, `sequenceFlow`, `messageFlow`; an end event also `ubl-bpmn-event-definition`,
`terminateEventDefinition`). Edit it with draw.io's BPMN palette (*More Shapes › BPMN*):
put a new task, gateway or event in its pool, attach a flow at both ends, and give a
flow its name as its own label; then give the new element, in *Edit Data* (Ctrl+M), its
`ubl-kind` and `ubl-bpmn-type`. `tools/check_drawio.py` reports an element without them,
and a flow not attached. The drawing is Ordering's source, and enough: no `.bpmn` is written
for it ("Questions for the TC", C3).

### The other figures of Groups A, B and C

Their own READMEs say how they are drawn: `history/group-a/README.md` (Ordering, above, and the
TC's own three drawings, adopted as they are: Pre-award, Procurement, Business Information),
`history/group-b/README.md` and `history/group-c/README.md` (drawn from the UBL PNGs). They have
no pool of lanes: `tools/check_drawio.py` checks their form, ids, attached flows and kinds (they
carry `ubl-notation`); the TC's three have no kinds, which it says. Real BPMN 2.0 files are a
possible option for the distant future only ("Questions for the TC", C1).

### The illustrations: the Fulfilment figures

`UBL-2.2-Fulfilment-1simple`, `-2split`, `-3intermediary` and `-4consolidated`
are not UML diagrams but pictures for the reader: parties, documents and
consignments, with the shipments and consignments between them. Their drawings
are made of

- **pictures**: SVG parts, embedded in the drawing as images, each element
  naming its part (`ubl-part`, under Edit Data): the Supplier, the Buyer, the
  forwarder, Supplier B, Buyer B, two parcels (the clip art of the deck they
  come from), the document and the pallet of boxes; the parts are kept as files
  in `illustrations/parts/`;
- **arrows**: draw.io lines, 6 pt, solid (a consignment) or dotted (a shipment);
- **labels**: the grey SHIPMENT and CONSIGNMENT boxes, and the texts, in
  Helvetica at the sizes the figure has them (not 12 pt);
- **the frame**, an element of `ubl-kind` `illustration`: this is what tells
  the tools a figure is an illustration. Its `ubl-png-scale` is the PNG's px per
  the drawing's: the drawing's origin is the frame's outer corner, so that the
  drawing lands on the UBL PNG at that multiple.

**Edit** in draw.io: move, resize, relabel, add an arrow or a label. A picture
is one image in draw.io; **to change a picture**, edit its part in
`illustrations/parts/` with an SVG editor (Inkscape, say), then put it into
every drawing that uses it:

```sh
python3 tools/embed_parts.py
```

They are not checked by `tools/check_drawio.py` (they hold no model); the export puts each picture
in the SVG as the SVG it is, prints `art/` in grey (8 bit), and takes the frame as the page. How
they were made: `history/illustrations/README.md`.

### The CPFR step illustrations

`UBL-2.2-CPFR-Steps1-2`, `-Steps3-4-5` and `-Steps6-9` are drawn the same way:
illustrations (frame of `ubl-kind` `illustration`), their flowcharts in
draw.io's shapes, their pictures the parts `illustrations/parts/cpfr-*.svg`:
the CPFR figures' clip art, redrawn (the originals are Visio stencil art, and
lost). How the parts and the drawings were made:
`history/illustrations/cpfr/README.md`.

### Checking a drawing

```sh
python3 tools/check_drawio.py diagrams/*/*.drawio
```

(An illustration is not checked: it says so.)

Run it by hand after an edit. It checks the conventions a drawing must keep:
every element has a known `ubl-kind` and a unique id; the lanes are in the pool
and every node in a lane; every flow is attached at both ends (a flow leaving
the page at one); a guard is used once. A finding makes it fail (exit status 1).
It also **warns** where the model is poorer than it should be - a flow without
its kind (`ubl-flow`), a document across a lane divider without the parties it
passes between (`ubl-between`) - and where an arrow is shorter than 3 times its
head: make room in draw.io by Ctrl+Shift+dragging on the background.

(With `--against history/diagrams` it compares the model with the JSONs the 78 were drawn
from: `history/README.md`, "The drawings against their JSON models".)

### The baseline: `baselines/2026-10-06/`

All 96 drawings as they are now, for later edits to be held against: `diagrams/` (the drawings,
byte for byte), `renders/` (each drawing's picture, as the export makes it: "One picture, one
origin" in "The export's rules"; drawn as `compare` draws it again, the pinned draw.io at scale 1,
the browser enlarging) and `summary.txt`, `summary.json` (per
figure, how it compares with the original PNG: red, ink only the PNG has; blue, only the drawing;
in % of the PNG's ink). It was made again the same day, its drawings unchanged, when its renders
became pictures and the pin moved to 32.2.0 (`history/README.md`, "The baselines"). The baselines
before, `2026-10-05` and `2026-09-30`, are kept as they were, their renders in the coordinates of
their PNGs, and `compare` reads them so;
what they hold, and how the 11 figures drawn later are placed on their PNGs: `history/README.md`,
"The baselines".

```sh
python3 tools/drawio_baseline.py compare baselines/2026-10-06 [--out <dir>] [<figure> ...]
```

Run it by hand after an edit. Per figure it says `same` (the baseline's file,
byte for byte), `same-drawing` (the file differs, not the model, not a pixel),
`model` (the model differs; what, is listed) or `DRAWING` (pixels differ;
with `--out`, a picture shows where: red only in the baseline, blue only in the
drawing). Both are rendered afresh, the same way, and compared with no
tolerance; where the baseline no longer renders as it did (a newer pin), it says so.
A figure that is not in the baseline says `new` and is not compared: it is not a
difference (none in 2026-10-06; against 2026-10-05, the 11 of Groups A, B and C).

A new baseline is a new dated folder, made only when asked for, from a run of the
comparison of the drawings with the original PNGs (it also makes the PDF of it, which
is not kept, about 36 MB):

```sh
UBL=<clone of the UBL repository at 3d81e8a> history/drawio-edits/diff/run.sh <diff dir>
python3 tools/drawio_baseline.py make <baseline dir> <diff dir> [<figure> ...]
```

With figures named, only those are added to (or replaced in) the baseline, and a run of
`history/drawio-edits/diff/one.py` on those figures is enough.

### Images made from the drawings: `to-ubl-repo/`

`to-ubl-repo/` holds everything that is to be committed to the UBL repository,
and nothing else, laid out as there: copied over a clone of it, it adds or
replaces, per figure, `images/<figure>.drawio` and
`images/<figure>.svg`, `art/<figure>.png` and `htmlart/<figure>.png`, and adds
`utilities/artwork/`, the tools that render them there (below). Nothing
in it is edited by hand: after an edit of a drawing, export it again and check.

It goes to the branch `ubl-2.6` ("Questions for the TC", A1, answered). The figures' files
would fit the 2.5 branches too (their `art/`, `htmlart/` and `images/` are the same); the build
step was tested on `ubl-2.6` only.

```sh
NODE_PATH=$(npm root -g) node tools/export_drawio.js [--report <file.json>] to-ubl-repo diagrams/*/*.drawio
python3 tools/check_svg.py to-ubl-repo
```

The check also fails where a drawing in `to-ubl-repo/images/` is no longer its source in
`diagrams/`: export again. An export of unchanged drawings is the same, byte for byte, in one
environment. In another (other fonts, other font rendering) the PNGs' text can come out a fraction
of a pixel apart, while the `.drawio` and `.svg` files stay the same: such PNGs are not a change,
so re-export only the figures whose drawing changed (measured: `history/README.md`, "The export:
how it is made, and what was decided"). `--report` writes, per figure, its size, the scale it is
fitted to the page at and the size its text prints at (kept out of `to-ubl-repo/`: it is not for
UBL). The export needs Node with playwright; the check Python 3 with pillow.

**The commit to the UBL repository also removes 9 files**, which a folder of files cannot say:
from `images/`, the 3 older sources of our figures under other names and 5 more files that are
none of the 96 and that `UBL.xml` does not use (A2; left there, they would confuse); from `art/`,
the PNG of a figure `UBL.xml` no longer uses (A5):

```sh
git rm "images/UBL 2.3-Common Transportation Report-Process.drawio" \
       "images/UBL 2.3-ImportDeclaration-Process.drawio" \
       "images/UBL 2.3-Transit Declaration Process.drawio" \
       images/UBL-2.3-GoodsCertificateProcess.svg \
       images/UBL-2.3-RequestForProofOfReexportationProcess-old.svg \
       images/UBL-2.2-Tender-Contract.svg \
       images/UBL-2.2-Tender-TenderingProcess.svg \
       images/UBL-2.3-Tender-TenderingProcess.drawio \
       art/UBL-2.0-BillingwithCreditNoteProcess.png
```

Then `images/` holds the 96 drawings and their SVGs and nothing else, and `art/` and `htmlart/`
the 96 figures' PNGs (tried on `ubl-2.6`, 2026-10-06: the same files as `to-ubl-repo/`).

**A second commit, of its own: the figures commented out in `UBL.xml`** (decided 2026-10-06 by the
UBL editor). `UBL.xml` on `ubl-2.6` has one comment that points at figures: line 700, in "Business
Object Overview" (`S-BUSINESS-OBJECT-OVERVIEW`), a paragraph and two figures,
`UBL-2.2-UseCaseOverview` and `UBL-2.2-UseCase`, which no branch has ever had a PNG or a source of.
It goes, in a commit of its own on `ubl-2.6`: it changes the specification's text, not its
artwork, and what the build publishes stays the same (a comment is not published):

```sh
sed -i '/<!--<para>The following diagrams illustrate the business context use case/d' UBL.xml
```

One line goes (tried on `ubl-2.6` at `d3e98ac`: `xmllint` passes before and after, and `UBL.xml`
then names neither figure). `UBL-2.5.xml` there, the document of the previous version, has the same
comment and is left as it is.

#### In the UBL repository: the build renders the drawings

Decided 2026-10-06 (A3): from the commit on, a figure is edited in the UBL repository, in its
`images/<figure>.drawio`, and the build renders every figure from its drawing before Ant packages
the specification: what comes after (`art/` for Réalta, `htmlart/` for the HTML) stays as it is. The
rendered files are committed too, so that the repository shows them; the build renders its own.

`to-ubl-repo/utilities/artwork/` is that: `render.sh`, the build's step; `README.md`, the editors'
guide (editing a figure, the build, the draw.io pin); and copies of the tools and the pictures
here: `export_drawio.js`, `drawio_picture.js`, `check_svg.py`, `drawio-version.json`, `check_drawio.py`,
`drawio_format.py`, `ubl-library.xml`, `embed_parts.py` (from `tools/`) and `parts/` (from
`illustrations/parts/`). The tools work in either layout (`diagrams/<figure>/` here, `images/`
there). `check_svg.py to-ubl-repo` also fails where a copy is behind: "utilities/artwork/X is not
tools/X: copy it again" ("Before a pull request", step 4).

`render.sh` renders the figures `UBL.xml` shows (`art/<figure>.png`) that have a drawing, so a
drawing in `images/` that is not a figure (as before the commit, the 4 it removes) is left alone. It
renders into a scratch folder and checks (`check_svg.py`); only a render that passes replaces the
committed files. Where the tools are missing or the render fails (a drawing that is not well-formed
is refused), the committed files are used. Where a committed SVG is not what its drawing gives, it
says so. Each is a GitHub annotation of the run; it never fails the build. Each is also reported in
the package, as the build reports its own problems (`INTEGRITY-PROBLEMS.txt`):
`ARTWORK-PROBLEMS.txt`, at the top of the package beside the specification's PDF, says what
happened and which files the build used (decided 2026-10-07 by the UBL editor). No problem, no file.

**The commit also edits three files of the UBL repository** (a folder of files cannot carry an edit):

- `build-common.sh`: before `echo Building package...`, `artworkProblems=$(mktemp)` and
  `bash utilities/artwork/render.sh "$artworkProblems"`; after the Ant build (after `sleep 2`), that
  file, if not empty, written to the package as `ARTWORK-PROBLEMS.txt`, and removed. Not before:
  Ant takes a `.txt` file at the top of the package for a problem of its own and then skips its
  consistency check (and one in its artefacts, the documentation);
- `.github/workflows/build.yml`, job `build`, between the steps `Dependencies` and `Build`: the
  steps `Set up Node` (`actions/setup-node@v7`, Node 22) and `Artwork tools` (playwright 1.56.1 with
  its Chromium, `fonts-liberation`, `python3-pil`), both `continue-on-error`, so that a failed
  install still builds the specification from the committed files and says so in
  `ARTWORK-PROBLEMS.txt`; as in `to-ubl-repo/utilities/artwork/README.md`, "The build";
- `README.md`, its section "Artwork" (draw.io's PNG export by hand, the `htmlart/` copy scaled in
  GIMP) replaced by:

  ```markdown
  ### Artwork

  Each figure is drawn in [draw.io](https://www.drawio.com): `images/<figure>.drawio` is its
  source, and every build renders it into `images/<figure>.svg`, `art/<figure>.png` and
  `htmlart/<figure>.png`. How to edit a figure, or add one:
  [`utilities/artwork/README.md`](utilities/artwork/README.md).
  ```

  `drawio-export.png`, the screenshot that section shows, is then used nowhere.

**Tested 2026-10-06** on a checkout of `ubl-2.6` (`d3e98ac`), `to-ubl-repo/` copied over it and
`build-common.sh` edited, with `build.sh` run as the workflow runs it (Java and 7z stubbed): all 96
rendered and checked in about 1.5 minutes, before Ant; the committed SVGs came out the same, byte for
byte, and the PNGs a fraction of a pixel apart (0.02-5.9 % of their pixels: another container than
the export's, as said above); a drawing edited and committed without rendering gave the warning; a
drawing cut short was refused and the committed files used; without Node the committed files were
used; the 4 drawings that are no figure were left alone. The export with playwright's own Chromium,
as on GitHub, gives the same files (3 figures tried).

**Tested on GitHub 2026-10-06**, on a fork of the UBL repository (`kduvekot/ubl`, with the UBL
repository's workflow and a Réalta account): `ubl-2.6` as it is (run 64, the baseline) and with the
commit (branch `ubl-2.6-artwork`, run 68, before the problems file). In run 68 the artwork tools
installed in 22 seconds and the 96 figures rendered and checked in 62 seconds; then Ant
(`BUILD SUCCESSFUL`, 39 minutes), no DTD or writing-rule errors, and Réalta without issues (the PDF,
HTML, ISO DOCX, ISO PDF, NISO XML and ODT made). Held against run 64, its log differed only by the
artwork steps and by `art/artpdf` holding 96 PNGs, not 97; the three packages (`.7z`), file by file,
only by what the commit changes: the figures and their drawings, the files it edits, `UBL-2.6.xml` by
the removed comment, and the documents that hold the figures. The PDF holds all 96 figures (black and
white, grey for 11; 17 at another size, one page more: "Questions for the TC", B3); the HTML is the
same but for its date. Of the 192 PNGs the build rendered, 185 are the committed ones byte for byte;
7 (Default Validation, Open-edi Application, Ordering, Pre-award) are a few pixels of text apart, as
on any other machine. The packages are half their size or less (57, 43 and 51 MiB to 28, 12 and
26), the PDF 21 to 7 MB.

**The problems file, tested 2026-10-07** as above (`build.sh`, Java and 7z stubbed): no file after a
normal render; at the top of the package, the right report for each of the tools missing, a drawing
cut short (the render's error, naming the drawing), the check failing (the figure, and why) and a
drawing edited without rendering (its SVG). Not tested: the commit as now on GitHub (Open work), a
failed install on GitHub's runner, and the ISO DOCX and NISO XML opened (only their size, smaller as
the PDF's).

After the commit, `diagrams/` here is the record of the drawings as committed, not their source.
The tools that stay here, the baseline and the upgrade check, work on `diagrams/`: to use them on
the UBL repository's drawings, bring those back into `diagrams/<figure>/` first.

#### The export's rules

Decided 2026-09-30 from how the [UBL repository](https://github.com/oasis-tcs/ubl) publishes its
artwork (the reasons and the measurements: `history/README.md`, "Decided for that export"):

- **what it makes**, per figure: `images/<figure>.drawio` (the source), `images/<figure>.svg` (the
  revisable vector file ISO asks for), `art/<figure>.png` (print: 600 dpi, at most 3425 px, 5.7 in,
  wide; white background, no border) and `htmlart/<figure>.png` (web: at most 750 px wide), both
  PNGs rendered from the SVG; `UBL.xml` keeps pointing at `art/<figure>.png`;
- **the PNGs:** `art/` black and white (1 bit), as line art is printed; 8 bit grey for the 7
  illustrations and the 4 drawings marked `ubl-art="grey"` (Business Information, Schema
  Dependencies, UDT-QDT, Model Realization); `htmlart/` 8 bit grey, its edges smoothed;
- **the SVG is real vector:** text as `<text>`, not HTML in `<foreignObject>` and not outlines; no
  bitmap and no `<use>`; an illustration's pictures as nested `<svg>`;
- **the drawing is the truth:** the SVG does not carry the drawing, only the picture and a comment
  naming the `.drawio` to edit;
- **one picture, one origin:** where a drawing's picture starts and how large it is, is draw.io's own
  export crop (the drawing's bounds, every line and label included, the corner rounded down to a whole
  unit; an illustration's: its frame, to the line's outer edge), read from draw.io and said once,
  `tools/drawio_picture.js`, for the export and for every render (the baselines, the upgrade check, the
  comparison deck). A comparison with an original UBL PNG asks for that PNG's coordinates by name
  (`history/drawio-writer/render-drawio.js`, origin `png`: the frame's `ubl-offset`, or the page's
  corner). Until 2026-10-06 the render had only those and used them for everything, so a render and the
  export of a drawing were a unit or more apart (`history/README.md`, "One picture, one origin");
- **scale:** each figure fitted to the page width (5.7 in), or kept at its natural size where it is
  narrower: 12 px text prints at 9 pt at natural size, smaller in a wide figure ("Questions for the
  TC", B3);
- **draw.io's code is pinned** (`tools/drawio-version.json`), so an export can be made again the
  same ("Upgrading draw.io");
- **font:** Helvetica, draw.io's own, named in the SVG as `Helvetica, Arial, "Liberation Sans",
  sans-serif` (the same widths), none embedded. If ISO requires its own (Cambria: "Questions for
  the TC", B2), it is set at export time for the ISO deliverables only, never in the drawings
  (`history/README.md`, "Decided for that export").

## Upgrading draw.io

`python3 tools/drawio_upgrade.py --check` says where draw.io is: the pin
(`tools/drawio-version.json`), the newest release that can be pinned (the
`VERSION` on jgraph/drawio's `dev` branch, if its tag has a viewer; the GitHub
API is not needed), and the live version of app.diagrams.net, the editor people
use, which can be ahead of every tag. Exit 1: a newer release can be pinned.

`python3 tools/drawio_upgrade.py [--to <version>] [--out <dir>]` then exports
all 96 drawings with the pin and with the candidate and compares, per figure,
the SVG (but for the version in its comment), both PNGs and the viewer's render
of the drawing's picture at the baseline's scale, pixel for pixel; where pixels differ it writes a
red/blue image. It ends in `VERDICT: SAFE` (nothing changed, exit 0) or
`VERDICT: REVIEW` (exit 1, with what differs). It takes about 4 minutes, needs
Node with playwright and Python with numpy and Pillow, and never changes the pin
or the baseline. Run it from a session as it is; the report says what to do.

`python3 tools/drawio_upgrade.py --editor` is the other half: what the editor does
to a drawing. It opens each drawing in the live editor (embed.diagrams.net in
headless Chromium, through `tools/drawio_editor_roundtrip.js`: the newest
version, which can be ahead of every tag), saves it again, and compares what
came back with what went in: every cell (attributes, style, geometry as numbers,
place in its parent's stacking order) and the render. About 5 minutes. It needs
the proxy's CA in the browser's trust store, once per environment. The environment may have
put it there already: `certutil -d sql:$HOME/.pki/nssdb -L` then lists `ccr-agent-proxy` and
`ccr-agent-proxy-2`. If not (`apt-get install libnss3-tools` for `certutil`), import both
certificates of `/root/.ccr/agent-proxy-ca.crt` (`certutil -A` takes only the first of a
file; do not run `-N` on an existing database, it hangs):

```sh
csplit -s -z -f /tmp/proxy-ca- /root/.ccr/agent-proxy-ca.crt '/BEGIN CERTIFICATE/' '{*}'
i=0; for f in /tmp/proxy-ca-*; do i=$((i + 1))
  certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n ccr-agent-proxy$([ $i -gt 1 ] && echo -$i) -i $f; done
```

To move: change `version` in `tools/drawio-version.json`; export all again
(`to-ubl-repo/`: every SVG changes by the version in its comment, which names
the release it was made with); `python3 tools/check_svg.py to-ubl-repo`; and,
if the renders changed, make a new baseline from them, so that
`drawio_baseline.py compare` does not report the version as a change of every
drawing.

What was tried with each version (31.5.3 to 32.2.0, the pin since 2026-10-06; the live editor 32.1.0 and 32.2.0), and how the
drawings came to be in the editor's form: `history/README.md`, "draw.io upgrades tried".

**draw.io itself** (checked 2026-10-06): the editor's code is Apache 2.0 and, at the pinned release,
its source is public in [jgraph/drawio](https://github.com/jgraph/drawio) (it was not for a while:
a "modified Apache" licence from 24.7.8, the sources gone from the repository at 26.0.0); the
[desktop app](https://github.com/jgraph/drawio-desktop) is GPL v3 and works offline. draw.io Ltd
(formerly JGraph) and draw.io AG own it and take no outside contributions. A licence change binds
only later releases: the pinned one stays usable, and can be forked or hosted anywhere. Should
draw.io go, the drawings are plain XML of mxGraph's model, which
[maxGraph](https://github.com/maxGraph/maxGraph) (Apache 2.0) still reads; each holds its model as
properties, and every figure is also a standard SVG. The one thing taken from GitHub is the pinned
viewer, fetched into a local cache (`~/.cache/ubl-drawio-viewer`), not kept here: were that tag
gone, an export could not be made again the same, but the drawings and the exports stay.

### Before a pull request

Whatever changed (a drawing, a tool, the pin), in this order, from the repository's
root (Node with playwright, Python with numpy and Pillow, and Chromium as
`tools/export_drawio.js` says):

1. **A drawing edited, or written by a script:** it is in the editor's form (saved
   from draw.io it is; a script's file: `python3 tools/drawio_format.py <file>`).
2. `python3 tools/check_drawio.py diagrams/*/*.drawio`: conventions, and the form.
3. `python3 tools/drawio_baseline.py compare baselines/2026-10-06`: only the
   drawings edited may differ, and each says how. The baseline itself is history:
   it is not edited once its day is over; a new baseline is a new dated folder,
   made only when asked for.
4. `NODE_PATH=$(npm root -g) node tools/export_drawio.js to-ubl-repo diagrams/*/*.drawio`
   and `python3 tools/check_svg.py to-ubl-repo`: every figure `ok`. In another
   container than the one the PNGs were made in, export only the figures edited (see
   "Images made from the drawings"). The export goes
   in the same commit as the drawing (the check fails on a stale one), and
   nothing in `to-ubl-repo/` is edited by hand. **A tool or a picture changed**
   (in `tools/`, `illustrations/parts/`, the pin): copy it again into
   `to-ubl-repo/utilities/artwork/` (the check fails on a copy behind):
   `cp tools/{export_drawio.js,drawio_picture.js,check_svg.py,drawio-version.json,check_drawio.py,drawio_format.py,ubl-library.xml,embed_parts.py} to-ubl-repo/utilities/artwork/`
   and `cp illustrations/parts/*.svg to-ubl-repo/utilities/artwork/parts/`.
5. `python3 tools/drawio_upgrade.py --check`: the pin is the newest tag, or it
   says so. Do this at the start of a session and before anything goes to the UBL
   repository. A newer tag: `python3 tools/drawio_upgrade.py` (exports and renders
   with both, ends in `SAFE` or `REVIEW`), then `python3 tools/drawio_upgrade.py --editor`
   (the live editor opens and saves every drawing; needs the proxy's CA in the
   browser's trust store, above). `SAFE` twice: change `version` in
   `tools/drawio-version.json`, export all again and copy the pin into
   `to-ubl-repo/utilities/artwork/` (step 4), and expect only the
   version in each SVG's comment to change. `REVIEW`: look at the diff images, and
   do not move the pin until what differs is understood.
6. A pin move is a pull request of its own, with the report's numbers in it, and
   the account in `history/README.md` ("draw.io upgrades tried") brought up to date. The live editor can be
   ahead of every tag: that is said by `--check`, and is not a reason to wait.

## History: `history/`

How the drawings came to be is kept whole in `history/`: its README is the index (the path from the
UBL PNGs to these drawings, step by step, and the measurements and trials behind the rules above);
`history/former-README.md` is this repository's README until 2026-09-29.

## Questions for the TC

Every question this work leaves for the TC, in one place (collected 2026-10-06). Elsewhere
in this repository a question is only pointed to, by its number here. A was to be settled
before the commit to the UBL repository (all answered, 2026-10-06); B is how UBL publishes the
figures; C is BPMN and the lost originals; D is what the diagrams say, for when they are next
revised.

### A. Before the commit to the UBL repository

**A1. Which branch?** *Answered 2026-10-06 by the UBL editor:* `ubl-2.6`; everything goes there.
The SVGs are taken from it separately for ISO when they are needed, in a submission of their own
(B1). This
work was read from `ubl-2.5` at `3d81e8a` (CSD03); `art/`, `htmlart/` and `images/` are the same
on `ubl-2.5-os`, `ubl-2.5-iso` and `ubl-2.6` as there (checked 2026-10-06), so the figures' files
fit any of them; `build-common.sh` and `build.yml` are another version on the 2.5 branches than
on `ubl-2.6`, where the build step was tested.

**A2. Remove 5 more files from `images/`?** *Answered 2026-10-06 by the UBL editor:* yes, all
five, as they would confuse; the commit removes them with the 3 older sources, before it is merged
("Images made from the drawings"). Found 2026-10-06: none is a source of the 96
under its name, and `UBL.xml` uses none; all came with the TC's initial load of 2021-05-15.
Two are older sources of our figures, as the 3 the commit removes ("Images made from the
drawings"): `UBL-2.3-GoodsCertificateProcess.svg` (Goods Certificate Export, under its
former name: the same words) and `UBL-2.3-RequestForProofOfReexportationProcess-old.svg` (an
earlier, smaller version of that figure). Three are of figures UBL does not have, none ever
with a PNG in `art/` on any branch: `UBL-2.2-Tender-Contract.svg` (an earlier, smaller Tender
Contract, 7 labels; `-Pre` and `-Post` have its place), and
`UBL-2.2-Tender-TenderingProcess.svg` with `UBL-2.3-Tender-TenderingProcess.drawio` (one
overview of the tendering process, in both). The UBL repository's history keeps them.

**A3. How is a figure edited once it is in the UBL repository?** *Answered 2026-10-06 by the UBL
editor:* the UBL repository becomes the source: a figure is edited in its `images/<figure>.drawio`,
and its build renders the drawings into `images/<figure>.svg`, `art/` and `htmlart/` before Ant,
so that what comes after stays the same; the rendered files are committed too. The tools go with
the drawings (`utilities/artwork/`), and the README's "Artwork" (draw.io's PNG export by hand, the
`htmlart/` copy scaled in GIMP) points to their guide ("In the UBL repository: the build renders
the drawings").

**A4. May the illustrations' clip art be published as it is?** *Answered 2026-10-06 by the UBL
editor:* yes; these pictures have been in UBL's figures for years. The published SVGs carry it
as vector art.

- *The CPFR step figures:* the people were traced from copies of the Visio stencil's own
  pictures (the originals are lost); they are drawn anew, but follow those drawings
  closely. If that is not acceptable, the people would have to be drawn freely
  (pictograms). The document, the clipboard, the desk's things and the stack of documents
  are this work's own drawing (`history/illustrations/cpfr/README.md`).
- *The Fulfilment figures:* 7 parts (the Supplier, the Buyer, the forwarder, Supplier B,
  Buyer B, two parcels) are the clip art of Tim McGrath's deck, converted (WMF to SVG), and
  the document is traced from the deck's picture; the pallet is this work's own drawing
  (the deck has a stock photo) (`history/illustrations/README.md`).

**A5. Remove `art/UBL-2.0-BillingwithCreditNoteProcess.png`?** *Answered 2026-10-06 by the UBL
editor:* yes; the commit removes it with A2's files ("Images made from the drawings"). It is in
the UBL repository's
`art/` (not in `htmlart/`) and not used: `UBL.xml` does not cite it. If the TC keeps it, it
is a UML activity diagram and would be the 79th drawing: the pipeline of `history/` does
not need to be run again for it, the drawing is made like the others
(`history/drawio-writer/README.md`; `history/remaining-figures.md`).

### B. How UBL publishes the figures (after the commit)

**B1. Should the published specification show the SVGs instead of the PNGs?** *Answered
2026-10-06 by the UBL editor:* no, not now: `UBL.xml` keeps pointing at `art/<figure>.png`, so the
HTML and PDF that the build and Réalta make show the PNGs, as before, and the commit changes nothing
in how UBL is published. The SVGs go to ISO in a submission of their own, apart from the normal
one, taken from `ubl-2.6` (A1). Showing the SVGs in the specification (sharp at any zoom, its text
selectable and searchable) would change every output, and each step of the build would have to
handle SVG well (Réalta, the DocBook stylesheets, the PDF engine, browsers; and the font, B2): a
question for later. `ubl-2.4-os-iso-pub` did switch, for ISO (`8801d64`, 2024-11-12, "Change PNGs
to SVGs for ISO use": its `UBL.xml` points at `art/*.svg`), but those 95 SVGs, made in Inkscape,
only wrap the PNG: each holds it as an embedded image, with no text and no vector drawing.

**B2. Does ISO require its own font in graphics?** *Answered 2026-10-06 by the UBL editor:* no
change now; if ISO requires it in the future, it is handled then. UBL goes to ISO as a PAS
submission, directly from OASIS. Should it come to that, the font is set for the ISO SVGs only, at
export time, never in the drawings (`history/README.md`, "If ISO requires its own font"). What
ISO's guidelines for drafts say (checked 2026-10-06, the version of 2022-04;
[a copy at JSA](https://webdesk.jsa.or.jp/pdf/dev/md_5638.pdf); ISO's own current one, 2025-02,
[RequirementsDrafts.pdf](https://www.iso.org/files/live/sites/isoorg/files/developing_standards/docs/en/RequirementsDrafts.pdf),
refused the download): figures in Cambria, but "in figures which are not technical drawings other
fonts are permissible if the figures are clear and the font used within them is consistent
throughout a document"; SVG among the formats recommended; text editable, not outlined; no
colour that carries meaning; words allowed in flowcharts; text at 10 pt, or smaller in the same
ratio (8 pt, say: B3).

**B3. Even out the printed text size?** *Answered 2026-10-06 by the UBL editor:* no change now;
no figure is redrawn to even it out. (This answer first said that the figures print as they do
today, fitted to the page width as UBL's PNGs always were: they do not all, below.) Every figure is
drawn with one text size, draw.io's 12 pt (12 px), and printed by one rule: fitted to the page width
(5.7 in), or kept at its natural size where it is narrower. At natural size its text
prints at 9 pt, and a figure twice the page's width prints it at 4.5 pt. Of the 87 drawn at 12 px
(2026-10-06): 18 at 9 pt, 22 at 7-8.9 pt, 34 at 5-6.9 pt, 13 at 3.5-4.9 pt; the smallest are
Fulfilment Receipt Advice (3.5 pt), Fulfilment Despatch Advice and Intermodal Freight Management
(3.7 pt) and Procurement 1.0 (3.9 pt); the export reports it per figure. It shows most in the HTML,
whose 750 px bitmap cannot be zoomed: 9 pt text is about 16 px high there, 3.5 pt about 6 px. A way
to even it out, for when a wide figure is revised anyway (D): draw it narrower, so that it is
scaled less. Pre-award and Procurement are the TC's drawings at 3425 px wide (text 40-70 px, 8 px
lines, printing at about 5-8 and 6-10 pt), not at the others' 12 px convention; a version rescaled
to 0.3 exists as an experiment and could be adopted then (`history/group-a/README.md`,
"`redrawn/`").

*Measured 2026-10-06, the rule kept 2026-10-07 by the UBL editor:* UBL's PNGs did not all follow
that rule. In a test build of `ubl-2.6` with the figures rendered from the drawings (a fork of the
UBL repository, `kduvekot/ubl`, branch `ubl-2.6-artwork`), 17 of the 96 figures print at another
width than in UBL 2.6 today; the other 79 print within 2 % of it. The editor keeps the rule.

- 6 print larger, their PNGs having been made smaller than the rule gives: Export Customs
  Declaration (3.81 to 5.71 in wide, its text 5.9 to 8.9 pt; the PNG was 300 dpi), Waste
  Notification and Waste Movement (4.17 to 5.34 in, 7.0 to 9.0 pt), Tender Contract Pre-signing
  and Post-signing (5.37 to 5.63 in, 8.6 to 9.0 pt) and Procurement (4.61 to 5.71 in; the TC's
  drawing, above).
- 11 print 2-9 % narrower, at their natural size, where their PNGs were stretched to the page
  width (text 9.2-9.9 pt, now 9 pt): Contract Information Notification, Unsubscribe from
  Procedure, Submission of Tenders, Award Notification, Guarantee Deposit, Invoicing for Vendor
  Managed Inventory, Transfer of Base Item Catalogue (CRP), Invoicing for Cyclic Replenishment
  Program, Transfer of Base Article Catalogue (ROCD), the Generic Freight Management Process (IMFM)
  and Open-edi Overview.

The specification's PDF grows by one page (209 to 210; the ISO PDF 196 to 198), mostly through
Waste Notification, Waste Movement and Export Customs Declaration, which together add about 3.6 in
on its pages 67 to 71.

### C. BPMN, and the lost originals

**C1. Should the 78 UML activity diagrams become BPMN too?** *Answered 2026-10-06 by the UBL
editor:* BPMN is strictly a possible option for the distant future: not for the 78, and no
official BPMN 2.0 file for Business Information or Ordering either (C3). The draw.io drawings are
the sources. Their drawings use BPMN pools and lanes; what an official BPMN file would take, should
the option be taken: `history/group-a/README.md`, "Future session". The two phase maps stay draw.io.

**C2. Business Information's envelopes, in its BPMN version.** *2026-10-06:* only if that
version is ever made (C1: a possible option for the distant future). A message flow joins two
elements directly; the envelope can become a message event or a send/receive task (which
changes what the figure says) or be dropped. Its message flows that end at an end event (not
a message end event) need the same decision.

**C3. If Ordering's `.bpmn` stays lost, is a reconstruction acceptable?** *Answered 2026-10-06 by
the UBL editor:* no longer relevant: Ordering's draw.io BPMN drawing, made 2026-10-06 with every
element linked as in a BPMN model, is its source, and enough; no `.bpmn` is written for it. The
original, `UBL-2.3-OrderingProcess.bpmn`, attached to the `ubl` list's mail of 2019-05-07
("UBL-171 - BPMN diagram + SVG"), is not found yet; if it turns up (C4), it is held against the
drawing (`history/group-a/README.md`).

**C4. Can someone with a browser search the `ubl` list's archive?** *2026-10-06:* ongoing, and no
longer critical (C3). The archives
(`lists.oasis-open.org`, `lists-archive.oasis-open.org`) refuse a script. Wanted: the
2019-05-07 attachment above, and the posts of 2016-2020 around the figures' creation (UBL
2.2: the IMFM, Open-edi, Schema Dependencies and UDT/QDT figures; UBL 2.3: Model
Realization), where an attachment may be a source. Worth an hour: search for `svg`,
`visio`, `vsd`, `png`, `bpmn` and the figure names. A find goes in
`history/<group>/sources/` (`history/remaining-figures.md`, `history/group-a/README.md`).

### D. What the diagrams say, for their next revision

The drawings stay faithful to the artwork. These are the points where the artwork itself may
be wrong, raised in the review of the figures with the TC (2026-09, the questions `q7` to
`q15`: `history/docs/artwork-conversion-notes.md`, §11 and §16), kept for when the diagrams
themselves are next revised. Figure numbers are as in that review.

**Decided 2026-10-06 by the UBL editor:** a change to what an existing diagram says is future
work, made in the UBL repository once its drawings are the source, and not part of this
transition to draw.io sources. The transition changes no diagram's content: every figure says what
it said in UBL 2.5. D1 too, which the TC wants fixed in UBL 2.6, comes after it.

- **D1. Billing with Debit Note: the supplier's guards** (decided: to be fixed in UBL 2.6, after
  the transition; to confirm: the new guard). The supplier's Reconcile Charges sends [initial charges or under
  charged] to *Raise Invoice* and [under charged] to *Raise Debit Note*: the two guards
  overlap, so "under charged" does not say which way to go (on the credit-note twin the
  second branch is [over charged]). The fault is new in 2.5: UBL 2.0 to 2.4 draw a different
  process, the Customer raising the Debit Note when [over charged] (os-UBL-2.4
  `art/UBL-2.0-BillingwithDebitNoteProcess.png`, the same drawing since 2.1, and in 2.0 as a
  JPEG), with the Supplier's diamond sending only [initial charges or under charged] to
  *Raise Invoice*. The 2.5 figure moves the Debit Note to the Supplier (the text after it now
  says the Supplier specifies the tax requirements) and was redrawn from the credit-note
  figure, keeping that guard; most likely the invoice branch should read [initial charges].
  The figure is published unchanged in the OASIS Standard (os-UBL-2.5, 12 August 2026, the
  same guards; the file there is a different export of the same drawing). The TC
  (2026-09-28): to be fixed in UBL 2.6. (Approved Errata, TC Process
  2.9, are limited to corrections that are not a Material Change, which a changed guard in a
  process diagram arguably is.)
- **D2. Update Catalogue Pricing, Create Catalogue, Update Catalogue Item Specification:** on
  all three a document runs straight into an end with no step that receives it, and the
  preparing step has two ways in (a start or a loop, and the fork) where "either" is meant -
  in UML two ways into a step mean "both"; a merge diamond would say it.
- **D3. Certification of Origin:** *Receive Response* has two ways out with no decision; the
  accepted outcomes (*Endorse CoO*) never reach the Exporter.
- **D4. Fig 37, Punch-out Sourcing** (`q7`, raised 2026-09-27):
  - *Who builds the basket?* The artwork puts *Build shopping basket* in the Seller Supplier
    Party's column. But in punch-out it is the Originator who browses the catalogue and
    fills the basket, on the Seller's system. UBL.xml says so itself: "The Originators leave
    ... their system and interact with the Seller's catalogue to locate and order products".
    The column may be showing whose system it is rather than who acts. A revised diagram
    could say this plainly, for instance with the action in the Originator's column and the
    Seller's catalogue application named as where it happens.
  - *UBL.xml's text reads "Seller" where "Originator" seems meant.* It says punch-out lets an
    Originator access a Seller's catalogue application "from within the Seller's own
    procurement application", which by the rest of the paragraph should be the Originator's
    own. Whose procurement application "transparently gathers pertinent information" is
    unclear for the same reason.
- **D5. Fig 14, CPFR Exception Monitor** (`q9`): redraw the connector from the Buyer's *Send
  Exception* to *Exception Notification (positive)* like its mirror on the Seller's side. A
  layout matter, for the session that re-lays diagrams.
- **D6. Goods Item Passport figures** (found 2026-09-27): the artwork writes the name both "GoodsItem" and
  "Goodsitem". The model follows the artwork in each place; a revision could make them all
  "GoodsItem".
- **D7. Utility Billing** (`q12`): drop "(from Business Processes)" in a redraw: the package
  means nothing to a reader of the specification; if the link matters, refer to the billing
  section instead.
- **D8. Documents across an intermediate lane** (`q14`): the artwork puts such a box next to
  the receiver 5 times and next to the sender 4 times. A redraw could agree a convention -
  simplest, always on the divider next to the receiver.
- **D9. Freight Status Reporting** (`q15`): "Receiver Party" is a questionable name for a
  party that both receives a request and sends the status report; and the divider marking
  off the self-initiated start could go - in BPMN it would be a timer start inside the
  Receiver Party's lane.
- **D10. Waste Movement and Waste Notification** (`q15`): the column titles read
  "Senderparty" and "ReceiverParty"; UBL.xml says "Sender Party" and "Receiver Party".
- **D11. CPFR phase boxes:** size each to its steps and the words that belong to it, with the
  same margin on every figure (Fig 9 is far too wide; Fig 7's "Retail Event Accepted ?"
  pokes out of its box).
- **D12. Decisions** (completeness sweep): guard every branch and give every diamond its question. Fig C.1,
  Certification of Origin and Fulfilment Despatch Advice can take their guards from the step
  each branch leads to; Create Catalogue's diamond can say "Respond to Request" as its Update
  Catalogue siblings do; the 2.5 billing figures' unlabelled branch out of *Reconcile
  Charges* can read [otherwise] or [dispute charges].
- **D13. Intermodal Freight Management:** split *Provide Transportation Network Information*
  into one step per phase (Planning, Execution).
- **D14. Party names:** one style across the figures, and one name per role (Buyer / Buyer
  Party / Originator Customer Party ...), checked against the party roles UBL.xml gives for
  each document.
- **D15. Self Billing** (text sweep): the choice after *Raise Self Billed Invoice* - accepted, or a reply
  comes - drawn as a branch, in BPMN an event-based gateway: an Application Response, a
  Credit Note, or no reply meaning the charges are accepted.
- **D16. Tender Contract Information Preparation** (text sweep): "Publish Official Journal" would read
  "Publish in Official Journal"; and the box says *Prior Information Notice* where both
  steps call it a *Simplified Notice*.
- **D17. Ends and starts** (actions sweep): an end after each of the 19 steps a path stops at, and a start
  before the 4 it begins at. On Fulfilment Despatch Advice a goods flow from *Despatch Order
  Item(s)* to *Receive Order Item(s)* (as in the notes' §11.6), and on Fig C.1 one into
  *receive goods*; on Utility Billing connect *Report usage*, for instance alongside *Raise
  Invoice*.
- **D18. Fulfilment with Despatch Advice:** the Despatch Party lane has a start event labelled
  "From Order", the Delivery Party lane has none. The TC: this diagram needs proper cleaning
  up (notes §11.4).
- **D19. Tender Award Notification** (documents sweep): draw the two notifications as two exchanges, or with a
  decision (won / not won), rather than two boxes on one line (the TC: a decision diamond,
  and arguably an extra lane for the awarded/unawarded split; notes §11.4).
- **D20. Tender Contract Pre and Post:** *Prior exchange of public keys* appears in both lanes,
  joined by a dashed line with an arrowhead at each end: a mutual precondition, not a flow.
  It needs additional work in the BPMN conversion (notes §11.4).
- **D21. CPFR two-way documents** (documents sweep): draw one box per direction, or say plainly that either
  party may send it to the other.
- **D22. Document names** (documents sweep): use UBL's document type names as they are ("Import Customs
  Declaration", "Proof Of Reexportation Request", "Digital Capability", "Trade Item Location
  Profile"), one spelling of "GoodsItem"; and on Initiate Freight Management "Send Bill of
  Lading to Consignor" and "Send Waybill to Consignor" send to the Consignee as well.
- **D23. Export Customs Declaration** (documents sweep): the stamped declaration is returned from the Customs
  Party to the Exporter; UBL lists the document as sent by the Exporter only. Either the
  roles in UBL.xml grow a second direction, or the return is drawn as a different document.
- **D24. Tender Guarantee Deposit** (`q8`): obtaining the guarantee from a financial
  institution is shown as one step with no document. Should UBL ever cover that exchange,
  the financial institution would become a party with its own column.

## Open work

- **The TC's answers** ("Questions for the TC"): D, changes to what the diagrams say: future
  work, not part of this transition (D1, for UBL 2.6, after it). A and B
  are answered, and C: BPMN is a possible option for the distant future (C1, C2), Ordering's
  drawing is enough (C3), and the archive search goes on (C4).
- **The commit to the UBL repository:** `to-ubl-repo/` copied over a clone of `ubl-2.6` (A1),
  9 files removed (A2: the 3 older sources and the 5 more files in `images/`; A5: the unused PNG
  in `art/`), and three of its files edited with it, `build-common.sh`,
  `.github/workflows/build.yml` and its README's "Artwork" (A3; "In the UBL repository: the build
  renders the drawings"). Its message names each file removed and what it was, and says that
  Group A's three drawings change only in form, that Ordering's bpmn-js SVG is replaced by its
  draw.io drawing and that drawing's export, that the PNGs are replaced by print PNGs in black and
  white (grey: the illustrations, Business Information and three of Group C), and that the build
  renders them from the drawings ("Images made from the drawings"; `history/remaining-figures.md`,
  "Before the UBL repository gets any of it"). Both commits are made, by the UBL editor, on
  `kduvekot/ubl` branch `ubl-2.6-artwork`, and tested on GitHub there ("In the UBL repository: the
  build renders the drawings"). Still to do: run the commits as now (with the problems file) there
  once more, then the pull request to `ubl-2.6`, by the UBL editor. The UBL repository's workflow
  builds on a push only, not on a pull request, so the merge is its first build there.
- **A second commit to `ubl-2.6`, of its own:** the figures commented out in `UBL.xml` removed
  (one line; "Images made from the drawings"); made, with the first, on `ubl-2.6-artwork`.
- **The original BPMN 2.0 XML of the Ordering Process** (`UBL-2.3-OrderingProcess.bpmn`, attached
  to the `ubl` list's mail of 2019-05-07, UBL-171): not found yet; the search goes on, no longer
  critical (C3, C4). Still to look in: the Sent folder of that mail, other list members' mailboxes
  (Ken Holman, Kenneth Bengtsson), the 2019 download folders and backups, bpmn.io's local
  storage in a browser profile of 2019, and the list archive, which refuses a script (C4).
  Ordering's source is its draw.io BPMN drawing, made from the bpmn-js SVG (2026-10-06),
  every element linked as in a BPMN model ("Ordering, a BPMN drawing"). A find goes in
  `history/group-a/sources/` and is held against that drawing.
- **The draw.io desktop app:** this README says to edit in it or in diagrams.net, but
  the drawings are tried in the web editor only (all 96 opened and saved again in the
  live editor, unchanged). Open and save one in the desktop app, and hold the file
  against the drawing with `python3 tools/drawio_format.py --diff` and
  `tools/check_drawio.py`: that shows whether the desktop app writes them the same.
- **Smaller:** the export's report of the size text prints at assumes 12 px text, which
  is wrong for Pre-award and Procurement (`history/group-a/README.md`);
  `history/group-c/lib_c.py` does not allow for draw.io multiplying `dashPattern` by the
  stroke width: fix it before a fifth figure is drawn with it (`history/group-c/README.md`).
- **The CPFR step figures:** what is still open on them (the shading of the handshake
  people) is in `history/illustrations/cpfr/README.md` ("Open work").
