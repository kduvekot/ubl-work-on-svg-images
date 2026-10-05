# Group A: the four figures that had a source

Done 2026-10-05. Four of the UBL repository's other 12 figures
(`history/remaining-figures.md`) already had a source in its `images/`: **the TC's own
files, which are the sources of the PNGs it publishes**. They are the figures' sources here
too, at the place and under the name of the others, exported to `to-ubl-repo/` like the
rest: **89 figures now**.

| figure | the TC's source | here | notation |
|---|---|---|---|
| `UBL-2.3-Pre-awardProcess` | `images/UBL-2.3-Pre-awardProcess.drawio` (draw.io 13.0.3, 2020) | `diagrams/<figure>/<figure>.drawio` | phase map |
| `UBL-2.3-ProcurementProcess` | `images/UBL-2.3-ProcurementProcess.drawio` (draw.io 13.0.3, 2020) | `diagrams/<figure>/<figure>.drawio` | phase map |
| `UBL-2.4-BusinessInformation` | `images/UBL-2.4-BusinessInformation.drawio` (draw.io 20.8.4, 2023-02-06, Kees Duvekot) | `diagrams/<figure>/<figure>.drawio` | BPMN-style |
| `UBL-2.3-OrderingProcess` | `images/UBL-2.3-OrderingProcess.svg` (bpmn.io / bpmn-js, 2019) | `diagrams/<figure>/<figure>.svg`, as it is | BPMN |

The files as the UBL repository has them are in `sources/` (`ubl-2.5` at `3d81e8a`; the
same on `main`, `ubl-2.4-os`, `ubl-2.3-os-iso`, `review` and `tsc-ubl-2.5-experimental`).

## They are the sources of the current PNGs (checked 2026-10-05)

Each source drawn (the draw.io files by the pinned draw.io; Ordering's SVG by Chromium), put where
the PNG has its ink, and held against `art/<figure>.png` of the UBL repository
(`compare_png.py`: the share of ink with no ink of the other within 4 px, at the PNG's size):

| figure | PNG ink not in the render | render ink not in the PNG |
|---|---|---|
| Pre-award | 0.07 % | 0.07 % |
| Procurement | 0.00 % (with its stray line taken out, below) | 0.00 % |
| Ordering | 0.00 % | 0.00 % |
| Business Information | 0.65 % | 13.2 % (the 1 bit print draws its 1 px lines 2 px wide) |

The git history says the same: the sources and their PNGs arrived together (Ken Holman's
"Initial load of files - copy of 2.3 CSD05", 2021-05-15, for three; Kees Duvekot's two
commits of 2023-02-06 for Business Information).

## What `adopt_originals.py` does

- **The three `.drawio` files:** the TC's drawing, with only what this repository's tools
  need, nothing of what it shows changed. Uncompressed, and in the form draw.io's editor
  writes (`tools/drawio_format.py`; the file's own `host`, `agent`, page and window stay);
  one element carries `ubl-notation` (`phase-map` or `bpmn`), the sign that the figure is not
  a UML activity diagram. **Procurement only:** a stray dashed line, 4000 px right of
  the figure and not in its PNG (cell `H2ljDLKrGr7yGGcZbY4q-120`), is taken out: it made the
  export's page three times too wide.
- **Ordering:** its source is a bpmn-js SVG, not a drawing: it is kept as it is, byte for byte
  (`diagrams/UBL-2.3-OrderingProcess/UBL-2.3-OrderingProcess.svg`), published as it is, and the
  PNGs are rendered from it (`tools/export_drawio.js` takes an `.svg`; `tools/check_svg.py` knows
  such a figure: the SVG is the source's, vector, words as text).
- **Not done to them, on purpose:** no rescale (below), no ids or kinds (`ubl-kind`) as in the
  78 diagrams, no change of colour, no redraw. `tools/check_drawio.py` checks them for the
  form and for what it can without kinds, and says so as a warning.

## What is as the TC made it, and may be for them to decide

- **Scale.** Pre-award and Procurement are drawn 3425 px wide with 60, 70 and 40 px text and
  8 px lines (the others: natural scale, 12 px text, 1 and 2 px lines). Fitted to the page they
  print as the PNGs do (the captions of Pre-award at 4.8 pt); the export's report line
  ("text 1.4 pt") assumes the others' 12 px and is wrong for these two. A rescale is a change to
  the TC's drawing; it was made in an experiment (`redrawn/`, below) at 0.3 and could be adopted.
- **Business Information's grey bars** (`#C0C0C0`, the foot of each task): in the SVG and the
  web PNG; the print PNG is black and white, where they are white. The drawings of the others
  are black and white only.
- **Business Information's envelopes** on the message flows are draw.io shapes (`shape=message`):
  BPMN 2.0 has no envelope on a message flow (below).
- **Procurement's and Pre-award's shapes** are loose lines and groups (a phase's outline is five
  lines, a list of documents two), as drawn in 2020: they edit badly.
- **None of the BPMN-style drawings is an official BPMN file** (next section).

## Future session: real BPMN 2.0 files for the BPMN figures

Said by the editor, Kees Duvekot (2026-10-05): for BPMN diagrams it is **very important that the
sources are official BPMN 2.0 files** (the OMG standard, ISO/IEC 19510:2013), not drawings in BPMN
style. That is a different requirement and its own session, not done here.

- **Which:** Ordering and Business Information. Pre-award and Procurement are phase maps
  with no BPMN semantics (chevrons, a milestone): they stay draw.io. (Whether the 78 UML activity
  diagrams, whose drawings use BPMN pools and lanes, should be BPMN too is for the TC.)
- **What an official file is:** BPMN 2.0.2 XML: a `collaboration` with participants and message
  flows, a `process` for each participant, with tasks, gateways, events and sequence flows, and a
  `BPMNDiagram` (BPMN DI) with every shape's and edge's place and size and the labels. Valid against
  OMG's normative XSDs (`BPMN20.xsd`, `Semantic.xsd`, `BPMNDI.xsd`, `DI.xsd`, `DC.xsd` at
  <https://www.omg.org/spec/BPMN/20100501/>, the specification at <https://www.omg.org/spec/BPMN/2.0.2/PDF>;
  `xmllint` is installed here), and opening in bpmn.io (bpmn-js, `bpmn-moddle` on npm) and a second
  modeler.
- **Ordering:** the real source is `UBL-2.3-OrderingProcess.bpmn`, attached to the `ubl` list's mail of
  2019-05-07 ("UBL-171 - BPMN diagram + SVG", see below). If it is found: validate it, render
  the SVG and PNGs from it with bpmn-js (the tool that made the original), and check them against the
  PNG as `compare_png.py` does. If not: write it from the SVG, which carries the BPMN ids
  (`Task_1bnlp2b`, `MessageFlow_0w3w0y5`, ...), the places and the bends of every element, as
  `redrawn/build_ordering.py` already reads them.
- **Business Information:** a draw.io drawing in BPMN style, made in draw.io 20.8.4, so no BPMN
  XML exists; write it from the drawing. Its **envelopes** need a decision: a message flow joins two
  elements directly; the envelope can become a message event or a send/receive task (which changes
  what the figure says) or be dropped. Its message flows that end at an end event (not a message end
  event) need the same look.
- **Then:** the `.bpmn` is the source, the SVG and PNGs are exports of it (as the `.drawio` is for the
  rest), `tools/check_svg.py` and a new check (XSD validity) apply, and the README's section on
  sources says so.

## Where the originals might still be (searched 2026-10-05)

- **UBL repository, all 31 branches:** the four above, nothing else, and no `.bpmn` file.
- **docs.oasis-open.org** (`UBL-2.x/art/`, the release directories): the PNGs only.
- **The UBL JIRA** (issues.oasis-open.org; its REST API answers): UBL-171 ("Accepted order are
  canceled") is where the Ordering diagram was redrawn in 2019. No attachment ("we can not attach
  documents to Jira Issues directly"), and Ken Holman says on 2019-05-06 that the sources of the original
  swim-lane diagrams are not available. No issue mentions draw.io, Visio or the other figures' sources.
- **The `ubl` mailing list, 2019-05-07,** "UBL-171 - BPMN diagram + SVG"
  (<https://lists.oasis-open.org/archives/ubl/201905/msg00011.html>, also on groups.oasis-open.org):
  **attaches `UBL-2.3-OrderingProcess.bpmn`**, the BPMN XML made in bpmn.io, and the SVG. The
  attachments could not be fetched from here: lists.oasis-open.org and lists-archive.oasis-open.org
  answer a script, and headless Chromium too, with Cloudflare's "verify you are not a bot" check (403),
  groups.oasis-open.org lists the attachment names only, without a link, for a visitor who is not logged
  in, and markmail.org and web.archive.org are not reachable from this environment (network policy: they
  would have to be added to the environment's allowed domains). **If the `.bpmn` is found (its author
  has it, or a TC member's mail), put it in `sources/`.**

## `redrawn/`: an experiment, not the sources

Before the originals were chosen, all four were drawn again as draw.io drawings made for this
repository: the BPMN pair as draw.io's BPMN shapes with the model's ids and kinds (Ordering from the
bpmn-js SVG, Business Information with white bars), Pre-award and Procurement rebuilt with draw.io's
own shapes at 0.3 of the TC's scale (text 12, 18, 21 px, lines 2 px; one dashed corner line per list of
documents). They matched the PNGs to 1-8 %, the originals to 0-0.07 %. Kept as a record of what a
cleaner, rescaled version looks like (`redrawn/*.drawio`, built by `redrawn/build_*.py`), in case the TC
wants the 12 px convention for these too. The scripts write beside themselves and cannot overwrite a
source.

## Run again

```sh
python3 history/group-a/adopt_originals.py            # sources/ -> diagrams/
python3 tools/check_drawio.py diagrams/UBL-2.3-*/*.drawio diagrams/UBL-2.4-BusinessInformation/*.drawio
NODE_PATH=$(npm root -g) node tools/export_drawio.js to-ubl-repo diagrams/UBL-2.3-OrderingProcess/*.svg \
    diagrams/UBL-2.3-Pre-awardProcess/*.drawio diagrams/UBL-2.3-ProcurementProcess/*.drawio diagrams/UBL-2.4-BusinessInformation/*.drawio
python3 tools/check_svg.py to-ubl-repo
python3 history/group-a/compare_png.py <ubl>/art to-ubl-repo/art <out> <figure> ...
```

After that the drawings are the source: edit them in draw.io. `adopt_originals.py` would overwrite an
edit; it is how they were adopted, and need not be run again.
