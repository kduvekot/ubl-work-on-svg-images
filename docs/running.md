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
| Python 3 | `numpy`, `scipy`, `pillow`, `pytesseract` |
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
| `-graph.json` | the reading: nodes, flows, labels, dividers, guards, and what it is unsure of |
| `-spec.json` | that reading turned into a drawing spec |
| `.svg`, `.drawio` | the editable output |
| `-classified.svg` | the same drawing coloured by what each element was classified as |
| `-render.png` | the SVG rendered back at the original's own pixel width |
| `-diff-r2.png` | the pixel difference: red lost from the SVG, blue invented by it |

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

## 6. The OCR cache

`ocr_cache.py` memoises every tesseract call, keyed by the image bytes and the
settings. It defaults to `~/.cache/ubl-ocr`, outside the working tree; set
`UBL_OCR_CACHE` to move it.

A cold cache is only slower, never different: a blind reproduction test confirmed
that 24 of 24 generated files came back byte-identical between a cold and a warm
run.

## 7. Data that is not derived from the PNGs

Three fixtures hold judgements the pixels cannot supply, and are read by the
tools at run time:

| file | what it holds |
|---|---|
| `tools/reading-lexicon.json` | 367 words, for settling an OCR reading against the rest of the set |
| `tools/direction-verdicts.json` | 26 flow directions checked against the originals, keyed by position |
| `tools/artwork-faults.json` | 9 diagrams, 12 rules: the artwork's own gaps, recorded rather than corrected |

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
