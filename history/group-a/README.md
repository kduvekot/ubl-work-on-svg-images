# Group A: the four figures that had a source

Done 2026-10-05. Four of the 12 figures of the UBL repository then still without a drawing here
(`history/remaining-figures.md`) already had a source in its `images/`: **the TC's own
files, which are the sources of the PNGs it publishes**. They are the figures' sources here
too, at the place and under the name of the others, exported to `to-ubl-repo/` like the
rest: **89 figures then**. (Ordering's, a bpmn-js SVG, was so until 2026-10-06; since then the
figure's source is a draw.io BPMN diagram made from it: "Ordering as a draw.io BPMN diagram", below.)

| figure | the TC's source | here | notation |
|---|---|---|---|
| `UBL-2.3-Pre-awardProcess` | `images/UBL-2.3-Pre-awardProcess.drawio` (draw.io 13.0.3, 2020) | `diagrams/<figure>/<figure>.drawio` | phase map |
| `UBL-2.3-ProcurementProcess` | `images/UBL-2.3-ProcurementProcess.drawio` (draw.io 13.0.3, 2020) | `diagrams/<figure>/<figure>.drawio` | phase map |
| `UBL-2.4-BusinessInformation` | `images/UBL-2.4-BusinessInformation.drawio` (draw.io 20.8.4, 2023-02-06, Kees Duvekot) | `diagrams/<figure>/<figure>.drawio` | BPMN-style |
| `UBL-2.3-OrderingProcess` | `images/UBL-2.3-OrderingProcess.svg` (bpmn.io / bpmn-js, 2019) | `diagrams/<figure>/<figure>.drawio`, redrawn from it as a draw.io BPMN diagram (2026-10-06; until then the SVG as it is) | BPMN |

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
| Ordering | 0.00 % (its draw.io drawing since 2026-10-06: 0.98 %) | 0.00 % (0.85 %) |
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
- **Ordering:** its source in the UBL repository is a bpmn-js SVG, not a drawing. Until 2026-10-06
  it was kept as it is, byte for byte, published as it is, and the PNGs rendered from it
  (`tools/export_drawio.js` takes an `.svg`; `tools/check_svg.py` knows such a figure, and both still
  do). Since then the figure's source is a draw.io BPMN diagram made from it (below), and
  `adopt_originals.py` leaves Ordering alone.
- **Not done to them, on purpose:** no rescale (below), no ids or kinds (`ubl-kind`) as in the
  78 diagrams, no change of colour, no redraw. `tools/check_drawio.py` checks them for the
  form and for what it can without kinds, and says so as a warning.

## Ordering: the SVG and the model

- **The source is a draw.io BPMN diagram, made from the SVG** (2026-10-06). The figure was drawn in
  bpmn.io, not draw.io; the UBL repository has only the SVG bpmn-js exported, and its PNG was
  rendered from that (0.00 % difference). Until 2026-10-06 that SVG was the source here too; since
  then it is the same figure redrawn as a draw.io BPMN diagram, linked as a BPMN model is
  (`diagrams/UBL-2.3-OrderingProcess/`: "Ordering as a draw.io BPMN diagram", below), so that all 96
  figures are draw.io drawings. The SVG stays in `sources/`.
- **The SVG is a picture, not the BPMN model.** It holds the BPMN ids (`Task_1bnlp2b`,
  `MessageFlow_0w3w0y5`, ...) and the places, bends and styles of every element, but no `collaboration`,
  `process`, `sourceRef` or `targetRef`: which task a flow joins, and what kind of flow it is, are not
  in it. The drawing has them, inferred from the SVG and checked (below), and is edited in draw.io as
  the other figures are; no official BPMN file is written for it (decided 2026-10-06: the drawing is
  enough; README, "Questions for the TC", C3).
- **The BPMN files come later** (decided 2026-10-05): not in the pull request of Group A, and not asked for before the
  real `.bpmn` is looked for once more.
- **The original `UBL-2.3-OrderingProcess.bpmn` is not found yet.** Looked for in the UBL repository
  (all branches), docs.oasis-open.org, the UBL JIRA and, from here, the `ubl` list (blocked, below); and by
  the editor, Kees Duvekot, who sent it in 2019: not found (2026-10-05). Still to try: the Sent folder of the
  2019-05-07 mail, other list members' mailboxes (Ken Holman, Kenneth Bengtsson), the 2019 download folders
  and backups, bpmn.io's local storage in the browser profile of 2019, and the list archive (README,
  "Questions for the TC", C4; ongoing, no longer critical). If it is found, it is held against the
  drawing. If not, nothing is lost: the drawing is Ordering's source, and enough (decided 2026-10-06,
  C3).

## What is as the TC made it

What the TC may want changed of it: README, "Questions for the TC", B3 (the scale) and C2 (the envelopes).

- **Scale.** Pre-award and Procurement are drawn 3425 px wide with 60, 70 and 40 px text and
  8 px lines (the others: natural scale, 12 px text, 1 and 2 px lines). Fitted to the page they
  print as the PNGs do (the captions of Pre-award at 4.8 pt); the export's report line
  ("text 1.4 pt") assumes the others' 12 px and is wrong for these two. A rescale is a change to
  the TC's drawing; it was made in an experiment (`redrawn/`, below) at 0.3 (whether to adopt it: B3).
- **Business Information's grey bars** (`#C0C0C0`, the foot of each task): kept everywhere, as in the
  UBL repository's PNG. The print PNG of this figure is therefore 8 bit grey, not 1 bit (as the
  illustrations' are, and three of Group C's since: its drawing says `ubl-art="grey"`, which
  `export_drawio.js` and `check_svg.py` read). Decided 2026-10-05 by looking at both (1 bit lost the
  grey, the rules stayed).
- **Business Information's envelopes** on the message flows are draw.io shapes (`shape=message`):
  BPMN 2.0 has no envelope on a message flow (below).
- **Procurement's and Pre-award's shapes** are loose lines and groups (a phase's outline is five
  lines, a list of documents two), as drawn in 2020: they edit badly.
- **None of the BPMN-style drawings is an official BPMN file** ("Future session", below).

## Checked in the live editor

draw.io 32.2.0 (2026-10-06, `tools/drawio_editor_roundtrip.js` and `python3 tools/drawio_upgrade.py --editor`):
the three drawings opened and saved again come back the same in every cell, style and geometry,
and exported, the same SVG and PNGs, byte for byte (`--editor` then compared renders only of the
baseline's figures, which these were not; since `baselines/2026-10-06/` it does for all 96). The file
differs in its first line only: the editor drops the `modified`, `etag` and `version` that the TC's files
carry (2020, 2023), so the first save in draw.io shows that line as changed in git. `--editor` said
`REVIEW` for it ("text: 2 lines differ") until `tools/drawio_format.py` counted those stamps among what
the editor decides itself (2026-10-06): it says `SAFE` now. Ordering's drawing: below.

## Future session: real BPMN 2.0 files for the BPMN figures

Said by the editor, Kees Duvekot (2026-10-05): for BPMN diagrams it is **very important that the
sources are official BPMN 2.0 files** (the OMG standard, ISO/IEC 19510:2013), not drawings in BPMN
style. That is a different requirement and its own session, not done here.

- **Which:** Business Information (Ordering: its draw.io BPMN drawing is enough, decided
  2026-10-06: README, "Questions for the TC", C3). Pre-award and Procurement are phase maps
  with no BPMN semantics (chevrons, a milestone): they stay draw.io. (Whether the 78 UML activity
  diagrams should be BPMN too: README, "Questions for the TC", C1.)
- **What an official file is:** BPMN 2.0.2 XML: a `collaboration` with participants and message
  flows, a `process` for each participant, with tasks, gateways, events and sequence flows, and a
  `BPMNDiagram` (BPMN DI) with every shape's and edge's place and size and the labels. Valid against
  OMG's normative XSDs (`BPMN20.xsd`, `Semantic.xsd`, `BPMNDI.xsd`, `DI.xsd`, `DC.xsd` at
  <https://www.omg.org/spec/BPMN/20100501/>, the specification at <https://www.omg.org/spec/BPMN/2.0.2/PDF>;
  `xmllint` is installed here), and opening in bpmn.io (bpmn-js, `bpmn-moddle` on npm) and a second
  modeler.
- **Ordering** (decided 2026-10-06): no `.bpmn`; its draw.io BPMN drawing
  (`diagrams/UBL-2.3-OrderingProcess/`, below) is its source, with the SVG's BPMN ids
  (`Task_1bnlp2b`, `MessageFlow_0w3w0y5`, ...), places and bends, and each flow's ends and each
  element's participant and type made explicit and checked. The original,
  `UBL-2.3-OrderingProcess.bpmn` (attached to the `ubl` list's mail of 2019-05-07, "UBL-171 - BPMN
  diagram + SVG", see below), is still looked for, no longer critically; if it is found, it is held
  against the drawing.
- **Business Information:** a draw.io drawing in BPMN style, made in draw.io 20.8.4, so no BPMN
  XML exists; write it from the drawing. Its **envelopes**, and its message flows that end at an end
  event, need a decision of the TC first: README, "Questions for the TC", C2.
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
  would have to be added to the environment's allowed domains). The search by someone with a browser:
  README, "Questions for the TC", C4. **If the `.bpmn` is found (its author has it, or a TC member's
  mail), put it in `sources/`.**

## Ordering as a draw.io BPMN diagram (2026-10-06)

Ordering's `.bpmn` is lost (above), and its SVG is a picture: which element a flow joins is said only
by where its line ends. So the figure is redrawn as a draw.io BPMN diagram, which holds the model and
is edited as the other 95 figures are: `diagrams/UBL-2.3-OrderingProcess/UBL-2.3-OrderingProcess.drawio`,
made from `sources/UBL-2.3-OrderingProcess.svg` by `build_ordering.py`. First kept beside the SVG as a
backup, it was made the figure's source the same day, so that all 96 figures are drawings of one kind.

- **draw.io's own BPMN shapes,** styled as its BPMN palette makes them (`Sidebar-BPMN.js`, 32.0.2):
  Generic Task (`mxgraph.bpmn.task2`), the Exclusive gateway (`mxgraph.bpmn.gateway2`,
  `gwType=exclusive`), the None Start and the Terminate end event (`mxgraph.bpmn.event`), Sequence Flow
  and Message Flow. A pool is the palette's plain swimlane (its pools are made for lanes, and this figure
  has none). Not as the palette has it, to look as the figure: the line weights (2 px; a message flow
  1.5 px, dashed 10 12) and text sizes (12 px; a flow's name 11 px), pool names not bold, flows
  orthogonal (the palette's elbow keeps one bend, these have up to four), a message flow's head open
  (as BPMN has it; the palette fills it).
- **Linked as a BPMN model is:** every element's id is its BPMN id and `ubl-bpmn-type` its BPMN type
  (all 50: 2 participants, 13 tasks, 3 exclusive gateways, a start event, 6 terminate end events, 19
  sequence flows, 6 message flows); every task, gateway and event is in its pool; every flow is
  attached at both ends (BPMN's `sourceRef` and `targetRef`); the 8 named flows carry their names as
  their own labels. What the SVG does not say the script infers, and stops where it cannot be sure:
  a flow's end is the one element its line ends on, an element's pool the one pool it lies in (which
  agrees with the SVG's order), and BPMN's rules hold (a sequence flow in one pool, a message flow
  between two). It prints the 25 links.
- **Checked:** `tools/check_drawio.py` ok (bpmn). Opened and saved in the live editor (32.2.0,
  `tools/drawio_editor_roundtrip.js`; `tools/drawio_upgrade.py --editor`: `SAFE`): the same file back
  (but the host and the window size, which the editor decides), every cell, link and label. Its
  export against the SVG's (`compare_png.py`, within 4 px on the print PNG): 1.02 % of the ink only
  in the SVG's, 0.86 % only in the drawing's; against the UBL repository's PNG: 0.98 % and 0.85 %
  (the SVG's own export: 0.00 %). Places and bends are the SVG's, the labels within 2 px; what differs
  is how draw.io draws the symbols (the terminate disc, the gateway's cross, the message flow's
  circle) and the dashes. In the baseline `baselines/2026-10-06/` with the other 95 (against 2026-10-05,
  `tools/drawio_baseline.py compare` says `new`).
- **Made once:** `build_ordering.py` writes the source, as the Group B and C scripts write theirs.
  Since then the drawing is edited in draw.io; running the script again would overwrite an edit.

## `redrawn/`: experiments, not the sources (but `lib.py`)

`redrawn/lib.py`, the writer of these drawings, is also what the sources' scripts write with
(`build_ordering.py`, `history/group-b/lib_b.py` and through it `history/group-c/lib_c.py`): keep it.

Before the originals were chosen, all four were drawn again as draw.io drawings made for this
repository: the BPMN pair as draw.io's BPMN shapes with the model's ids and kinds (Ordering from the
bpmn-js SVG, since redrawn properly as the figure's source, above, which replaced its experiment;
Business Information with white bars), Pre-award and Procurement rebuilt with draw.io's
own shapes at 0.3 of the TC's scale (text 12, 18, 21 px, lines 2 px; one dashed corner line per list of
documents). The redraws matched the PNGs to 1-8 %, and the TC's originals they were drawn from to 0-0.07 %.
Kept as a record of what a cleaner, rescaled version looks like (`redrawn/*.drawio`, built by `redrawn/build_*.py`
and `redrawn/adopt_businessinformation.py`), in case the TC
wants the 12 px convention for these too (README, "Questions for the TC", B3). The scripts write beside themselves and cannot overwrite a
source.

## Run again

```sh
python3 history/group-a/adopt_originals.py            # sources/ -> diagrams/ (the three .drawio)
python3 history/group-a/build_ordering.py             # sources/UBL-2.3-OrderingProcess.svg -> diagrams/
python3 tools/check_drawio.py diagrams/UBL-2.3-OrderingProcess/*.drawio diagrams/UBL-2.3-Pre-awardProcess/*.drawio \
    diagrams/UBL-2.3-ProcurementProcess/*.drawio diagrams/UBL-2.4-BusinessInformation/*.drawio
NODE_PATH=$(npm root -g) node tools/export_drawio.js to-ubl-repo diagrams/UBL-2.3-OrderingProcess/*.drawio \
    diagrams/UBL-2.3-Pre-awardProcess/*.drawio diagrams/UBL-2.3-ProcurementProcess/*.drawio diagrams/UBL-2.4-BusinessInformation/*.drawio
python3 tools/check_svg.py to-ubl-repo
python3 history/group-a/compare_png.py <ubl>/art to-ubl-repo/art <out> <figure> ...
```

After that the drawings are the source: edit them in draw.io. `adopt_originals.py` and
`build_ordering.py` would overwrite an edit; they are how the drawings were made, and need not be
run again.
