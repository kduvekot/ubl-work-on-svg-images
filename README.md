# ubl-work-on-svg-images

Recovering **editable sources** for the UBL specification's artwork. UBL publishes
its process diagrams as PNG; most of their original sources are lost, so a
change means editing a bitmap. The aim is a **model** of each diagram - lanes,
steps, documents, flows, guards, each with an identity - from which an editable
SVG and draw.io file are drawn, and later perhaps BPMN.

Scope so far: the **78 UML activity diagrams** of UBL 2.5 (of the 97 figures).

> Also here, from before this work: `imageSummary.xsl`, run from the UBL
> repository directory to compare its `art/` with a directory of new images:
> ```
> xslt2pe UBL.xml utilities/images/imageSummary.xsl ~/t/compare.fo new-dir=/Users/admin/t/new-images/ ; AHFCmd -d ~/t/compare.fo -o ~/t/compare.pdf -silent ; open ~/t/compare.pdf
> ```

## Where we are (2026-09-27)

1. **The conversion runs over all 78** (`tools/`): each 600-dpi PNG is read,
   turned into a model, drawn as SVG and draw.io, rendered back and checked
   against the original pixel for pixel. Every structural count is zero.
2. **A fixed reference point.** `baselines/2026-09-25/` is a complete run, kept
   for ever. Every later change is held against it: the drawing must stay
   pixel-identical unless the change is meant to alter it.
3. **The model is its own format** - per diagram a `-diagram.json` (what the
   diagram says), `-layout.json` (where it is drawn) and `-extraction.json` (how
   the reading went), each with a schema, stable ids, and a split that provably
   loses nothing.
4. **Reviewing the model with the TC**, one question at a time. Sixteen questions
   are settled (q1-q16), recorded as corrections the pipeline applies. None of
   them has changed a pixel of any drawing.
5. **Misread text is being noted, not fixed**, to be corrected in one pass at the
   end (TC instruction): 22 so far, with 9 drawing fixes found alongside.

The record of every decision is in
[`docs/artwork-conversion-notes.md`](docs/artwork-conversion-notes.md) §16;
the corrections themselves, question and answer included, in
[`tools/model-corrections.json`](tools/model-corrections.json).

> **Fix pass in progress (2026-09-27).** Step 1 done: the 22 text fixes are
> applied as corrections `text-01`..`text-22` (the list is kept as
> `appliedTextFixes`); against the baseline exactly those 12 diagrams differ.
> Step 2 done: the model errors (corrections `model-01`..`model-04`: a reversed
> flow and two text scraps on Fulfilment Despatch Advice, an invented flow on
> CPFR Create Joint Business Plan); 14 diagrams differ.
> Step 3 done: the drawing fixes (corrections `draw-01`..`draw-08` for line
> widths, a two-line text and a route; drawing code for upright document labels
> and notched filled arrowheads), listed in `appliedDrawingFixes`. Step 4 done:
> the checkers see every correction that changes what they check (the
> corrected graph now applies reversed, removed and added flows, removed and
> re-measured texts). 27 diagrams differ from the baseline, each only where
> fixed (red/blue PDF); the last two added by misread words found in the
> completeness sweep (Self Billing with Self Billed Credit Note, CPFR Identify &
> Resolve). Next: the TC checks that PDF, then a new baseline.

## Working method

These were settled by correction along the way and are not to be relaxed:

- **The PNG in `art/` is the source of truth**, never the draft SVGs in
  `svg-images/`.
- **Fidelity is proved by measurement.** When a check shows a difference, fix the
  output; never widen a tolerance.
- **Every change is held against the baseline, over all 78**, never only on the
  diagram that prompted it: `tools/compare-to-baseline.sh`, then the red/blue
  PDF from `comparison-pdf/build-compare-deck.sh`.
- **Questions go to the TC one at a time**, with context, an overview and a
  close-up of the original, and a suggested answer; UBL.xml's own text is read
  first, since it often settles the question. Each answer becomes a correction
  in `tools/model-corrections.json`, is checked (all 78 split, join back and
  validate; no pixel moves unless meant to), committed and pushed on its own.
- **Corrections are recorded, never hand edits** of generated files: the model is
  still regenerated from the PNG on every run, so a hand edit would be lost.
- **Faults in the artwork itself are recorded, not corrected** (the SVG stays
  faithful to the drawing; `tools/artwork-faults.json`).
- **A step that involves a party the diagram does not draw** (a bank, goods
  sent, an authority without a column) is an ordinary step of the party that
  takes it; only what the specification itself puts outside its scope becomes
  an external segment (q7, q8). Each case settled this way is still mentioned
  to the TC when found, so it is clear it was seen.
- **The next question is prepared as soon as the previous answer is recorded**,
  without waiting to be asked.
- **A plain fault in how the artwork is drawn** (q9), where the model has it
  right, is recorded in `tools/artwork-faults.json` and mentioned, not asked
  about; the drawing is left as it is until a later session re-lays diagrams.
- **Text fixes wait for the end** and go into `pendingTextFixes`.

## Resuming

Everything needed is in this repository except the artwork and the tools.

```sh
# the artwork (the conversion was run against ubl-2.5 at 3d81e8a)
git clone --branch ubl-2.5 https://github.com/oasis-tcs/ubl.git

# the tools (Debian/Ubuntu; details in docs/running.md section 2)
apt-get install -y tesseract-ocr default-jdk-headless fop libsaxonhe-java
pip install numpy scipy pillow pytesseract jsonschema
npm install -g playwright && npx playwright install chromium   # if no Chromium yet
export CHROMIUM_PATH=/path/to/chrome   # unless it is at /opt/pw-browsers/chromium-1194/chrome-linux/chrome

# a full run over the 78, then the check against the baseline, then the PDF
JOBS=4 tools/verdict-sweep.sh ubl/art out tools/uml78-bycomplexity.txt
tools/compare-to-baseline.sh baselines/2026-09-25/diagrams out out-compare
SAXON_JAR=/usr/share/java/Saxon-HE.jar \
  comparison-pdf/build-compare-deck.sh ubl out-compare compare.pdf 2026-09-25 "this run"
```

What a correct run shows today: the sweep's tally `correct 9 improvable 0
needs-human 69 failed 0`, identical line for line to `baselines/2026-09-25/sweep.txt`
once sorted; the comparison `identical 71, same drawing 7, differs 0`. The 7
"same drawing" are the CPFR figures whose model was corrected (q2-q5): not a
pixel differs, the SVG says something more accurate about what it draws.

A first run takes about 6 minutes on 4 cores, later ones under 2: the reading
of each PNG and each render are cached outside the repository
(`docs/running.md` section 6).

Tested on 2026-09-27 as a recovery drill: a fresh clone of this branch from
GitHub, empty caches, only the steps above - the sweep and the comparison came
out as stated, and every generated file was byte-identical to the working run's.

## Open work, in order

1. **Review questions still queued** (candidates found by scanning all 78, each
   to be brought to the TC one at a time):
   - From the model review (a checker reading the corrected model: document
     names and roles against UBL's own list, parties, verbs, guards, placement):
     artwork document names that differ from UBL's; "Receive" steps with no
     document coming in; "Publish Official Journal" on Contract Information
     Preparation.
   - The 266 notes for a person are settled (notes section 16); what they
     turned up waits in `pendingTextFixes` and `pendingDrawingFixes`.
2. **The one fix pass** at the end: apply `pendingTextFixes` as `retext`
   corrections (the machinery is built and was tried on the first 18) and
   `pendingDrawingFixes` (a reversed and an invented flow, stray texts, line
   widths, label style, arrowhead shape - these need corrections or drawing
   code not yet written), then re-baseline.
3. **Known defects not yet fixed** (docs/running.md section 8): the draw.io model
   is poorer than the SVG (fork bars, bands, off-page flows, guards not on a
   flow); the text check accepts a one-letter misreading; the checkers still read
   the extractor's graph rather than the model.
4. **Decisions not yet taken**: UML-in-draw.io or BPMN as the target; where in
   the UBL repository the sources and the pipeline should live.

## Map

| | |
|---|---|
| `tools/` | the pipeline: `extract_graph.py` (read a PNG), `model_io.py` (graph to model, corrections, validation), `spec_from_model.py` + `build_diagram.py` (draw), `render-svg.js`, `VisualDiff.java`, `verify_conversion.py` (the referee), `model_sheet.py`, the sweep and comparison scripts |
| `tools/schema/` | JSON Schemas of the three model files |
| `tools/*.json` | judgements the pixels cannot supply: `model-corrections.json`, `direction-verdicts.json`, `artwork-faults.json`, `reading-lexicon.json` |
| `baselines/2026-09-25/` | the reference run: every output of all 78, the sweep table, the review PDF |
| `examples/` | four diagrams as the pipeline currently writes them |
| `comparison-pdf/` | the review PDFs: against the original (`build-deck.sh`), against a baseline (`build-compare-deck.sh`) |
| `docs/running.md` | how to run everything, what to install, the caches, known rough edges |
| `docs/artwork-conversion-notes.md` | the working record: why each rule exists, what was measured and rejected, and every TC decision |
| `docs/review-questions/` | the pictures each review question was asked with |
| `svg-images/` | earlier hand-made draft SVGs under TC review - not a reference |
