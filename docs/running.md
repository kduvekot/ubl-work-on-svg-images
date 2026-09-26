# Running the conversion

Everything the pipeline needs is in this repository except the artwork itself,
which stays where OASIS publishes it. This page is what a fresh checkout needs in
order to reproduce the current result and carry on from it.

`docs/artwork-conversion-notes.md` is the working record - why each rule exists
and what it was measured against. This page is only how to run it.

## 1. The artwork

The 600-dpi PNGs under `art/` in the UBL repository are **the source of truth**
throughout: every rule in the extractor was measured against them, and the
acceptance test compares a render back to them pixel for pixel.

```sh
git clone --branch ubl-2.5 https://github.com/oasis-tcs/ubl.git
```

That gives `ubl/art/` - 97 PNGs, of which 78 are the UML activity diagrams this
work covers. The conversion as it stands was run against commit `3d81e8a`
("Updated CSD03 version number, release date, and editor").

Do not substitute `htmlart/`. It is the same diagrams at 750 pixels and 131 dpi,
roughly a fifth of the linear resolution; the type is 11 pixels tall there
against 51, and none of the readings in this pipeline survive it.

## 2. What has to be installed

There is no dependency manifest. What the current result was produced with:

| | |
|---|---|
| Python 3 | `numpy`, `scipy`, `pillow`, `pytesseract`, and `jsonschema` for the schema checks |
| tesseract | 5.3.4, with the English data |
| Node | 22, with `playwright` (a global install is fine) |
| A JDK | `javac`/`java`, for `VisualDiff` |

Two environment variables matter:

- `NODE_PATH` must reach a global Playwright install. `run-pipeline.sh` and
  `validate-artwork.sh` set it from `npm root -g` themselves; a sweep inherits it.
- `CHROMIUM_PATH` chooses the Chromium binary. It defaults to
  `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`, which is where this
  container puts it; set it if yours is elsewhere.

`VisualDiff.class` is compiled on first use by whichever script needs it.

## 3. One diagram

```sh
tools/run-pipeline.sh <art-dir> <out-dir> <basename> [<basename> ...]
```

Reads `<art-dir>/<basename>.png` and writes, into `<out-dir>`:

| file | what it is |
|---|---|
| `-graph.json` | the extractor's reading, as it writes it: everything below is made from this |
| `-diagram.json` | the model: lanes, nodes, flows, texts and what refers to what |
| `-layout.json` | where each element of the model is drawn, keyed by its id |
| `-extraction.json` | the extractor's own measurements and open questions, for review only |
| `-spec.json` | the model and layout turned into a drawing spec |
| `.svg`, `.drawio` | the editable output |
| `-classified.svg` | the same drawing coloured by what each element was classified as |
| `-render.png` | the SVG rendered back at the original's own pixel width |
| `-diff-r2.png` | the pixel difference: red lost from the SVG, blue invented by it |

The graph is split into the three files by `tools/model_io.py`, which refuses a
split that does not join back into exactly the graph it came from, and checks
each file against its schema in `tools/schema/` and every reference between them
(`model_io.py validate`). Nothing is drawn from the extraction report. What each
file holds, and why, is in section 15 of the notes.

## 4. The whole set

```sh
JOBS=4 tools/verdict-sweep.sh ubl/art out tools/uml78-bycomplexity.txt
```

`tools/uml78-bycomplexity.txt` lists the 78 basenames **hardest first**, which is
the working method rather than a detail: the hard cases are met while there is
still room to change the approach. `JOBS` defaults to one per core. The sweep
adds, per diagram, a `-struct.json` (the referee's report), a `-model.json` and
`-model.txt` (the UML rules read back as a sentence), and a `-marked.png` with
each finding numbered on the difference image.

It prints one line per diagram and a tally:

```
FIGURE                                    VERDICT     MISSING  INVENTED FINDINGS PERSON
UBL-2.2-DigitalAgreement                  needs-human   0.645%    0.494%       10      7
```

- **MISSING / INVENTED** are percentages of the diagram's own line-work ink, at
  radius 3, with text masked out and judged as text instead.
- **FINDINGS** is the structural count: elements absent or invented, text absent
  or misread, incoherence between the drawing and the model. **This is the number
  that must stay at zero.**
- **PERSON** is what is left for a human: an arrowhead too small to measure, a
  shape the reading is unsure of.
- **VERDICT** is `correct` only when the line-work diff is blank at the honest
  radius, every label reads back, and nothing is left for a person.
  **Never widen the radius to reach it.**

### The baseline to compare against

The result at the head of this branch, over all 78:

| | |
|---|---|
| elements absent / invented | 0 / 0 |
| text absent / text differs | 0 / 0 |
| coherence findings | 0 |
| mean ink in error | 1.212% |
| model sheets passing every rule | 78 of 78 |
| verdict `correct` | 9 |
| notes for a person | 266 |

A change is kept only if it holds every structural count at zero and does not
raise the ink. Measure it over the whole set, never on the diagram that prompted
it - most of the rules in here looked right on one diagram and cost elements on
another.

## 5. The review deck

```sh
comparison-pdf/build-deck.sh <ubl-clone> <sweep-dir> <out.pdf>
```

A landscape page per figure: the original, the conversion, and the difference
with red for ink lost and blue for ink invented, plus that figure's findings.
Needs Saxon and Apache FOP on `CLASSPATH`/`PATH` - see the script's header.

FOP will not read a 1-bit PNG, and three of the 97 are 1-bit. Most of the
greyscale originals also embed a grey ICC profile, which FOP carries into the PDF
and at least one viewer then paints solid black, and 25 are RGBA on a transparent
black ground. The script re-saves all of those as RGB, flattened onto white and
without the profile, into a scratch directory; the drawing's pixels are untouched.

It was last run with Saxon-HE 9.9 and FOP 2.8 as Debian/Ubuntu package them
(`apt-get install libsaxonhe-java fop`, then `SAXON_JAR=/usr/share/java/Saxon-HE.jar`).

### Comparing a run with a baseline

```sh
tools/compare-to-baseline.sh baselines/<date>/diagrams <sweep-dir> <compare-dir>
comparison-pdf/build-compare-deck.sh <ubl-clone> <compare-dir> <out.pdf> <date> "<what changed>"
```

The first renders the baseline's SVG and the new run's SVG side by side, now and
with the same renderer, at the original PNG's pixel width, and differences them
at radius 0 with no alignment. It also counts every pixel that differs at all,
because the red/blue picture is drawn from ink and would not show a change of
shade, and compares the SVG, `.drawio` and spec byte for byte - and, where they
differ, again with the new run's element ids mapped back to the baseline's, so a
renaming alone shows as `ids` rather than `DIFF`. It prints a line per diagram,
writes `summary.json`, and exits non-zero unless every diagram is identical.

The second makes the PDF: a summary page, then per figure the baseline render,
the new render, and the difference, red for ink only the baseline has and blue for
ink only the new SVG has. While the JSON is being restructured, **every figure
must come out identical**: that is the fixed reference point.

### Saved baselines

`baselines/<date>/` holds a complete sweep, kept so that any later run can be
compared against it and so that it can always be gone back to. A baseline is
never regenerated or overwritten: a new one goes into a new dated directory
beside it. Each holds

| | |
|---|---|
| `sweep.txt` | the sweep's table, as printed |
| `review-deck.pdf` | the review deck built from it |
| `diagrams/` | everything the sweep wrote, per diagram |

| baseline | artwork | result |
|---|---|---|
| `2026-09-25` | `ubl-2.5` at `3d81e8a` | the table above, exactly: every structural count 0, 1.212% ink, 9 `correct`, 266 notes |

That run used tesseract 5.3.4 and Chromium 1194 (Playwright's build), in a
container with no Helvetica or Arial: the SVGs rendered in Liberation Sans. A run
elsewhere can differ in the renders and the text reading for that reason alone.

## 6. The caches

Three caches make a repeat run fast. All live outside the working tree, all are
keyed on everything their result depends on, and a cold one is only slower,
never different.

**`ocr_cache.py`** memoises every tesseract call - the whole-page reads, keyed on
the file's bytes, and the label crops the extractor and verifier read one by one,
keyed on the crop's pixels - with the settings. It defaults to `~/.cache/ubl-ocr`;
set `UBL_OCR_CACHE` to move it. A blind reproduction test confirmed 24 of 24
generated files byte-identical between a cold and a warm run.

**`graph_cache.py`** keeps the extractor's reading of each PNG, keyed on the PNG,
the extractor's code and fixtures, the tesseract version and the numeric
libraries' versions. Most rounds of work - correcting the model, changing the JSON
or the drawing - do not change the reading, and with this they do not repeat it;
any change to the extractor misses and reads again. It defaults to
`~/.cache/ubl-graph`; set `UBL_GRAPH_CACHE` to move it, or `UBL_NO_GRAPH_CACHE=1`
to bypass it.

**`render-svg.js`** keeps each render, keyed on the SVG's bytes, the width, the dpi,
the browser build and the renderer itself; a sweep and a baseline comparison
render all their SVGs in one browser (`--batch`), `JOBS` pages at a time, where
each render used to start Chromium of its own. The baseline's SVGs never change,
so a comparison renders them once. It defaults to `~/.cache/ubl-render`; set
`UBL_RENDER_CACHE` to move it, or `UBL_NO_RENDER_CACHE=1` to bypass it.

Measured over all 78 on this container's 4 cores, every output byte-identical in
each case:

| run | time |
|---|---|
| sweep, nothing cached, one browser per render | 332 s |
| sweep, labels cached, reading everything again | 252 s |
| sweep, reading reused, one browser per render | 167 s |
| sweep after an extractor change (reading again, one browser, renders cold) | 240 s |
| sweep, reading and renders reused | 102 s |
| baseline comparison, first time | 70 s |
| baseline comparison, renders reused | 41 s |

What is left of the 102 s is mostly the verifier's whole-page image filters and
reading and writing the large PNGs. Starting Java is not among it (0.05 s);
`VisualDiff` now reads and writes its pixel arrays directly rather than a pixel
at a time, byte-identical over all 78 in both modes and about a fifth faster, but
that took a sweep only from 102 s to 101 s.

## 7. Data that is not derived from the PNGs

Four fixtures hold judgements the pixels cannot supply, and are read by the
tools at run time:

| file | what it holds |
|---|---|
| `tools/reading-lexicon.json` | 367 words, for settling an OCR reading against the rest of the set |
| `tools/direction-verdicts.json` | 26 flow directions checked against the originals, keyed by position |
| `tools/artwork-faults.json` | 9 diagrams, 12 rules: the artwork's own gaps, recorded rather than corrected |
| `tools/model-corrections.json` | what a person decided about the model where the reading got it wrong, by stable id; applied by `model_io.py` |

`build_lexicon.py` regenerates the first from a sweep. It overwrites the shipped
fixture by default, so pass it an output path if that is not what you want.

## 8. Rough edges, known and unfixed

Found by a reproduction test run by an agent with no access to this repository,
and still true:

- The radius is 2 in `run-pipeline.sh` and `validate-artwork.sh` and 3 in
  `verdict-sweep.sh`, so a sweep leaves two different "missing" percentages per
  diagram with nothing saying which one is the gate. The gate is the sweep's.
- `verdict-sweep.sh` runs `model_sheet.py` and `mark_findings.py` under
  `|| true`, so a crash in either is invisible in the table. One was hiding there.
- §6 of the notes accepts a diagram whose open questions have been **signed off**,
  but `verify_conversion.py` has no notion of a sign-off, so any diagram carrying
  a note reads as `needs-human` however much has already been confirmed about it.
