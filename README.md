# ubl-work-on-svg-images

Recovering **editable sources** for the UBL specification's artwork. UBL publishes
its process diagrams as PNG; most of their original sources are lost, so a
change means editing a bitmap. This work turns each of the **78 UML activity
diagrams** of UBL 2.5 (of its 97 figures) into a **model** - lanes, steps,
documents, flows, guards, each with an identity - from which an editable SVG and
draw.io file are drawn.

## What there is now: originals, JSONs, SVGs

```
 original PNG  ──(reading + recorded corrections)──▶  JSONs  ──(drawing)──▶  SVG + draw.io
 UBL repository, art/                                 diagrams/<figure>/     diagrams/<figure>/
 (not copied here)                                    the basis              generated, never edited
```

| | where | what it is |
|---|---|---|
| **The originals** | `art/` in the [UBL repository](https://github.com/oasis-tcs/ubl), branch `ubl-2.5` at `3d81e8a` - not copied here | The 600-dpi PNGs as OASIS publishes them. Everything was read from them and checked back against them, pixel for pixel. |
| **The JSONs** | `diagrams/<figure>/<figure>-diagram.json`, `-layout.json`, `-extraction.json` | **The basis of the SVGs.** What the diagram says (lanes, nodes, flows, texts), where each element is drawn, and how the reading went. Each has a schema in `tools/schema/`. |
| **The SVG and draw.io** | `diagrams/<figure>/<figure>.svg`, `.drawio` | Drawn from the diagram and layout JSONs alone, by `tools/draw-from-json.sh`. Never edited by hand. |

That the committed SVG and draw.io files are exactly what their JSONs give is
checked, without any PNG, by

```sh
tools/draw-from-json.sh --check diagrams     # all 78, about 20 s
tools/draw-from-json.sh diagrams <figure>     # redraw one figure after its JSONs change
```

`-extraction.json` is not drawn from: it records the reading's measurements and
open questions, for review.

**Starting over from the PNGs is still possible.** The whole pipeline that made
the JSONs is kept in `tools/`: `extract_graph.py` reads a PNG, `model_io.py`
applies the corrections in `tools/model-corrections.json` and splits the result
into the three JSONs, and `run-pipeline.sh` / `verdict-sweep.sh` run it end to end
and check the drawing against the original (`verify_conversion.py`). A run at
this commit writes exactly the JSONs, SVGs and draw.io files in `diagrams/`
(section "Resuming" below, and `docs/running.md` section 10).

## Where we are (2026-09-28)

1. **All 78 figures have been reviewed with the TC**, figure by figure, hardest
   first: the model checked against the PNG, the SVG checked for faithfulness.
   Every decision is recorded - as a correction in
   `tools/model-corrections.json` (361 over 68 figures, each with its question
   and answer), a fault of the artwork itself in `tools/artwork-faults.json`, or
   a drawing rule in the code - and written up in
   [`docs/artwork-conversion-notes.md`](docs/artwork-conversion-notes.md) §16.
2. **The result is committed** in `diagrams/`: per figure the three JSONs, the SVG
   and the draw.io file.
3. **Measured against the originals**: every structural count is zero (no element
   or text absent or invented, nothing incoherent); the ink in error averages
   1.099% of each diagram's line-work (1.212% at the 2026-09-25 baseline); 9
   figures verdict `correct`; the 266 notes for a person are all settled.
4. **Standing drawing rules the TC set during the review** (notes §16): lane
   dividers are one straight line; a line hop only where two solid flows cross
   (never at a divider, a phase boundary or a dashed line); a guard on its own
   flow's line is moved off it where it can stand clear; texts stay inside their
   boxes; no grey; fork bars black; small arrowhead differences are accepted.
5. **Points for a future UBL release**, where the artwork itself is wrong (for
   instance the guard overlap on Billing with Debit Note, for UBL 2.6), are
   listed in notes §16.

## Working method

These were settled by correction along the way and are not to be relaxed:

- **The PNG in `art/` is the source of truth for what a figure shows**, never the
  draft SVGs in `svg-images/`. The JSONs record what was read from it.
- **Fidelity is proved by measurement.** When a check shows a difference, fix the
  output; never widen a tolerance.
- **Every change is checked over all 78**, never only on the diagram that
  prompted it: a sweep, `tools/compare-to-baseline.sh`, and the red/blue PDF from
  `comparison-pdf/build-compare-deck.sh`.
- **Questions go to the TC one at a time**, with context, an overview and a
  close-up of the original, and a suggested answer; UBL.xml's own text is read
  first, since it often settles the question. Each answer becomes a correction,
  is checked, committed and pushed.
- **Faults in the artwork itself are recorded, not corrected**: the SVG stays
  faithful to the drawing (`tools/artwork-faults.json`); what should change in
  the specification goes into the future-release points.
- **A step that involves a party the diagram does not draw** (a bank, goods
  sent, an authority without a column) is an ordinary step of the party that
  takes it; only what the specification itself puts outside its scope becomes
  an external segment (q7, q8).
- **The drawing may depart from the artwork only by a rule the TC set** (the
  standing drawing rules above); each departure is marked in the SVG and left
  out of the pixel check on both sides.

## Resuming

To draw from the JSONs, only Python 3 with `jsonschema` is needed:

```sh
tools/draw-from-json.sh --check diagrams
```

To start over from the PNGs, the artwork and the tools are needed as well:

```sh
# the artwork (the conversion was run against ubl-2.5 at 3d81e8a)
git clone --branch ubl-2.5 https://github.com/oasis-tcs/ubl.git

# the tools (Debian/Ubuntu; details in docs/running.md section 2)
apt-get install -y tesseract-ocr default-jdk-headless fop libsaxonhe-java
pip install numpy scipy pillow pytesseract jsonschema
npm install -g playwright && npx playwright install chromium   # if no Chromium yet
export CHROMIUM_PATH=/path/to/chrome   # unless it is at /opt/pw-browsers/chromium-1194/chrome-linux/chrome

# a full run over the 78: PNG -> JSONs -> SVG, checked against the PNG
JOBS=4 tools/verdict-sweep.sh ubl/art out tools/uml78-bycomplexity.txt
# the same files as committed?
for n in $(cat tools/uml78-bycomplexity.txt); do
  for s in -diagram.json -layout.json -extraction.json .svg .drawio; do
    cmp -s out/$n$s diagrams/$n/$n$s || echo "differs: $n$s"; done; done
```

What a correct run shows today: the sweep's tally `correct 9 improvable 0
needs-human 69 failed 0`, and no file differing from `diagrams/`. Against the
2026-09-25 baseline all 78 differ, as expected: the review changed every figure
(misread words, bold titles, sizes, the drawing rules). A new baseline is due.

A first run takes about 6 minutes on 4 cores, later ones under 2: the reading
of each PNG and each render are cached outside the repository
(`docs/running.md` section 6).

## Open work

1. **A new baseline**, `baselines/2026-09-28/`, from this state, once the TC has
   looked at the result. `baselines/2026-09-25/` is kept as it is.
2. **How figures are changed from here** is not yet decided: in their JSONs
   directly (the PNG pipeline then only a check), or still as corrections re-run
   from the PNG. Until it is, a change made by hand in `diagrams/` would be
   overwritten by copying in a new pipeline run - check with
   `tools/draw-from-json.sh --check` and the `cmp` loop above.
3. **The draw.io file is poorer than the SVG** (`docs/running.md` section 8): no
   bands, dividers, phase boxes or off-page flows; and every action is marked
   bold, even where the artwork sets actions in regular type.
4. **Known limits of the checkers** (`docs/running.md` section 8): they read the
   extractor's reading rather than the JSONs, and the text check forgives one
   wrong letter (the misreadings were found by eye and corrected).
5. **Decisions not yet taken**: UML-in-draw.io or BPMN as the target; where in
   the UBL repository the sources and the pipeline should live.

## Map

| | |
|---|---|
| `diagrams/` | **the result**: per figure the three JSONs (the basis) and the SVG and draw.io file drawn from them |
| `tools/` | the pipeline: `extract_graph.py` (read a PNG), `model_io.py` (reading to JSONs, corrections, validation), `spec_from_model.py` + `build_diagram.py` (draw), `draw-from-json.sh` (draw from the committed JSONs), `render-svg.js`, `VisualDiff.java`, `verify_conversion.py` (the referee), `model_sheet.py`, the sweep and comparison scripts |
| `tools/schema/` | JSON Schemas of the three JSON files |
| `tools/*.json` | judgements the pixels cannot supply: `model-corrections.json`, `direction-verdicts.json`, `artwork-faults.json`, `reading-lexicon.json` |
| `baselines/2026-09-25/` | the reference run before the figure review: every output of all 78, the sweep table, the review PDF |
| `comparison-pdf/` | the review PDFs: against the original (`build-deck.sh`), against a baseline (`build-compare-deck.sh`) |
| `docs/running.md` | how to run everything, what to install, the caches, known rough edges |
| `docs/artwork-conversion-notes.md` | the working record: why each rule exists, what was measured and rejected, and every TC decision (§16) |
| `docs/review-questions/` | the pictures each review question was asked with |
| `svg-images/` | earlier hand-made draft SVGs under TC review - not a reference |
| `imageSummary.xsl` | from before this work: run from the UBL repository to compare its `art/` with a directory of new images (`xslt2pe UBL.xml utilities/images/imageSummary.xsl ~/t/compare.fo new-dir=...`) |
