# UBL artwork conversion — working notes

Handover notes for the effort to recover **editable sources** for the UBL
specification artwork. Written at the end of a working session so the next one
does not have to rediscover any of it.

**Where things stand now, and the open work, is in the README.** These notes grew
in the order the work was done, so read them as a history: sections 1-14 are the
conversion itself (to 2026-09-24), section 15 the model format and the baseline it
is held against, section 16 the review of the model with the TC.

These notes are the *why*: what each rule is for, what it was measured against,
and what was tried and rejected. **`docs/running.md` is the *how*** - where to get
the artwork, what has to be installed, the commands, and the numbers a new run
should reproduce. Start there if the object is to run this rather than to change
it.

---

## 1. Why this exists

UBL publishes its process diagrams as PNG. The UBL repository's own README
already states the intent:

> `images` — original revisable source vector artwork in `.svg` or `.drawio`
> *(incomplete set of files because many originals have been lost; please add
> originals here using same base name as published)*

Measured against `ubl-2.5` — reproduce with the commands in §2:

| | count | of 97 |
|---|---|---|
| diagrams published in `art/` | 97 | 100% |
| with **any** file in `images/` | 24 | 25% |
| with a **model-editable** source (`.drawio`, or `.svg` carrying an `mxfile`) | 12 | 12% |

So **85 of 97 diagrams cannot currently be edited as a model.** Changing one
means editing a bitmap. That is the problem this work addresses.

The goal is not "an SVG" — an SVG can be just as unmaintainable as a PNG if it
is a traced outline. The goal is a **model**: shapes with identity, labels as
text, edges that know their endpoints.

---

## 2. Reproducing the inventory

```bash
U=<path-to>/oasis-tcs/ubl                       # branch ubl-2.5
ls $U/art/*.png | wc -l                         # published diagrams
ls $U/images/ | wc -l                           # candidate sources
grep -l 'mxfile' $U/images/*.svg | wc -l        # SVGs that carry a model
```

For the intersection (which `art/` basenames actually have an editable source),
list basenames on both sides and `comm -12` them. Matching is by basename —
that is the convention the README sets.

---

## 3. Ground rules

These were established by correction during the work, and they matter more than
any individual technique:

1. **The PNG in `art/` is the source of truth.** Not the SVGs in
   `svg-images/` — those are draft conversions under TC review and are the
   thing being checked, not the reference.
2. **Fidelity is proved by pixel diff, not by eye.** Render the candidate SVG
   back to a PNG at the original's exact pixel size and difference them.
3. **When the diff shows a difference, fix the SVG — never loosen the
   tolerance.** This is the rule that changed the approach most. The first
   proof of concept was built from eyeballed coordinates and then defended by
   widening tolerances; rebuilding it from measurements taken off the PNG cut
   the error from 60% to 25% at a 2px radius. Everything in the pipeline now
   derives from measurement. If a number is guessed, that is a bug.

---

## 4. What the 97 diagrams actually are

Not a homogeneous set. Roughly:

- ~78 **UML activity diagrams** with partitions (the bulk of the work)
- 2 **BPMN** diagrams (`UBL-2.3-OrderingProcess`, `UBL-2.4-BusinessInformation`)
- 3 VICS CPFR step models
- 3 chevron/phase overviews
- 6 reference figures (tables, schema fragments)
- 4 pictorial illustrations
- 6 are bitmap wrappers — a PNG embedded in an SVG shell, carrying no vector
  content at all

`UBL-2.3-OrderingProcess` is the existence proof: its PNG was exported from
real vector artwork, and its SVG diffs clean.

Grouping matters because "convert the artwork" is really several different
jobs. The activity diagrams are mechanisable; the pictorial ones are not.

---

## 5. Standards research — conclusions

**There is no official OMG SVG shape library for UML.** This was checked
directly and the answer is a genuine no, not a "could not find". OMG publishes
*Diagram Definition* (DD), whose DC/DG/DI metamodels define diagram interchange
as **XMI**, not as a normative SVG rendering. UML DI 1.0 is superseded. UML
2.5.1 (formal/17-12-05) specifies notation — what a shape means — but not a
file you can adopt. So "make the SVGs officially UML-conformant by using the
standard library" is not an available move; conformance here means following
the notation, which the pipeline does deliberately (§7).

**BPMN is the stronger long-term target if interchange matters.** BPMN 2.0.1
is also ISO/IEC 19510:2013 and *does* define interoperable diagram
interchange — a BPMN file moves between tools with its layout intact, which a
UML activity diagram largely does not.

**draw.io / mxGraph is the pragmatic middle.** An SVG carrying its model in a
`content="<mxfile…>"` attribute is simultaneously a published image and an
editable model, in one file, with no second artefact to keep in sync. UBL
already uses this for the 12 editable diagrams, so it is the house format
rather than a new dependency.

---

## 6. The pipeline

```
art/NAME.png  ─▶ extract_graph.py    ─▶ NAME-graph.json   (the reading)
              ─▶ model_io.py split    ─▶ NAME-diagram.json (model), -layout.json,
                                         -extraction.json  (see §15)
              ─▶ spec_from_model.py   ─▶ NAME-spec.json    (build spec)
              ─▶ build_diagram.py     ─▶ NAME.svg + .drawio
              ─▶ render-svg.js        ─▶ NAME-render.png   (original's exact size)
              ─▶ VisualDiff           ─▶ NAME-diff.png     (the acceptance test)
```

Run it:

```bash
./tools/run-pipeline.sh <path-to-ubl>/art <out-dir> <basename> [<basename> ...]
```

**Dependencies:** python3 with numpy / scipy / pillow / pytesseract, the
`tesseract-ocr` binary, node with playwright, a JDK.

**Reading the diff:** white = agreement, **red** = in the original and missing
from the SVG, **blue** = invented by the SVG.

**Do not use radius 40.** An earlier version of these notes called "missing at
radius 40" the number to act on. It is not a measurement — it is a tolerance
wide enough to pass. The radius means "count this pixel as matching if the other
image has any ink within r", so r=40 is an 81×81 forgiveness window over artwork
whose strokes are ~6px. Measured on `UBL-2.5-BillingwithCreditNoteProcess`:

| candidate | missing @ r2 | missing @ r40 |
|---|---|---|
| unmodified render | 10.28% | 2.7355% |
| one whole node box displaced 20px | 13.79% | **2.7355%** |
| the same node deleted outright | 13.87% | 6.23% |

Displacing an entire node changes the r40 figure by nothing at all, to four
decimals. It was introduced (session of 2026-09-16, ~19:25) explicitly as "a
criterion a person can actually pass", and then used to choose the PoC canvas
height — 955 over 960 — although the stricter radius in the same table said 960
was far better. That is exactly what ground rule 3 forbids, so any "@ r40"
figure in older notes, commit messages or the §9 table below should be treated
as void rather than merely optimistic.

**The acceptance test: structural completeness.** A redraw never lands every line
exactly, so demanding a blank diff demands the impossible — pixel-blank is only
reachable when the PNG was *generated from* the SVG. That is why the r40 fudge
appeared: the gate as originally written could not be passed. Removing the fudge
without replacing the gate left every diagram "improvable" forever.

What matters is not that every pixel matches but that **nothing is missing and
nothing is invented**. The two are distinguishable, and the distinction was noted
in the first session and then dropped: *red paired with ink nearby* means the
element is there and slightly displaced; *red with nothing near it* means the
element is not there at all. `verify_conversion.py` mechanises that. A diagram is
**structurally complete** when:

1. **No unexplained ink in the original** — every cluster of missing line-work
   lies within 15px of line-work the SVG drew, i.e. it is placement error. A
   free-standing cluster the size of a letter or larger is a lost element.
2. **Nothing invented** — the same test in reverse.
3. **Text present, correct and placed** — every word the original's own OCR finds
   must appear in a model text element covering that position.
4. **The graph is coherent** — no dangling edge endpoint, no node typed against
   its measured outline, no isolated node (notes excepted: UBL anchors them with
   a dashed leader the extractor does not recover).
5. **Nothing unresolved** — the `uncertain` list is empty, or signed off.

This is not a weaker bar than the original "white diff = done". It is the second
half of that same rule — *"anything red would require a check to see what caused
it and if it's acceptable"* — with "acceptable" given a definition: a line 2px off
is acceptable, a missing connector never is.

**Underneath it, two measurements, because the artwork has two kinds of
content.** Text redrawn in a different typeface never matches pixel for pixel,
which is the real problem r40 was invented to dodge. Split them rather than
widen the tolerance:

- **Line-work** — boxes, arrows, rules, frames — with text masked out of *both*
  images, compared at radius 2–3 (anti-aliasing only). Blank is achievable and
  this is the gate. Unlike r40 it moves when geometry moves: the displacement
  above shows up as 7.10% → 9.78%.
- **Text** — compared *as text*, not as pixels: the label must be correct,
  complete, and in the right place. This is stricter than any pixel test, which
  would happily bury OCR turning "Send Transport Progress Status" into "end
  Transport Progress Status".

---

## 7. Non-obvious findings

Each of these cost measurement to establish. They are the parts most likely to
be re-broken by a well-meaning change.

### Structure recovery

- **Partition rules are identified by where they *end*, not by how much ink
  they have.** A lane divider and the edge of a tall box both sit around 55%
  coverage once the boxes straddling the divider have punched holes in it. What
  separates them: a divider runs frame to frame, so it is unbroken for the first
  and last stretch of the interior; a box edge starts and stops inside it.
  Counting gaps does not work either — UBL draws object nodes *on* the divider,
  interrupting it a dozen times.
- **Whitespace trapped between shapes looks exactly like a node.** On a dense
  2-D partition grid this produced 29 phantom nodes out of 57. Three tests
  together fix it: the region must not coincide with a partition cell; it must
  not enclose another region; and its interior must match a UML outline
  (rectangle, rounded rectangle, rhombus, ellipse) while the line-work bounding
  it stops at its own edges. *Border coverage does not work* as a test —
  rounded boxes, rhombi and rings all leave their bbox corners white.
  This also removed a phantom decision node from a diagram that had previously
  been reported as having four.
- **Object vs action is a relative stroke weight, not an absolute one.** UBL
  draws object nodes heavier than action nodes, but the weights differ per
  diagram (6 vs 3 in one, 8 vs 4 in another). Sort the box strokes and cut at
  the widest gap. A fixed threshold misclassifies whole diagrams.
- **Label text is not necessarily centred.** Several tall activity boxes carry
  their label near the top. Measure each line's position and put it back there;
  assuming centring was the single largest source of error (~240px on one node).
- **Corner radii can be elliptical.** `UBL-2.2-VMI-Invoicing` was reported as
  measuring rx 91 / ry 58 — the artwork having been scaled non-uniformly at some
  point — and measuring both radii rather than assuming a stadium (r = h/2) was
  said to cut that diagram's error from 6.11% to 4.42%. *Treat the numbers as
  unverified:* they were produced by an extractor that no longer exists, and the
  current code measures rx 86 / ry 85 on the same shape. The principle — measure
  both radii, do not assume a stadium — still holds; the figures do not.
- **Font size from cap height.** The 90th percentile of glyph heights inside
  node labels is the cap height; divide by 0.70 for the em size. Deriving it
  from OCR bounding boxes is badly wrong when labels wrap.
- **A connector crossing a partition rule gets cut in two** when the rule is
  masked out, and then neither half touches both its nodes. Bridge the cut
  where line-work continues on both sides, or you silently lose those edges.

### Arrow direction

Direction is read from arrowhead ink density at each end. It is reliable in
isolation and **unreliable where several arrowheads converge on one node** —
the probe cannot tell whose ink it is seeing. Hence `directionConfidence` on
every edge: `high` / `medium` / `LOW`. The LOW flags are real; at least one
known-reversed edge was correctly flagged. **Treat LOW edges as unverified
until a human checks them** — do not let the graph be trusted as a model
without that pass.

### Rendering and output

- **Apache FOP cannot lay out Inkscape's `flowRoot`** (SVG 1.2 Full). Sanitise
  render copies only. Note: the five `flowPara` in the UBL SVGs are *empty
  placeholders* — nothing visible is lost.
- **FOP does not support `marker-start` with `auto-start-reverse`** (affects 66
  files). Substituting `auto` was verified safe for this artwork: 899
  `marker-end` references, zero `marker-start`, and Chromium A/B rendering was
  pixel-identical on all 66. Re-verify before assuming it holds for new files.
- **The `art/` PNGs carry a 600 dpi `pHYs` chunk** and an XSL-FO formatter sizes
  images by their intrinsic dimensions, so renders must carry it too. When
  writing that chunk by hand, the CRC goes at offset `4 + len(type) + len(data)`
  — getting this wrong produces a file that `file(1)` calls a valid PNG and
  Pillow refuses to open.
- **Compute the render height from the viewBox.** With `height:auto` the
  browser rounds the computed height *up*, giving a 1px overshoot that
  misaligns the whole diff.
- **One `UBL-1.0-ProcurementProcess` render looked garbled** — that was FOP's
  raw-PNG path, not an artwork defect. Re-encoding the PNG fixed it.

### Sweep cost

A full sweep of the 78 UML diagrams went from **~20 minutes to 202 seconds**
(cold cache, 4 cores) with every one of the 78 graphs and 78 verdict reports
**byte-identical** to the run before. The three causes, measured:

- **`OMP_THREAD_LIMIT=1`.** Tesseract splits one page across all cores with
  OpenMP, and OpenMP busy-waits. With three pages in flight each read took
  **15 s** where one alone took 0.25 s — the spinning threads were fighting, so
  running the sweep in parallel was *five times slower* than serial. Pinned to
  one thread, a serial run is unchanged and parallel scales.
- **A square dilation is separable.** `near()` asks "is there ink within r
  pixels", and `binary_dilation` against an explicit k×k footprint does not
  exploit that; `maximum_filter(size=k)` does. Identical output pixel for pixel,
  2.00 s → 0.02 s at the span the structural test uses, four calls per diagram.
  That alone was 90% of the verifier.
- **Page OCR is cached** on file content (`tools/ocr_cache.py`). The `art/` PNGs
  never change and a re-rendered SVG usually hashes the same, so both sides of
  the text mask hit. Keyed on content, not mtime, so an edited file cannot hit a
  stale entry.

The remaining per-diagram cost is ~6 s warm: extractor 1.6 s (mostly per-label
OCR crops), verifier 3-5 s, render 1.2 s, `VisualDiff` 0.8 s.

---

## 8. The semantic graph

`extract_graph.py` emits a **notation-neutral** model, which is the durable
part of this work. (Since §15 it reaches the rest of the pipeline split into a
model, a layout and an extraction report; the graph below is what the extractor
writes and what the split is made from.) Geometry can be re-laid-out and the notation re-rendered as
long as who-connects-to-what survives.

```json
{
  "partitions": [ {"axis":"column","index":0,"title":"Transport User"},
                  {"axis":"band","index":0,"title":"Planning"} ],
  "nodes": [ {"id":"n5","kind":"object","label":"Transport Service\nDescription\nRequest",
              "col":1,"row":0,"x":778,"y":308,"w":355,"h":171,
              "shape":"rect","stroke":6} ],
  "edges": [ {"from":"n4","to":"n6","routing":"diagonal",
              "fromPoint":[2699,449],"toPoint":[3078,707],
              "guard":"[initial\ncharges or\nunder\ncharged]",
              "directionConfidence":"LOW"} ]
}
```

`kind` is one of `initial`, `final`, `action`, `object`, `decision`, `fork`,
`note`. `routing` is `straight`, `diagonal` or `orthogonal`.

**This is what makes a future UML → BPMN move a re-render rather than a
redraw:** `col`/`row` become pools and lanes, `action` → task, `decision` →
exclusive gateway, `fork` → parallel gateway, `object` → data object,
`initial`/`final` → start/end events, and every edge already carries source,
target and guard. What changes is the renderer, not the content.

---

## 9. Validation results so far

> **These figures are void** — they are "@ r40" numbers, and §6 explains why that
> measures almost nothing. They are kept only so the claims can be traced. The
> "neither invents anything" claim in particular was forgiveness, not fidelity:
> swept across all 78 UML diagrams, the "blue at r40 is always zero" invariant
> fails on 49 of them.

| diagram | nodes | edges | missing @ r40 (void) | invented @ r40 (void) |
|---|---|---|---|---|
| `UBL-2.2-IMFM-IntermodalFreightManagementProcess` | 28 | 30 of 31 | 0.53% | 0% |
| `UBL-2.5-BillingwithCreditNoteProcess` | 17 | 17 of 19 | 2.74% | 0% |

Both align at scale 1.0000 on both axes. What is still missing is a short,
named list rather than a percentage:

- IMFM — the two note-anchor lines from the "Transportation Network
  Information" notes.
- Billing — two connectors meeting the fork bar, one line hop (the semicircle
  where an edge crosses another), and `]` characters dropped by OCR from two
  guards.

Earlier conversions, in `examples/`: `UBL-2.2-IMFM-BasicTransportExecutionPlan`
(the first proof of concept, the most complex diagram in `art/`) and
`UBL-2.2-VMI-Invoicing` (the simplest).

**Every example in `examples/` is now regenerated by `tools/`, and must stay that
way** — an example the committed code cannot reproduce is worse than no example,
because the next session will trust it. Both of the originals were of that kind
and both cost a later session real time:

- `VMI-Invoicing` was generated at 20:23 on 2026-09-16 and copied into
  `examples/` at 21:30 — sixteen minutes *after* the extractor was rebuilt. Its
  `-graph.json` was in the pre-rebuild schema (`lanes`, no `shape`, no
  `routing`), which was the tell. It was described as "converted end to end with
  no hand editing", but the committed code did not reproduce it.
- `BasicTransportExecutionPlan` was built by `build_tep.py`, a bespoke script
  deliberately excluded from the repo as superseded, so nothing here could
  regenerate it. It is now pipeline output, which also measures better than the
  hand-built version it replaced: line-work invented 6.87% → 4.16%, missing
  unchanged at ~8.05%.

**If you change the extractor, regenerate the examples in the same commit.**

That rule had lapsed: the examples were last written at `80f72c4` and 41 commits
to the extractor, spec and builder followed before anyone noticed. They were
refreshed from the saved baseline, `baselines/2026-09-25/diagrams/`, and are kept
as the current pipeline writes them: since §15 that adds the model, layout and
extraction files, and the SVG, `.drawio` and spec carry the model's ids, which is
their only difference from the baseline's. The two `-diff-r40.png`
images went with the refresh, since that radius is void (§6) and nothing
produces them any more.

---

## 10. Open items (as of 2026-09-16)

*Partly overtaken since: all 78 have been run (sections 11-14), and the target
and location questions are still open. The current list is in the README.*

**Known gaps in the extractor**

- Note anchor lines are not recovered as edges (they merge with nearby
  connectors and get classified as text).
- Connectors meeting a fork/join bar are unreliable — the bar's mask margin
  swallows them.
- Line hops (crossing-edge semicircles) are neither detected nor drawn.
- Guard-label OCR loses trailing `]` and sometimes splits one guard across two
  text blocks.
- `directionConfidence: LOW` edges need a human pass. IMFM has 11 of 30.

**Bigger questions, not yet decided**

- Is the target UML-in-draw.io, or BPMN? §5 argues BPMN is stronger for
  interchange, but it is a larger jump and changes what the TC publishes.
- Should the recovered sources go in UBL's `images/` (matching the README's
  existing convention) with the pipeline in `utilities/`? `imageSummaryGrouped.xsl`
  in `comparison-pdf/` in particular belongs in UBL's `utilities/`, not here.
- The remaining ~76 activity diagrams have not been run. The two validated here
  were chosen deliberately to exercise 2-D partitions, notes, fork bars and
  diagonals; a sweep should surface whatever they do not cover.

**A caution for whoever picks this up:** the pixel diff is a *regression gate*
for generated SVGs — 0 red / 0 blue is achievable and meaningful. For a
hand-redrawn diagram it is only a *triage aid*, because text glyph differences
are irreducible. Do not set a percentage target for hand-drawn work.

---

## 11. Review with the TC, diagram by diagram (2026-09)

All 78 UML activity diagrams were converted and swept. Two rounds of review with
a person followed, both recorded here because the *verdicts* are evidence that
cannot be re-derived from the artwork by the pipeline alone.

### 11.1 Flow directions: 26 checked, 25 confirmed, 1 corrected

Every flow whose direction the extractor could not settle - 26 across 10
diagrams - was put beside the original PNG and judged by eye.

**Twenty-five are drawn the way the model has them.** One was not:
`CPFR-ExceptionMonitor`, where the artwork draws the head into the *Exception
Notification (positive)* document and the model had `n6 -> n7`. Corrected to
`n7 -> n6`.

These 26 are a **fixture**: any change to how direction is read must leave all of
them reading as recorded. The list lives in `review/direction-checks.txt` (not
tracked - regenerate it from the sweep if lost) and the corrected one is in the
graph itself.

Why the other 25 could not be settled, now that all are known - **none was a
failure to read the artwork**:

| n | cause |
|---|---|
| 8 | the head probe overshoots the arrow's point and takes in what lies beyond: the next box's border, a diamond's upper edges, a document's border across a gap. Figs 17, 23, 31, 32. |
| 4 | the head is a **solid triangle** and the measurement looks for a shaft widening into a V. Figs 66, 70; 10 of the 78 draw filled heads. |
| 13 | the head is too small against the page for the ink at the two ends to separate. Fig C.1 draws 42px heads on a 3425px page, five flows through 29px diamonds. |

None of the three has been fixed. Each would change how direction is read across
all 78 to remove flags on flows that are already right - risk with no
correctness gain. The fixture makes them safe to attempt later.

### 11.2 Method note: verdicts validate, they do not determine

A rule was drafted from the corpus (head width 0.7-1.1x the diagram's own, from
953 readings) and **simulated over all 78 before shipping**. It would have turned
round five flows - four of which were correct, verified against the PNGs. It was
discarded and replaced by a narrower form that fires on exactly the three known
-wrong flows.

The trap it avoided: looking at head width *because* one case was wrong, then
fitting to it. The protection is to run any candidate rule over the whole set and
look at everything it touches, not only the case that motivated it.

### 11.3 Defects in the conversion, confirmed with the TC

Walked through one at a time with a crop of the original beside the render.

1. **Lane title loses its multiplicity.** `BUSINESS PARTY 0..n` reads as
   `BUSINESS PARTY O` plus a detached `N`. The `0` is taken for `O`; the `..n`
   falls below the cap-height band the lane-title reader uses, so the run breaks
   apart. Figs 86, 87. *Fix.*
2. **Last letter of a line falls outside the text block.** `Change of` ->
   `Change o`, `charges or` -> `charges o`. The glyph's pixels are present and
   unclaimed; the block simply stops short of them. Figs 45, 79. *Fix.*
3. **`Item` stored as `ltem`** (lowercase L for capital I). Invisible in the
   render - identical glyphs in bold Helvetica - wrong only in the data. The
   corpus settles it: `item` 41 times, `ltem` once. Fig 7. *Fix.*
4. **`Is` stored as `ls`, plus an arrowhead read as `>` merged into the label,
   plus the two lines collapsed into one** so the text now overlaps the diamond.
   Root cause is the third: line-work admitted into a text block widens its box,
   which breaks the line-breaking. Fig 42. *Fix.*
5. **A guard swallowed by the question above it.** `[no]` never reaches the
   model; it is absorbed into `Update Transport Execution Plan Request?` along
   with an arrowhead, and a label can only be drawn once. Same root cause as 4.
   Fig 74. *Fix.* (TC note: the original's own spacing invites this - the `[no]`
   sits tight against the question with the arrowhead between them, where the
   other diamond on the same diagram has clear space.)
6. **The checker reads a solid arrowhead as `mM`.** No such text in the original.
   The stroke version of this was fixed earlier (a note's fold reading `IN`); a
   filled triangle is not a thin stroke so it slipped through. Narrow fix: a
   reading sitting on a filled arrowhead the extractor has already measured is
   not text - position, not shape. Figs 64, 65. *Fix the checker.*

### 11.4 Faults in the original artwork - do NOT correct, record a remark

The TC's instruction: keep the SVG faithful, note the discrepancy in the
conceptual model.

7. **Fig 28 Award Notification** - *Unawarded Notification* and *Awarded
   Notification* have no connector at all; the one flow runs straight past them.
   TC: the diagram is wrong and would need a decision diamond to choose which
   notification to send, and arguably an extra lane for the awarded/unawarded
   split. Out of scope. Remark only.
8. **Fig 83 Utility Billing** - *Report usage* -> *Utility Statement* ->
   *Receive Utility Statement* is a three-element limb with nothing feeding it.
   Remark only.
9. **Fig 55 Fulfilment with Despatch Advice** - the Despatch Party lane has a
   start event labelled "From Order"; the Delivery Party lane has none, so
   *Receive Order Item(s)* simply begins. TC: this diagram needs proper cleaning
   up, outside this exercise. Remark only.
10. **Figs 31/32 Tender Contract Pre/Post** - *Prior exchange of public keys*
    appears in both lanes joined by a dashed line with **an arrowhead at each
    end**: a mutual precondition, not a flow. Decision: **set `arrowBoth`** so
    the model records it as bidirectional (the flag already exists and this pair
    is what it was built for), accept the four model-sheet findings it raises,
    and **note that this precondition needs additional work in the BPMN
    conversion project**.
11. **Fig 86 Business Card / Fig 87 Digital Capability** - the flow from the
    document to *Download business card* carries two short parallel diagonals
    across the lane divider. TC: this is a **"break" signal hijacked from BPMN**
    into a UML diagram, because the right-hand lane is `0..n` parties and the
    card may go to any of them - the original is drawn in a mixed notation on
    purpose. Keep the drawing as it is; **add a note**. (The extractor already
    records these as `crossMarks` and says their meaning is unread - that note
    can now be answered.)

    Note the two CPFR forecast documents (Figs 9, 12) that are written and never
    read are *faithful* - the last thing the phase produces, handed off the page.

### 11.5 The last of the walkthrough

**The 11 dead-end actions and the 7 diagrams with an unlabelled branch are
faithful.** Checked against the artwork: the three branches out of *Determine
Action* on Fig 55 carry no word in the drawing either, the bare diamonds on Figs
1 and 62 have none anywhere near them, and Fig 13's two *Receive & Resolve
Exception* boxes really do stop there. Both model-sheet rules now **report**
rather than fail (§12.3).

One real defect turned up while checking: Fig 13's left-hand *Receive & Resolve
Exception* read as `Receive & Resolve | Exception`, a stray `|` picked up from
the lane divider 110px to its right. No text check caught it, because the checker
compares words and `|` is not one. *Fixed* (§12.1).

### 11.6 Physical goods are a different kind of edge, and the drawing says so

The TC asked whether a physical goods movement could be **recorded and fully
validated**, and whether that could be **determined from the sources** rather
than from this conversation. Nothing in the repo recorded an edge's kind at all.
Two sources were tested; both work.

**The drawing itself.** Of the 21 flows that cross a lane with no document on
them (15 diagrams), one structural pattern picks out exactly the five physical
goods movements - no false positives, no misses:

> the flow forks from the action that sends the **Despatch Advice**, and re-joins
> the document's arm after receipt.

That is the drawing saying *the goods go with this advice*, and the Despatch
Advice is the UBL document whose whole purpose is to accompany a despatch. Figs
40, 42, 44, 47, 54. Three more kinds fall out of structure alone: **rework** (a
guarded branch out of a decision, 4), **phase** (same party, next band, 2, both
on Fig 72), **start** (an endpoint is a start event, 1, Fig 57). Twelve of the 21
classified with no prose at all.

Deliberately **not** used: a verb list. Tried over the whole set it agreed 352
times against 17, but its disagreements included readings that were right.

**UBL.xml's own prose**, which the conversion had never read - only
`UBL-local.xml`, and only for figure numbering. The section enclosing each
`<figure>` links every UBL document type the process uses as
`<link linkend="S-...-SCHEMA">`; 64 of the 95 figures do, which is machine
-readable per figure. It settles several of the nine left over outright:

- Fig 37 Punch-out - *"the exchange transaction is tightly coupled to the
  specific catalogue application and is **considered outside the scope of
  UBL**; thus, the only UBL document type involved in this process is
  Quotation."* The source states there is no document on that crossing.
- Fig 57 - *"the Consignor **or** Consignee initiates the transportation
  arrangements"*, which is why one start event reaches into the other lane: the
  same `0..n` looseness as Figs 86/87.
- Figs 31/32 - *"the exchange of electronic signatures depicted in the diagrams
  above is provided for the general understanding of the business
  choreography"*: context, not a step.

The prose is not wired into the pipeline; it is recorded here as the source to
use when the BPMN re-render needs to know which documents a process uses.

## 12. The fixing pass (2026-09)

Everything the walkthrough agreed, applied in one pass. Each change was measured
over all 78 before it was kept, and nothing was widened to make a difference go
away.

### 12.1 Readings

**Punctuation is not a letter.** `text_floor` models a letter's area, so the two
dots of `0..n` (69 and 74 pixels against a floor of 132) were dropped, leaving a
52px hole the blocks could not merge across. Ink below the floor is now kept
aside and may lengthen a block whose own ink already reaches it - the same
chain-back the corners cut off by node erasure already used, now shared as
`chain_in()`. A speck that starts no block of its own still cannot become a word.
Fixes the `0..n` titles and `charges of`.

**Line-work read as a character.** A connector stub entering a box from below
comes back as `|`, an arrowhead's two halves as `\/`, a note's folded corner as
`~`. Over the 78 these appear 61 times as a token on their own and never as
anything the artwork writes, while `&`, `?` and the hyphen - the only other
non-word tokens in the set - are always real. Stroke-only tokens are dropped, and
a text block left empty goes with them: **four diagrams were drawing whole
phantom words made out of their dashed connectors**. Fixes Fig 13's stray `|` and
the `>` glued to two questions.

**Spelling settled against the set.** A reading is only ever replaced by a
variant of *itself* that differs in characters the reader confuses (`l/I/1`,
`O/0`, `S/5`) and that the set writes more often. Case is **not** folded in: with
case included the rule changes 99 readings, nearly all of them the artwork's own
mixture of `Order` and `order`; without it, one word. One diagram is not always
enough evidence - `Is there a new item to be delivered?` on Fig 42 has no second
`Is` on its own sheet - so the counts come from all 78, in
`tools/reading-lexicon.json`, rebuilt by `tools/build_lexicon.py`. It is evidence,
not a spell-checker: a word the set gets wrong everywhere stays wrong, and nothing
outside the set's own vocabulary can enter a label. UML writes a multiplicity with
a digit, which settles `O..n`.

**A head at both ends, Figs 31/32.** Whether the point measures at all depended on
where the walk down the centre of the connector stopped - an artefact of the
trace, not a fact about the drawing. One end ran into the head, the other stopped
short of it, so the pair came out one-way and "high". Now a measured point at one
end says this is a head and not a junction, and the ordinary measurement is
enough at the other, provided the two agree on length, width and taper within the
same 1.4x already used. Over the 78 this sets `arrowBoth` on exactly those two
edges and touches nothing else.

### 12.2 The checker was naming arrowheads

`line_like` catches a stroke by its shape and cannot catch a solid head, which is
a blob: `mM` on Figs 64/65, `ZT` and `Ft` elsewhere. Shape will not separate
those from words - measured over the 78, real text runs to **9.7 type heights**
in one connected component where the head is 2.0, and to **0.53 of a type height
thick** where the head is 0.18, because the reversed lane titles are heavier than
any arrowhead. What does separate them is that the model already knows where it
put each head. The head must fall **inside** the reading's box: these boxes reach
along the shaft, so a tolerance wide enough to reach from the centre also
swallows nine guard labels sitting at the same node boundaries.

### 12.3 Edge kinds, and three rules that now report

`edgeKind` is written on every flow: `object` (467), `control` (562), `goods` (5)
- see §11.6 for how the five are picked out, and for the prose in UBL.xml that
corroborates them. Three model-sheet rules state something UML asks for that this
artwork does not always give, and all three were checked against the drawings, so
they **report** rather than fail:

- *work crossing between parties goes through a document* (15 diagrams) - each
  crossing is now named with what the drawing says it is: the goods beside their
  Despatch Advice, a start event, a phase change, a guarded branch, or "no
  document drawn - read this one against the artwork".
- *every action passes its work on* (11 diagrams) - the artwork does end on an
  action.
- *branches out of a decision are labelled* (7 diagrams) - the artwork leaves
  them bare.

### 12.4 Closing out the rest

**The last two text findings.** `text_floor` models a letter of average build, and
an `f` is a stem and two strokes where an `o` is a ring: the `f` of `Change of` is
258 pixels against a floor of 265. The speck rule of 12.1 now uses the same size
test the text blocks themselves use, which also recovers the final `r` of
`Importer` and of `Transport Service Provider`, and the `[` of a `[no]`.

**Arrowheads read as words, at the source this time.** Six text lines over the 78
enclose an arrowhead the extractor has already measured, and every one reads as
rubbish - `WZ`, `L`, `VA`, `Y`, `74`, `VA`. The bit is dropped before the blocks
are built rather than after, so the block is not stretched over the head either,
and `[accept items] VA` comes back as `[accept items]`.

**The guard swallowed by the question above it** (Fig 74). Two things had to give.
A band that the block reader already gave a line of its own is text: reading
`[no]` on its own comes out `) no]` at 43 against a floor of 45, two points short,
where reading it in its block comes out `[no]` - so the band was thrown away.
And brackets are UBL's own notation for a guard, so a block holding a bracketed
line and unbracketed ones is two things; over the 78 exactly one block is, this
one. Split back apart, the question is the decision's and `[no]` is the guard on
its branch, drawn where the artwork draws it.

**The 26 direction verdicts are now in the pipeline** as
`tools/direction-verdicts.json`. It never sets a direction: it marks the one that
was read as checked, and says so loudly if a flow it names is no longer read that
way, which makes every future change to how direction is read run into it. Flows
are keyed by where their elements sit, because node ids are handed out in reading
order and move, and a label can be re-read.

**Two isolated documents on Fig 28** were counted as incoherent. A node with
nothing attached is usually a connector the model lost, and then the pixels say
so - the line is missing from the rebuild right at its edge. Where nothing is
missing within the diagram's own arrowhead length, nothing was lost, and the
finding goes to a person instead.

**The break marks on Figs 86/87 are drawn again.** `cross_stub` expected each
stroke to arrive in two halves, one either side of the divider, because the
divider's ink is taken out before the components are found. The line-break repair
that runs earlier now puts those halves back together - "a 12px break at 146
degrees" - so the marks arrived whole and stopped at nothing, and the test threw
away the very strokes it was written for. A mark that straddles the rule is now
taken, at up to twice the length of a half, and has to be drawn with the pen that
drew the rule: the two stacked words of the `Customs Party` lane title lie at 70
degrees across the top frame and are 3.5:1 as a blob, but they are 42 pixels
thick against a rule drawn at 10, where these marks measure 7.6 against a rule of
7. Figs 86 and 87 fall from 1.32% and 1.75% of ink in error to 0.12% and 0.59%.

While chasing that: the flow out of the Business Card runs **down the lane
divider itself**, which is why the document reads as written and never read. A
route drawn as the divider cannot be recovered as a flow. The drawing stays as it
is, per the TC; the model records the gap.

### 12.5 What a failing rule means now

Twelve rule failures over nine diagrams were each read against the original and
found to be the drawing's own gap, not the reading's - the two notifications with
no connector on Fig 28, the forecast documents handed off the page on Figs 9 and
12, the limb with no start event on Figs 9 and 83, the lane with no start event
on Fig 55, the standing precondition on Figs 31 and 32, the divider-as-flow on
Figs 86 and 87. They are listed element by element in
`tools/artwork-faults.json`, and `model_sheet` reports those instead of failing
them **only where every element it names is on the list**. A new isolated
element anywhere else still fails, so the rule stays what it was written to be: a
tripwire for a connector the model has lost.

### 12.6 Where the set stands

| | r104 | r107 | r110 |
|---|---|---|---|
| elements absent / invented | 0 / 0 | 0 / 0 | 0 / 0 |
| text differs | 8 | 1 | **0** |
| text absent | 1 | 1 | **0** |
| coherence | 2 | 2 | **0** |
| mean ink in error | 1.206% | 1.212% | **1.189%** |
| diagrams with no finding at all | - | - | **78** |
| verdict CORRECT (nothing left for a person either) | - | - | 9 |
| model sheets passing every rule | 45 | 62 | **78** |

Every structural finding over the 78 is now zero. What is left is 291 notes for a
person - the arrowheads too small to measure, the shapes the reading is unsure
of - and the artwork's own faults, recorded rather than corrected.

### 12.7 Still open

- **The nine unclassified lane crossings** of 11.6: Figs 28, 37, 56, 72 (x3), 57
  and 31/32. Each is named in its model sheet with what the drawing says it is.
- **The four artwork faults** of 11.4 and the nine diagrams of 12.6, which stay as
  drawn by instruction.
- **UBL.xml's prose is still not wired into the pipeline.** It names, per figure,
  the UBL document types each process uses; that is the source to use when the
  BPMN re-render needs them.

---

## 13. Reproduction test (2026-09)

The package was handed to an agent with no access to this repository: a zip of
`tools/`, six 600-dpi `art/` PNGs, a names file and these notes, unpacked into a
sandbox it was told not to leave. Its instructions said what to do - unpack, work
out how to run it from the package alone, run every input, run whatever checks the
package provides at whatever settings the package specifies - and never what
result to produce. It was told to record every point where it had to guess, and
that every figure it reported had to come from a command it ran rather than from
these notes.

**It reproduced the six exactly.** Its missing/invented percentages match this
project's own run to three decimal places on all six, its structural lines are all
zero, and it confirmed determinism independently: with a cold OCR cache, all 24
compared `-graph.json`, `-spec.json`, `-struct.json` and `.svg` files came back
byte-identical to the warm run. It installed nothing and needed nothing from
outside the zip.

### 13.1 Four defects it found, all real, three of them recent

1. **`mark_findings.py` died on any diagram with a cross-mark.** A mark's two ends
   are given along its own axis, so a stroke leaning up to the right has
   `x1 > x2`; the bounding box was taken as `min(x1)` to `max(x2)` and came out
   **126 pixels wide in the negative**. Pillow refused it. The numbered review
   images and the `review` key were never written for Figs 86 and 87 - the two
   diagrams the cross-mark recovery had just fixed - and because the sweep runs
   that step with `|| true`, the summary table showed nothing wrong. Both halves
   fixed: the box is built from both endpoints, and `mark_findings` orders the
   corners of any box it is handed rather than trusting geometry it did not
   measure.
2. **The direction verdicts never retired the finding they exist to settle.** The
   two Tender-Contract flows carried `directionConfidence: "checked"` on the edge
   *and* an `edge-direction` item in the same graph's `uncertain` list, so the
   sheet said "checked" and "confirm which way this edge points" in one breath.
   The list is built from the confidences before the last direction decision is
   made. Moving the verdicts earlier is the obvious fix and is wrong - it judges
   the flows before they are final, and the table's own tripwire caught it
   immediately. The items are cleared where the verdicts are applied instead.
   Notes for a person: **291 -> 266**.
3. **`validate-artwork.sh` could not render anything as shipped**: it never set
   `NODE_PATH` for a global Playwright install the way `run-pipeline.sh` does, so
   every diagram came back `RENDER FAILED`, and it discarded the renderer's stderr
   so there was nothing to diagnose from. Fixed both.
4. **The model sheet contradicted itself.** Its narrative walk seeded only from
   drawn start events while its reachability rule also seeds from flows that come
   onto the page from outside, so Fig 86 printed "not reached from any start
   event: Download business card" directly above "ok every element is reachable
   from a start event". The walk now uses the same seeds as the rule.

Over the 78 after the four fixes: pixels and structural findings unchanged
(1.189% ink, every count zero), 78 of 78 marked images written where 76 were
before, no tracebacks, and the direction tripwire silent.

### 13.2 What it could not work out, and what is still true

Its other findings are about the package rather than the conversion. Those that
stand: the radius is 2 in `run-pipeline.sh` and `validate-artwork.sh` and 3 in
`verdict-sweep.sh`, so one sweep prints two "missing" percentages per diagram -
7.8% and 0.050% for Fig 86 - with nothing saying which is the gate; the OCR cache
defaults to `~/.cache/ubl-ocr`, outside the working tree; `build_lexicon.py`
overwrites a shipped fixture by default; and the `|| true` guards hide exactly the
crash it found. They are listed again in §8 of `docs/running.md`, where someone
about to run this will meet them.

Two it found are now answered: `docs/running.md` names `verdict-sweep.sh` as the
entry point and lists what has to be installed, and `tools/uml78-bycomplexity.txt`
is the names file a sweep needs, which until now existed only outside the
repository.

One it got wrong: `render-svg.js` does not hardcode the Chromium path. The
absolute path is a default and `CHROMIUM_PATH` has overridden it since the first
commit. The agent read the default and reported it as fixed; it is recorded here
because a finding from a test like that is worth no more than the evidence under
it.

One of its conclusions is overstated and is recorded here so it is not repeated:
it saw six diagrams that all carry notes for a person and concluded no diagram can
ever reach `correct`. Nine of the 78 do. The point underneath it is fair - §6's
acceptance criterion says "the `uncertain` list is empty, **or signed off**", the
package ships signed-off tables, and `verify_conversion.py` has no notion of a
sign-off, so a diagram with any note is `needs-human` whatever a person has
already confirmed about it.

---

## 14. Reading the deck page by page (2026-09)

The comparison deck was read figure by figure against the original. Everything
found was a defect in the reading, never a tolerance to widen; each rule below
was measured over all 78 before it was kept, and every one of them leaves the
structural counts at zero.

### 14.1 Nine rules, each measured before it was kept

1. **A dashed outline's corners are not words** (Figs 12, 13 and the rest of
   CPFR). Neither shape nor confidence separates a row of marks from a word; the
   size of the marks does. Over the 78 the largest mark in a real text block is
   never below 0.51 of the type height, and these sit at 0.24-0.28: nine blocks
   in 352 fall below half, and they are exactly the nine.
2. **A guard is not a lane title** (Fig 14). Two guards in the header strip were
   read as lanes called "No", and the spec then suppressed every other "No" on
   the page as already drawn. Matching a title by name now needs six letters:
   over the 78 that suppression fires eight times, four of them wrong and four
   of them real titles of eleven letters and up.
3. **A letter is not a flow leaving the page** (Figs 34, 35, 80). The left stems
   of "C", "I" and "U" in "Customer Initiated Update" were traced as flows with
   arrowheads and drawn through the word. An open end at least a fifth inside a
   text block is that block's ink.
4. **A sliver on a divider is the divider** (Figs 40, 41, 47, 54, 73, 76) - but
   only where the measured rule span covers it. Dropping all ten cost five
   elements: on four diagrams the artwork's divider overshoots its measured span
   by 473-487 pixels and the sliver is the only ink drawing it.
5. **A hair along a box's own border is that border** (Figs 73, 76). The IMFM
   object boxes are stroked 15 pixels and fitted to the inside of that stroke, so
   the outermost pixel survives the node's erasure and is traced as a flow round
   the box. Twelve over the 78, three to a box on four boxes; invented ink on
   Transport Progress Status falls from 963 pixels to 244.
6. **A mark fused to a word is still line-work** (Figs 65, 69). Nineteen readings
   carry a mark stuck into a word; eighteen are an arrowhead or a divider. The
   one that is not is "Create/Update", where the artwork really writes a solidus,
   so the solidus and the hyphen stay and the rest come out of a word as readily
   as from beside one.
7. **A guard of one letter**, §14.2 below (Fig 88).

Figs 18, 42, 51 and 62 - a dropped or doubled letter, a guard set at the wrong
size - were left by instruction after being traced to the same family: the type
size is measured per diagram and a short reading is fitted to it, so a single
letter set beside a long one reads as a different weight. Fig C.1's degraded
readings were left the same way. Its mixed bold is not a reading fault: measured
at identical scale the stems are 0.104 and 0.130 of the cap height, so the
artwork itself uses two weights.

### 14.2 The six "Y"/"N" guards on Fig 88, and the four ways that did not work

DigitalAgreement's three decisions each carry a "Y" and an "N" beside their
branches. One was read; five were not. A single character defeats the page
reader outright - it segments into lines and words and returns nothing at all
for one letter, however the crop is padded or scaled - so the letters were never
in the reading to place.

Four routes were tried and each was rejected by its own measurement:

- **Let a stranded mark start a text block.** Gained one of the six and destroyed
  four clean guards on the Tender diagrams, merging "Yes" and "No" into "7 No Yes".
- **Relax the block width gate.** 332 narrow marks of letter height over the 78,
  of which roughly 329 are dashes of a dashed outline or halves of an arrowhead.
- **Filter by connectivity.** Rejects the letters themselves, which touch nothing.
- **Accept any one alphanumeric near a branch.** Replaced the guard
  "[accept charges]" with "X" and lost a "No".

What separates a guard from every other small mark is *where* it is: beside a
branch out of a decision, which the reading already knows. Looked for only there,
only as one mark of this diagram's own cap height that no block already holds,
and read with the single-character mode on an isolated canvas, the 78 give 31
candidates and the reader names 2 - both of them a missing "N". The other 29 it
declines, so none is ever admitted.

That left three of the six still missing, for the reason the previous attempt
predicted: the area a node holds was its bounding box, and **a decision is a
diamond, whose bounding-box corners are empty canvas - which is exactly where the
drawing puts the guard**. All three stand in one. A decision now holds its own
area rather than its box: written as `|dx|/hx + |dy|/hy`, the diamond is 1 and
the same 14 pixels of clearance is `1 + 14*hypot(1/hx, 1/hy)`; the three letters
stand at 1.25, 1.24 and 1.35 against a clearance of 1.08.

All six are now drawn, each beside the branch it belongs to and in the place the
artwork puts it. Over the 78 one diagram changed, its ink in error fell from
1.326% to 1.139%, the set mean from 1.214% to 1.212%, and every structural count
stayed at zero with the same 266 notes for a person.

### 14.3 Guard placement

On Figs 64, 65, 74 and 88 a guard sits on the flow it labels rather than beside
it, because the artwork puts it there and the conversion copies the artwork. It
stays as drawn, by instruction.

---

## 15. The graph split into model, layout and extraction (2026-09)

The graph mixed three things in the same objects: what the diagram says (a node
is an action called "Raise Invoice" in the Supplier's lane), where it is drawn
(its box, its corner radii, where each line of its label sits), and how the
reading went (the fill ratio of its outline, the ink at an arrowhead). A person
correcting a label, or a BPMN rendering, needs the first; the SVG needs the first
two; only a reviewer needs the third. They are now three files per diagram, each
with a schema in `tools/schema/`:

| file | holds | keyed by |
|---|---|---|
| `-diagram.json` | lanes, nodes, flows, texts, off-page flows, marks, phases, and what refers to what | its own ids |
| `-layout.json` | every element's geometry, the rules, the type and arrowhead sizes | the model's ids |
| `-extraction.json` | the extractor's measurements, its open questions, and what the split found | the model's ids |

`tools/model_io.py` makes them from the graph and can put the graph back together
from them. The split is refused if the two are not equal field for field, so no
reading is lost on the way; all 78 round-trip. The spec is now made from the model
and layout alone (`spec_from_model.py`, formerly `spec_from_extract.py`).

**Held once instead of twice.** A guard was the words of a text block and a copy
of them on its flow; the flow now points at the block. A lane title was the lane's
and a second reading of it as a free text block; the second reading is moved to
the extraction report as `titleReadings`. Named fields replace the positional
arrays (`rules` and `ruleSpan` become one list of `{at, width, span}`), and a node
names the lane and band it stands in by their ids rather than by index.

**What the split turned up**, recorded as `findings` in the extraction report,
and all of it drawn exactly as before:

- *A lane title used as a guard*, four times. The reading attached the lane title
  "Seller" to a flow on `UBL-1.0-ProcurementProcess`, and "Producer" on
  `CRP-ChangeArticleCatalogue` and `VMI-PermanentReplenishment`. On
  `CPFR-CreateOrderForecast` it is the other way round: a real "No" guard in the
  header strip was read as the title of a lane. The SVG never drew these as flow
  labels, but the draw.io model did.
- *Two texts on one flow*, once: on `CPFR-ExceptionHandling` both "No" and "Yes"
  are attached to `n4->n7`, and the flow kept "Yes". One of them belongs to
  another branch.

**The fixed reference point.** Every step of this restructuring is held against
`baselines/2026-09-25` with `tools/compare-to-baseline.sh`: after the split, all
78 SVGs, `.drawio` files and specs are byte-identical to the baseline's, every
rendered pixel is the same, and so are the verifier reports, the model sheets and
the sweep table. Until the model starts being corrected on purpose, that is the
rule for any change to the JSON.

**Stable ids.** The graph's ids were handed out in reading order (`n1`, `n2`, ...)
and moved whenever the extractor changed, so no correction could be pinned to one.
Every element of the model now has an id that says what it is:

| element | id | example |
|---|---|---|
| lane, band | `lane-<title>`, `band-<title>` | `lane-accounting-supplier`, `band-1` where untitled |
| node | `<kind>-<label>` | `action-raise-invoice`, `object-invoice` |
| unlabelled node | `<kind>-<lane>` | `initial-accounting-supplier`, `fork-accounting-supplier` |
| flow | `flow-<from>-to-<to>` | `flow-raise-invoice-to-invoice` |
| text | `text-<words>` | `text-accept-charges` |
| off-page flow, mark, phase | `offpage-<node>`, `mark-<n>`, `phase-<n>` | |

A label shared by nodes in different lanes takes the lane's name
(`decision-reconcile-charges-in-accounting-supplier`); anything still alike is
numbered `-2`, `-3` from the top of the page. The ids are names, not a hash: once
a model is kept and corrected by hand its ids stay, and correcting a label does
not rename anything. The graph's own ids are kept in the extraction report as
`formerIds`, which is also how the split joins back.

The SVG and the `.drawio` carry the same ids, so every drawn element can be
traced to the model: a lane title, a flow, a guard are no longer `lane0`, `e3`,
`text5`. That is the one change in their bytes. Against `baselines/2026-09-25`,
over all 78: not a pixel differs, and the SVG, the `.drawio` and the spec are
each the baseline's exactly once the ids are mapped back - a check
`compare-to-baseline.sh` makes by pairing the elements in document order,
requiring the pairing to be one-to-one, and comparing bytes after renaming. The
verifier reports, model sheets and sweep table are unchanged.

**Not yet done.** The verifier, the model sheet and the review marks still read
the graph itself, not the model (text fixes aside, see 16); the uncertain list
still points at places by coordinates rather than at elements by id; and the
model is still regenerated from the PNG on every run - which is why a person's
decisions are kept as corrections the pipeline applies (16), never as edits to
the generated files.

---

## 16. The model review with the TC (2026-09-25 to 2026-09-27)

The model is reviewed with the TC one question at a time: the question with its
context and pictures (`docs/review-questions/`), UBL.xml's own text read first,
a suggested answer, the TC's decision. Each decision is a correction in
`tools/model-corrections.json`, applied by `model_io.py`, checked over all 78
against the baseline and committed on its own (the procedure is in
`docs/running.md` section 9).

| | question | decided | diagrams | drawing |
|---|---|---|---|---|
| q1 | two guards attached to one flow | "Yes" labels the flow into Send Exception, "No" the flow leaving the page | Fig 10 | unchanged |
| q2 | the CPFR columns and box titles | the box title is the phase's name; the columns are Buyer Party (left) and Seller Party (right), from the text or by convention; the "No"s at the top label the arrows arriving from the previous phase | Figs 6, 7, 9, 10, 12, 13, 14 | unchanged |
| q3 | q1's mirror on the right-hand decision | the same answer | Fig 10 | unchanged |
| q4 | Fig 9 as one column; documents on a divider | split Fig 9 at its grey line; every document drawn on a divider stands *between* the two lanes (all 228) | Fig 9; all 78 | unchanged |
| q5 | *Ordering*, the prior key exchange | boxes that stand for a process outside the diagram (`external`); Ordering stands between the parties; the key exchange is a mutual `precondition` | Figs 13, 14, 31, 32 | unchanged |
| q6 | words beside a start or an end | they name it; three name the process it starts from or leads into (`linkedProcess`) | Initiate Freight Management, Certification of Origin | unchanged |
| q7 | the punch-out exchange, the only crossing without a document | the whole punch-out session is outside UBL's scope: a `segment` of the two actions and the flow between them, named by the note; the start stays outside it; the note stands between the parties | Fig 37 | unchanged |
| q8 | *Get Guarantee from financial institution*, a step involving a party the diagram does not draw | an ordinary step of the Tenderer: what it takes to complete is not this diagram's concern. A rule for all such steps (goods sent, a bank, an authority not drawn), settled without the TC from now on | Tender Guarantee Deposit | unchanged, no correction |
| q9 | the crumpled connector into *Exception Notification (positive)* | an artwork fault: the model has the flow right, the drawing is special drawing instructions to leave as they are until a later session re-lays the diagram; recorded in `artwork-faults.json` | Fig 14 | unchanged, no correction |
| q10 | the three notes on Intermodal Freight Management, on crossings with no document | an information exchange that takes place, which no current UBL document carries: drawn as a note instead of a document box, to show that it happens and between whom. The flow is of kind `information`, the note `annotates` it and belongs to no party; Fig 37's note annotates its segment the same way | Intermodal Freight Management, Fig 37 | unchanged |
| q11 | the flow Figs 86/87 draw down the lane divider, with the break marks | the model has the link: an object flow from the document to the download action, routed `along-divider`, with the two marks `on` it as a `break`; the drawing stays as it is. The two artwork-fault entries go | Figs 86, 87 | unchanged |
| q12 | "(from Business Processes)" under two documents | UML-tool notation: the document is defined in another package of the tool's model; each text labels its document, which records `definedIn` "Business Processes" | Utility Billing | unchanged |
| q13 | 42 texts in 20 figures labelling nothing | a question beside a diamond is the decision's `question`; words beside a start or an end name it (`starts-from` where they name another process); two merged texts split, and their decisions' guards put on the branches they are written on; three lane titles taken for guards removed | 25 figures | unchanged |
| q14 | 14 documents drawn on a divider that is not between the parties exchanging them | a document's `between` names the parties that exchange it, left to right, as its flows say (three where three take part); where it is drawn is the layout's; validation checks the two agree | 7 figures | unchanged |
| q15 | column titles read as loose text; Freight Status Reporting's untitled third column; sliver "columns" | the texts are the columns' titles, drawn where they are (Waste Movement takes UBL.xml's "Sender Party"/"Receiver Party", the drawing keeps "Senderparty"); Freight Status Reporting's third column is part of the Receiver Party (`merge-lane`): its start is the Receiver Party reporting on its own initiative, recorded as the start's `trigger` (in BPMN a timer start), drawn as the original draws it; seven 7-10 px strips between the last divider and the frame removed | 9 figures | unchanged |
| q16 | the lines between the CPFR figures | every line leaving one figure arrives at the next (Figs 6, 7, 9, 10, 12, 13, 14 in UBL.xml's order), same number, same left-to-right order: 1 the Buyer's side, 2 the Seller's. Each records `continues`, `port` and `counterpart`; validate checks both sides agree; Ordering is one step drawn on Figs 13 and 14 (`sameAs`); a Fig 9 line reversed to "out" | 7 CPFR figures | unchanged |
| - | misread text | noted, fixed in one pass at the end (`pendingTextFixes`, 22 so far; and `pendingDrawingFixes`, 9) | 25 | - |

After q12: 66 corrections over 16 diagrams; over all 78 not a pixel differs from
`baselines/2026-09-25` (71 identical, 7 the same drawing with a corrected model)
and the sweep table is the baseline's.

Settled without the TC, by looking at the original: 24 of the 28 notes for a
person on the CPFR figures - 16 arrowheads that are drawn and point the way the model says
(a guard beside the head made them unmeasurable), whitespace between a line and
the frame taken for an empty box, a dashed corner taken for line-work, documents
found by shape where no stroke weight told them apart. 224 of the 228 documents
have both a sender and a receiver among their flows; the other four are the
artwork faults of 11.4.

The detail of each decision follows.

**Corrections to the model.** `tools/model-corrections.json` holds what a person
decided about a model where the reading got it wrong, question and answer
included, naming the elements by their stable ids. `model_io.py` applies it
after the ids are assigned. Each correction also records what the reading held
before (`was`); if a later reading no longer holds that, the split stops rather
than apply a decision to something it was not made for. What each correction
touched is kept in the extraction report, so the split still joins back to the
graph exactly, and the finding it settles is marked `resolvedBy`.

The first, `q1` on `CPFR-ExceptionHandling`: of the two texts attached to the
flow into *Send Exception*, "Yes" is its guard and "No" is the guard of the flow
that leaves the page downwards. To say so, an off-page flow can now carry a
guard. None of this changes the drawing: over all 78 the renders are still the
baseline's, and the only files that changed are that diagram's model and report.

The second, `q2`, settles the CPFR phase diagrams (Figs 6, 7, 9, 10, 12, 13, 14),
from UBL.xml's CPFR text and the TC's review:

- *The title in the dashed box is the phase's name* - it is each figure's own
  caption in UBL.xml - not a column's. The reading had taken it for the title of
  the right-hand lane, or left it as free text.
- *The unnamed columns are Buyer Party (left) and Seller Party (right)*, as Fig 6
  draws them: stated by the text for Figs 7, 9 and 12 (the Seller creates the
  forecasts, the Buyer sends Retail Event and Product Activity), implied by
  convention for Figs 10, 13 and 14. The artwork does not draw these names, so
  the model marks them `titleShown: false` with their `titleSource`; the draw.io
  model carries them, the SVG does not draw them.
- *Each "No" at the top of Figs 12 and 14 labels the arrow beside it*: the
  no-exception branches of Figs 10 and 13 continuing onto the page. The reading
  had taken three of them for lane titles. Each incoming and outgoing flow of the
  pair now says which figure it `continues`.

Corrections are now applied before the final ids are assigned, so a corrected
lane is `lane-buyer-party` rather than `lane-no`; the corrections themselves name
elements as the uncorrected reading does, and the uncorrected model is kept in
the extraction report. Words that move from lane title to phase title or guard
are drawn exactly as before, so over all 78 every render is still the
baseline's: 71 identical, and these 7 the same drawing with a corrected model
(`compare-to-baseline.sh` now tells the two apart). Fig 9's split into two
columns is still open: its divider is drawn in light grey and the reading took
the page as one column.

The third, `q3`, is `q1` for the right-hand decision of the same figure, where the
reading had it the other way round: "No" was the guard of the flow into *Send
Exception* and "Yes" labelled nothing. Now "Yes" is that flow's guard and "No"
the guard of the flow that leaves the page, so both decisions read alike.

The fourth, `q4`:

- *Fig 9 is split at its grey line* into Buyer Party and Seller Party (a
  `split-lane` correction). The reading drew the line as a grey rule but did not
  take it for a divider, so the model had one column.
- *A document drawn on the line between two columns stands between them.* UBL
  draws all 228 documents in the 78 diagrams that way, and the reading had put
  each into whichever column its centre fell in, sometimes by a pixel - on Fig 12
  *Retail Event* came out the Buyer's and *Product Activity*, drawn the same way,
  the Seller's. Every document now has no lane of its own and names the two it is
  `between`. This is a rule, applied to every diagram (`place_documents()`), not
  a per-diagram correction. Who hands a document over and who receives it are
  its flows, which name both elements; 224 of the 228 have both, and the other
  four are the artwork faults already recorded (Fig 28's two notifications,
  and the flow drawn along the divider on Figs 86/87).

The drawing is unchanged: over all 78 no pixel differs from the baseline.

The fifth, `q5`, introduces boxes that stand for a process outside the
diagram's scope, which the diagram points at and does not describe - in BPMN
terms a call activity. The model marks them `scope: "external"` with a
`reference` saying what they stand for and where the specification says so:

- *Ordering* on Figs 13 and 14 is CPFR step 9, Order Generation: a separate phase
  outside CPFR ("This phase may be implemented using other UBL processes"), part
  of none of the other phases. It is drawn across the line between the parties
  and stands `between` them, and Fig 13's two lines out of it continue into
  Fig 14.
- *Prior exchange of public keys* on Figs 31 and 32 is a precondition of the
  contract process, which UBL.xml says is depicted "for the general understanding
  of the business choreography" and details under UBL Digital Signatures. Each
  party's box is external, and the dashed two-headed line between them is a flow
  of kind `precondition` - mutual, not a step in sequence (see 11.4 item 10).

Nothing drawn changes. Other boxes of the same kind are to be looked for across
the 78; Fig 37's punch-out exchange, "considered outside the scope of UBL", is the
first candidate.

The sixth, `q6`: words beside a start or an end name it. On Initiate Freight
Management the start is labelled "Ordering Process" and the end "Fulfillment
Process"; on Certification of Origin the start "Initiate Transport Process" and
the end "End of CoO Process". Each text now `labels` its node, and the three that
name another process record it as the node's `linkedProcess` (`starts-from` or
`leads-into`) - the same idea as the external boxes of `q5`, written on a start
or an end instead of drawn as a box.

The seventh, `q7`: on Fig 37, Punch-out Sourcing, *Initiate a punchout session*
(Originator) runs to *Build shopping basket* (Seller) with no document between
them - the one such crossing in the figure - and the note "Transaction accessing
Seller's catalogue application" sits on that line, over the divider, joined to
nothing. UBL.xml (section S-PUNCHOUT) says the exchange "is considered outside
the scope of UBL; thus, the only UBL document type involved in this process is
Quotation". The first suggestion was to mark the one flow `external`, as `q5`
marks a box; the answer went further: the whole session is outside UBL, a
prerequisite in sequence for sending the Quotation. So the model gains
`segments`: a part of the process the diagram sets apart without drawing a box
round it, here `segment-punch-out-session` with the two actions and the flow
between them as `members`, `scope` "external" and the UBL.xml reference; the
note names it (first as the segment's `annotatedBy`, since `q10` as the note's
own `annotates`). The start stays outside the segment, as the start of the
whole process; the flows keep their kinds (unlike the key exchange of `q5`, this
one has an order: the basket before the Quotation); the note, drawn across the
divider, stands `between` the parties. The model sheet now names the crossing
"outside UBL's scope" instead of asking for it to be read against the artwork.
A segment is not drawn, so Fig 37 stays identical to the baseline. (The one
other note drawn across a divider, *Regulatory Information* on Intermodal Freight
Management, is left for its own question.)

The eighth, `q8`, made a rule rather than a correction. On Tender Guarantee
Deposit the Tenderer's first step, *Get Guarantee from financial institution*,
involves a party the diagram does not draw, with no document passing. Unlike the
punch-out session of `q7`, UBL.xml says nothing about its scope. The answer: it is
a step whose detail is not given, and that detail is not relevant to this
diagram. It stays an ordinary action in the Tenderer's column. The same holds for
every step like it - sending physical goods, dealing with a bank or an authority
that has no column - so these are settled by this rule and not brought to the
TC. A `segment` with scope "external" is kept for what the specification itself
puts outside its scope, as UBL.xml does for punch-out.

The ninth, `q9`: on Fig 14 the connector from the Buyer's *Send Exception* to
*Exception Notification (positive)* is drawn collapsed - a short hook off the
action's corner and an arrowhead standing off the document - where its mirror on
the Seller's side is whole. The model already has the flow as it plainly is, its
direction checked (11.1). The answer: what is wrong is only how it is drawn,
"special drawing instructions", and the underlying model is right; so it is
recorded in `tools/artwork-faults.json` (a `drawn` entry, breaking no rule) and
left for a later session that moves elements around for a better flow. Artwork
faults as plain as this are from now on recorded without a question, and
mentioned when found.

The tenth, `q10`: Intermodal Freight Management has three notes -
*Transportation Network Information* twice and *Regulatory Information* - each on
a line that crosses between parties with no document on it; the model had them
as loose notes in the Transport Regulator's column, where two of them are only
drawn because the line runs through it. With Fig 37's they are the only four
notes in the 78, and all four do the same thing. The answer: there is no current
UBL document for these exchanges, but they are drawn to show that they take place
and between whom - relevant to the diagram, not a UBL document, and that is why
they are notes and not document boxes. So the flow gets a new kind,
`information` (beside `goods` and `precondition`), and the note `annotates` it;
a note belongs to no party - the flow's ends say who exchanges the information -
and stands `between` two parties only where it is drawn on their divider
(*Regulatory Information*, as Fig 37's). Not `external`: UBL.xml does not put
these exchanges outside its scope. Fig 37's note was changed to work the same
way, annotating its segment, so every note in the 78 points at what it names.
The model sheet now says "information exchanged with no UBL document:
Regulatory Information" where it asked for the line to be read against the
artwork. The notes' ids lose their lane (`note-transportation-network-information`,
`-2`); nothing drawn moves.

The eleventh, `q11`, closes a gap the model had recorded since 11 and 12.4. On
Figs 86 and 87 the way out of the Business Card (Digital Capability) runs down the
lane divider itself, carrying the pair of diagonal break marks - the BPMN break
the TC named in 11 - and then turns into the download action. A route drawn as
the divider cannot be read as a flow, so the model had the document written and
never read (an artwork fault), the download entered from off the page, and the
marks as unread line-work. The answer: the break character is a weird artifact,
but from the model's perspective there is a direct connection between the
document and the download action, and the model should have it - so that a
future redraw in BPMN 2.0 knows what is connected to what between the two lanes.
A new correction, `divider-flow`, adds the object flow
`flow-business-card-to-download-business-card` in place of the off-page flow; its
layout is routed `along-divider` (the divider draws the first stretch, the
off-page flow's old line the last, so nothing drawn moves), and the two marks
record that they are `on` it with the `meaning` "break". The model sheet reads the
added flow, so both figures now pass every rule on their own, and their entries
in `tools/artwork-faults.json` are gone. The draw.io file still lacks the link,
as it lacks every off-page flow (running.md section 8).

The twelfth, `q12`: Utility Billing writes "(from Business Processes)" in bold
italic under *Invoice* and *Invoice Status Response*, not under *Utility
Statement* - the only such words in the 78. They are Rational Rose notation: the
element is defined in another package of the tool's model, here "Business
Processes"; the invoice documents are borrowed from the billing processes, the
Utility Statement belongs to this diagram. A new correction, `defined-in`, makes
each text label its document and records the document's `definedIn`. Nothing
drawn changes (the squashed line is in `pendingDrawingFixes`).

The thirteenth, `q13`, came out of the model review (below): 42 texts in 20
figures labelled nothing. About 25 are the question a decision asks, written
beside its diamond ("Accept application?", "Exception Received ?", "Above
Thresholds?"), in figures whose branches often carry no words, so the question
is the only thing saying what is decided; about 10 name a start or an end ("From
Order", "Supplier Initiated Update", "Transport Service Ready For Execution").
Each was paired with its node by where it sits and checked by eye. New
corrections `decision-question` (the text labels the diamond, which records
its `question`), `split-text` and `unguard`. Two texts had a guard merged into
the question ("Is there a new item to be delivered? True"); splitting them
showed that on those two decisions (VMI Permanent Replenishment, CRP Change
Article Catalogue) "False" was on the wrong branch and the lane title "Producer"
was the other branch's guard - both put right. On Fig C.1 the lane title
"Seller" was a branch's guard and is removed. The checkers now see guard changes
too, so CPFR Exception Handling's model sheet shows the q1 decision ("Yes" into
Send Exception) instead of the reading's "No". Left for their own questions:
"Sender Party"/"Receiver Party" (Freight Status Reporting) and
"Senderparty"/"ReceiverParty" (Waste Movement), which are lane titles, and
"Publish Official Journal" on Contract Information Preparation.

The fourteenth, `q14`: after q4b a document's `between` was the divider it is
drawn on, which for 214 of 228 documents is also the pair of parties that
exchange it. For 14 it is not: a long arrow across an intermediate lane
(Certification of Origin, Intermodal Freight Management, Fulfilment Receipt
Advice, Fig C.1's Receipt Advice) or three parties (Fig C.1's Despatch Advice,
Initiate Freight Management, Payment Notification). Asked whether such a box
always stands next to the receiver: no - 5 of the 9 two-party cases do, 4 stand
next to the sender; a request and its response stand together, and the artwork
follows no rule. The answer: `between` says who exchanges the document, left to
right, from its flows; the layout keeps where it is drawn; `model_io.py
validate` refuses a document whose `between` disagrees with its flows. Nothing
drawn changes; 8 ids that named the drawn divider now name the parties.

The fifteenth, `q15`: on Freight Status Reporting and Waste Movement the column
titles are drawn smaller or bolder than elsewhere and were read as loose text,
leaving the columns untitled. New corrections `lane-title-from-text` (the lane
takes the title, drawn as and where the text was, so nothing moves),
`lane-area` and `remove-lane`. Waste Movement's lanes take UBL.xml's names
("the Sender Party ... the Receiver Party") while the drawing keeps the artwork's
"Senderparty"/"ReceiverParty". Freight Status Reporting's third column holds
only the start "Trigger reporting procedure": UBL.xml says a Transportation
Status is provided "either through a Transportation Status Request ... or
through an agreed status reporting procedure". First suggested as an area
outside the parties; after looking at the original the TC's view is that it
belongs to the Receiver Party: the start is the Receiver Party beginning a
status report of its own, independent of any request - in BPMN a timer start.
So `merge-lane` makes the column part of the Receiver Party (the divider stays
in the layout's rules, and the render is byte-identical), and `start-trigger`
records what sets the start off. "Model and layout are separate" is exactly
what lets the model say one party while the drawing keeps the artwork's line.
Waste Notification draws the same "Senderparty"/"ReceiverParty" titles; by the
same answer its lanes take UBL.xml's names too (`lane-name`: the model's name,
with the drawn words kept as the layout's `titleWords`; render byte-identical).

The element-by-element completeness sweep (started 2026-09-27) goes from the
rarest kind of element up. The first three are complete: the segment (1: its
members, scope, reference, and the note naming it), the marks (4: rule, the
flow they are on, meaning) and the notes (4: what each annotates, no lane of
its own). That there are only four notes in the 78 was checked on all 78
originals by eye, twice: on contact sheets, then each figure at 1400 px wide
(about 1:2.4 of the PNG, where the smallest note is some 180 px across): one on
Sourcing Punch-out, three on Intermodal Freight Management, none elsewhere.

The sixteenth, `q16`, checked the lines between the CPFR figures on the
originals, each figure's bottom laid over the next one's top. All of them
match: the same count, the same left-to-right order, positions within about
25 px, line 1 always the Buyer's side and line 2 the Seller's. New corrections
`hand-over` (the figure, the port number and the counterpart on the other
figure), `offpage-direction` (Fig 9's left line out of *Forecast (sales -
positive response)* leaves the figure; the reading had it arriving) and
`same-step` (*Ordering* on Figs 13 and 14 is one step; its lines are flows on
one figure and off-page lines on the other). `validate` refuses a hand-over
whose two sides disagree in port, direction or pointer.

The phases (7) were complete in title but not in content: which steps belong
to a phase was said only by where they are drawn. The model now lists each
phase's `members` - the nodes drawn wholly inside its dashed box - and
`model_io.py validate` refuses a phase whose members disagree with its box, so
a layout change can no longer move a step into or out of a phase unseen. On all
seven figures no node straddles a border; on Figs 13 and 14 *Ordering* stands
outside the box, as `q5` decided. Nothing drawn changes. Checked by the TC on the pictures: no step inside
a phase belongs to another phase. The boxes are drawn nearly frame-wide on every
figure whatever their content (Fig 9 has some 11 letter heights empty each
side): a layout matter, kept as drawn.

The fork/join bars (21) must each have a way in, a way out and two on one
side; `validate` now says so. Twenty did. The upper bar in Fig C.1's Seller
column had three ways in and none out: the line to *despatch order item(s)* was
read the wrong way round (the head is drawn at the step), so the bar is a join
of the two decisions' branches (`fork-01`, reverse-flow). The arrowhead moves to
where the artwork draws it, and the figure's missing ink drops (0.609% to
0.600%). CPFR Fig 12's bar takes both "No" lines from Fig 10 and starts two
branches: a join and a fork in one, as UML allows.

The off-page flows (31): the 20 on the CPFR figures are the hand-overs of
`q16`. The other 11, on eight CRP, ROCD and VMI figures, were no flows at all:
each lay exactly on the lane divider, which those figures draw in pieces that
stop at every document on the line, and the reading took each piece touching a
document for a line leaving it off the page. Invisible in the drawing, since
the "flow" was drawn exactly where the divider is. New correction
`divider-piece` takes them out of the model and keeps them in the layout as
pieces of the divider (`rules.pieces`), drawn as before - all 78 renders
byte-identical. `validate` now refuses an off-page flow that does not say which
figure it continues into. They were not caught by any rule on documents: a
document only had to be written once and read once, and 17 documents
legitimately have a second line in or out (a revision loop in CPFR, three
parties, two receivers), so "more than one" is not an error by itself.

The decisions (73). Contract: a question (or a name, like "Reconcile
Charges"), and a guard on every way out - or `unstated`, a new field recording
that the artwork gives none and why (correction `unstated`); `validate` refuses
anything else. 60 were complete. The other 13 are the artwork's own: Fig C.1's
four plain diamonds (no question, no guards; the step each branch leads to says
what it means), Certification of Origin's three (questions, unguarded
branches), Create Catalogue's diamond after *Respond to Request* (no words,
guarded branches), Fulfilment Despatch Advice's *Determine Action* (three
unguarded branches) and the four *Reconcile Charges* on the 2.5 billing
figures, which guard the accepting branch and leave the otherwise case
unlabelled. 29 `unstated` entries; nothing invented, nothing drawn changes.

The starts (75). Contract: a way out and none in; and every figure has a
start, or is entered from another figure, or records that the artwork draws
none (`unstated` now also works for the figure as a whole). All 75 have a way
out and none in. Of the 78 figures, 71 have a start; six CPFR figures are
entered from the previous one (`q16`); Fig C.1 draws none - the process begins
with the Buyer's *place order* - recorded as unstated. Words beside a start
are its name (`q6`, `q13`), with a linked process ("From Order", "From
Billing", "Ordering Process", "Initiate Transport Process") or a trigger
(Freight Status Reporting, `q15`) where they say one. On IMFM Goods Item Itinerary the two starts are
events - the Transport Execution Plan confirmed, or updated - recorded as their
`trigger` (TC, 2026-09-27); on the Update Catalogue pair "Supplier/Customer
Initiated Update" says who starts it, which the lane already says, so a name is
enough.

Bands and phases are one thing (TC, 2026-09-27). A stage of the process is a
*phase* in the model - a title and its members - however it is drawn: a dashed
box on the seven CPFR figures, a row across the page on Intermodal Freight
Management (Planning, Execution, Completion), whose layout now says `as`
"band". Nodes no longer carry a band. Figures that draw no stages have no
phase: the figure itself is the grouping. The bands the reading made that were
no stage are gone: the one untitled band covering a figure (69), the row under
the frame on the three 2.3 customs figures, which holds exactly the lane titles
(checked word for word) and is kept as the layout's `titleRow`, a display of
the lane names, and the 10 px margin between the frame and the edge of the PNG
on five figures, which holds nothing. The lines are the layout's rules, so all
78 renders are byte-identical. The split now always keeps the reading as it
was (`uncorrected`), so it joins back whatever the model makes of it.
*Provide Transportation Network Information* on Intermodal Freight Management
is drawn across Planning and Execution and serves both; the TC: it belongs
to both (`also-in-band`, the node's `alsoIn`), and a redraw could split it.

The ends (104). Contract: a way in and none out; every figure has an end, or
hands over to another figure (six CPFR figures, `q16`), or records that it
draws none; `validate` checks both. All 104 and all 78 figures pass. 52
figures have one end, 26 have two to four (one per outcome: rejected,
accepted, cancelled). Words beside an end name it ("End of CoO Process",
"Transport Service Ready For Execution") or the process it leads into
("Fulfillment Process", `q6`). Not every figure has an end: the six CPFR figures before
Fig 14 end by handing over to the next figure; and paths that stop at an action
without an end are the actions' part of the sweep.

The columns (170): every one has a name and something in it. The names were
written five ways - capitals on the Tender, Business Card, Digital and Enquiry
figures, line breaks inside a name, run together ("CustomsParty"), a
lower-case "party". The model now takes one clean form (Title Case, no line
breaks, a space before "Party"): 46 `lane-name` corrections, the drawing keeping
the artwork's words, all 78 renders byte-identical. 59 distinct names remain.
The same role under different names (Buyer / Buyer Party / Originator Customer
Party; Seller / Seller Party / Seller Supplier Party; Issuer / Issuer Party;
Exporter / Exporter Party / Export Party) is left as each figure has it: a
party vocabulary checked against UBL.xml's roles is a later decision. Settled from
the original and mentioned: on seven figures (Enquiry, five Tender figures,
both Tender Contract figures) the reading made a third column 7-10 px wide out
of the strip between the last divider and the frame; removed.

The texts (183): every text says what it labels. By what it labels: a guard on
a decision's branch (138: 132 on flows, 2 where the branch leaves for another
figure, and 4 where it arrives on that figure, repeating the guard it carries
where it leaves - the CPFR "No" lines, `q16`); a decision's question (25); a
start's name (12) or an end's (3); "(from Business Processes)" under a
document (2, `q12`); and three the TC settled (2026-09-27):

- *A guard out of an ordinary step (2, both Self Billing figures).*
  "[accept charges]" stands on a line from *Raise Self Billed Invoice* straight
  to an end. The step is a choice drawn without a diamond: the customer waits
  on the supplier, and either no dispute comes (the charges are accepted, the
  process ends) or a reply comes and leads to *Reconcile Charges*. Kept as
  drawn, a guarded flow out of the step, recorded as the flow's
  `impliedChoice` (`choice-01`, `choice-02`).
- *A text that labels nothing (1, Tender Contract Information Preparation).*
  "Publish Official Journal" stands under the line from *Prepare Simplified
  Notice* to the second *Prior Information Notice*. It is no guard - nothing is
  chosen there, and the "No" loop below has its own - but what that exchange is
  for: below the thresholds the notice goes in the buyer profile, and the
  simplified notice sent to the Publication Office announces it in the Official
  Journal of the EU, as UBL.xml says beside the figure. It now labels the flow
  with `role` "purpose" (`label-01`).
- *The repeated guards on hand-over lines* are the decision's guard, not a kind
  of their own. `validate` now checks that both ends of a handed-over line
  carry the same guard; all three pairs do.

`validate` also checks that a guard stands on a flow out of a decision or a
fork, or on one recorded as `impliedChoice`, and that a `role` text labels a
flow without being its guard. Settled from the original and mentioned: on
Self Billing with Self Billed Credit Note both "[accept charges]" were misread
- the line each stands against hides the closing bracket, and in one was read
as "[accept 1" - now `text-23`, `text-24`; that figure's render changes by
those words only.

The documents (228). Contract: a UBL document type's name, standing between
the two or three parties that exchange it (all 228 do), with a way in and a
way out; `validate` now checks the ways in and out. 211 have exactly one of
each. Of the rest:

- *Tender Award Notification* drew one line from *Send awarding
  notification* to *Receive notification*, with *Awarded Notification* above
  it and *Unawarded Notification* below, and the model had the two boxes
  connected to nothing. The TC (2026-09-27): the line carries one of the two
  each time - the winner gets the Awarded Notification, every other tenderer
  the Unawarded one, as UBL.xml says under Awarding of Tenders. The model now
  has two exchanges, one through each document, the flows into them
  `alternative`s of one group, each saying `when` (`doc-01`); the one line
  stays in the layout as a `sharedLine` that draws them, so the render is
  byte-identical.
- One box for two exchanges in opposite directions (6, CPFR: Exception
  Notification (positive) on Exception Handling, Exception Monitor and Identify
  & Resolve; Forecast Revision on Create Order Forecast and Creating Sales
  Forecast; Exception Criteria (revision) on Establishing Collaborative
  Relationships): two ways in, two ways out, and the model did not say which
  goes with which - read literally, the Buyer's *Send Exception* could arrive at
  the Buyer's own *Receive & Resolve Exception*. The TC (2026-09-27): each way
  in passes to the way out into the other party (the in-flow's `passesTo`,
  `doc-02` .. `doc-07`); `validate` requires it wherever a document has two ways
  in and two out. The drawing keeps its one box.
- One sender, two receivers (a copy to each: *DespatchAdvice* on Fig C.1,
  *Bill of Lading* and *Waybill* on Initiate Freight Management) and two
  senders, one receiver (*Certificate Of Origin*, *Application Response* on
  Certification of Origin; *Remittance Advice*; *Forwarding instructions*):
  read as drawn, nothing to settle.
- A box with a way in and none out on the page hands over to the next figure
  (the CPFR positive responses, `q16`).

Names: the artwork writes some names other than UBL's document type -
"Import/Transit Customs Declarations" (plural), "Request For Proof Of
Reexportation" (UBL: Proof Of Reexportation Request), "Digital Capabilities"
(Digital Capability), "TILP (response positive)" (Trade Item Location
Profile), "Goodsitem" and "GoodsItem". The model keeps the artwork's words.
Roles: UBL.xml gives each document a submitter and a receiver; one figure
sends a document the other way - Export Customs Declaration returns the
stamped declaration from the Customs Party to the Exporter Party, which UBL
lists as sent by the Exporter only. Faithful, and kept.

Settled from the original and mentioned: four Goods Item Passport boxes read
"Goodsltem" or "Goodsitem" where the artwork writes "GoodsItem" (`text-25` ..
`text-28`), and on CPFR Identify & Resolve the reading took the left end of a
rounded box for a "1" ("Receive & Resolve 1 Exception"; `text-29`, with the
line measured again, `draw-09`). Each changes those words in the render only.

The actions (516). All have a name and a party. Looking at the ones with no
way in or out on the original found one model error (TC, 2026-09-27): on Fig
C.1 the line between the Seller's *change order* and the diamond under
*receive order* runs into the diamond - its arrowhead is drawn there; after a
change the Seller decides again. The reading had turned it round by the rule
that an unlabelled diamond takes one flow in and sends the rest out, which a
diamond merging two ways in does not follow (`model-05`; the render now
matches the original there).

Contract: a way in and a way out in the sequence (a precondition between the
parties is not one), or the model records that the artwork draws none (`unstated`
`wayIn` / `wayOut`, `act-01` .. `act-31`); `validate` checks it. The TC settled
the rest on the originals (2026-09-27), in three groups:

- *A path ends at a step with no end drawn (19).* Mostly receiving is the end
  of the story - *Receive & Resolve Exception* (6, CPFR), *Receive Bill of
  Lading / Waybill / Status Report* (6, Initiate Freight Management), *Receive
  application response* (2, Digital Agreement) - and four branches end in the
  decision's outcome: *Endorse CoO* (2), the Seller's *cancel order* on Fig
  C.1, *Adjust Order* on Fulfilment Despatch Advice; and *Perform Compliance
  Management* on IMFM takes only the Regulatory Information.
- *A path begins at a step with no start drawn (4).* *place order* (Fig C.1
  draws no start); *Create Item Information Request* on CPFR Creating Sales
  Forecast, a second beginning beside the path handed over from Create Joint
  Business Plan; *Receive Order Item(s)* on Fulfilment Despatch Advice, which
  starts when the goods arrive - the artwork draws their despatch, not their
  movement; *Report usage* on Utility Billing, connected to none of the
  supplier's other steps (the start leads into *Reconcile Charges*, as on the
  other two 2.5 billing figures).
- *Prior exchange of public keys (4, both Tender Contract figures)*: the
  precondition between the parties settled before (`flow-kind`), not a step in
  the sequence, so neither a way in nor a way out.

Nothing is added to the model; the ends and starts are for a redraw.

The flows (1,038: 555 control, 473 object, 5 goods, 3 information, 2
precondition). Contract: both ends are nodes of the figure, and the flow says
how its direction was settled; `validate` now checks the second. 951 were read
with high confidence. The rest were put beside the original, both ends zoomed:
the 45 read with medium confidence or settled by a notation rule away from a
start or end are all drawn the way the model has them, and are recorded as
confirmed in `tools/direction-verdicts.json` (now 71 entries: 70 as drawn,
1 corrected) - apart from the one the notation rule got wrong on Fig C.1 (`model-05`,
above). The six flows a person added (the two down a divider on Business Card
and Digital Capability, the four on Tender Award Notification) are marked as
settled by a person. The receive steps with no document coming in are
settled by rule: a document reaching them through a join (the catalogue
figures, CPFR Create Order Forecast), a line handed over from another figure
(CPFR), or goods arriving (Fig C.1's *receive goods*, the *Receive Order
Item(s)* steps) - drawn as goods flows on five figures, and not drawn on
Fig C.1 and Fulfilment Despatch Advice.

**Figure by figure, most complex first (from 2026-09-27).** With every element
kind under contract, each figure is gone over with the TC: the latest SVG
coloured by element kind beside the original, the model read back, and the
differences shown.

- *Intermodal Freight Management (1 of 78).* Model correct and complete. Two
  drawing points, settled: the lane titles and the phase titles up the gutter
  are set bold in the artwork and were drawn regular. Title weight is now
  measured (`title_is_bold` in extract_graph.py: stem width against the
  letters' own height - 0.11 to 0.18 regular, 0.20 to 0.28 bold over the 78,
  whatever the face) and drawn: the layout's `titleBold` on a lane or a band,
  `bold` on a title moved to a phase. 14 figures have bold titles (Fig C.1,
  IMFM, five CPFR phase titles, seven 2.3 customs figures, Waste
  Notification). And "AnnounceTransport Services" is the artwork's typo: model
  and drawing read "Announce Transport Services", recorded in
  `tools/artwork-faults.json` (`text`).
- *Initiate Freight Management (2 of 78).* Model correct and complete. The
  start is drawn on the line between Consignee and Consignor, with a line to
  each party's *Request Logistic Service*: the Ordering process sets off both,
  so it stands between them (`start-04`; the reading had put it in the
  Consignee's column). "Forwarding instructions" was misread for the
  artwork's "Forwarding Instructions" (`text-30`). Two lines sit a few pixels
  off the original (into the Consignor's *Receive Waybill*, and from its
  *Request Logistic Service*), invisible at normal size: accepted.
- *Update Catalogue Pricing, Create Catalogue, Update Catalogue Item
  Specification (3-5 of 78).* Models correct and complete; SVGs faithful, a
  few line ends some pixels off (accepted). For a future release: on all
  three a document runs straight into an end with no step that receives it,
  and the preparing step has two ways in (a start or a loop, and the fork)
  where "either" is meant - in UML two ways into a step mean "both"; a merge
  diamond would say it. The fork and join bars stay black (the TC,
  2026-09-27), though the artwork fills most of them dark grey.
- *Tender Contract Information Preparation (6 of 78).* Model correct and
  complete (the kind 8 text and the "Above Thresholds?" question settled
  before); SVG faithful.
- *Digital Agreement (7 of 78).* Model correct and complete. The lane titles
  were drawn at the labels' size, about 24% narrower than the artwork's; over
  the 78 a third of the titles were 10-28% off, either way. Titles (and words
  set as one, the CPFR phase titles) are now set at the size and width the
  artwork gives them, as label lines are: the size from the height of the
  letters (cap height 0.716 of the type size, plus the descender where one
  drops), the width from the title's own extent, the baseline where the
  letters stand (spec_from_model.py). A title whose box is far from its
  neighbours' size takes theirs. Measuring showed four boxes stretched to the
  frame (IMFM's Transportation Network Manager, three Goods Item Passport
  titles): the extractor now leaves a rule running through the title cell
  out of it. The two-line titles of three 2.3 figures keep the labels' size.
- *CPFR Create Joint Business Plan (8 of 78).* Model correct and complete.
  The originals stop most arrowheads a small gap short of their target; ours
  touch it. Standing rule (the TC, 2026-09-27): small arrowhead and line-end
  differences are not blocking, and are not raised figure by figure.
- *Certification of Origin (9 of 78).* Model correct and complete, as drawn.
  For a future release: *Receive Response* has two ways out with no
  decision; the accepted outcomes (*Endorse CoO*) never reach the Exporter.
- *IMFM Basic Transport Execution Plan (10 of 78).* Model correct and
  complete. "EvaluateTransport" (twice) is the artwork's typo, put right in
  model and drawing and recorded in artwork-faults.json (`text-31`,
  `text-32`); the lower "[no]" was measured with the diamond's edge in its
  box and drawn too large (`draw-10`, `draw-11`). It also stood against the
  diamond's corner, too high, in the artwork; the TC (2026-09-27): set it
  beside the branch it labels, the line down to *Reject Transport Execution
  Plan*. A layout correction may now say it `departs` from the artwork on
  purpose: the checkers are told where the artwork's words are (`wasAt`), so
  a deliberate improvement is not reported as a missing text.
- *CRP Initial Stocking by Retailer (11 of 78).* Model correct and complete.
  Two drawing points, both left as they are (the TC, 2026-09-27): the steps'
  corners come out rounder than the artwork's (its top edges slope a pixel or
  two and the corner reading falls back to a median that is itself thrown -
  also on ROCD Initial Stocking, the VMI figures, CRP Sales and Inventory
  Movement): the SVG's corners are kept. And the drawing tool's "line jump"
  where the goods line crosses the divider is not drawn.
- *CPFR Creating Sales Forecast (12 of 78).* Model correct and complete.
  No grey in the diagrams (the TC, 2026-09-27): the three dividers the
  artwork draws grey (two on Fig C.1, one here) are drawn black at their own
  width; the layout keeps the artwork's tone, and the checker counts the grey
  line as the artwork's ink. The real SVGs now use black and white only.
- *Tender Contract Post-award (13 of 78).* Model correct and complete; SVG
  faithful.
- *ROCD Initial Stocking (14 of 78).* Model correct and complete. Two drawing
  points, fixed (the TC, 2026-09-27). The words set on the page - guards,
  decision questions, notes - were drawn at the labels' size and squeezed
  into their measured width; here "False", "True" and "Changes are
  necessary?" came out a quarter too tall. They are now fitted as the titles
  are, line by line: the size from the letters' height, the baseline where
  they stand, a line more than 15% off the figure's usual size taking the
  usual (spec_from_model.py; over the 78 most such texts were within 10-20%
  of the labels' size, seven figures clearly smaller). And the divider
  between *Despatch Advice* and *Receipt Advice* was drawn twice, a straight
  rule and beside it the stretch where the artwork's line leans 7px, read as
  a separate piece. Settled with figure 17 by a standing rule (below): one
  straight line.
- *UBL 1.0 Procurement Process (15 of 78).* Model correct and complete (43
  flows; "decision if item(s) rejected" is a step, as drawn; no start, as
  recorded). The scan is too blurred for the weight reading: the documents'
  names, bold upright in the artwork, were drawn bold italic, and about half
  the steps' names bold where all are regular. Set as drawn for the whole
  figure (`draw-13`, `draw-14`, the new `label-style` correction; the layout
  may now say a node's words are upright). The dashed lines' small heads
  come out as the usual open heads: not blocking.
- *CPFR Create Order Forecast (16 of 78).* Model correct and complete: the
  two "No" lines in from CPFR Exception Handling onto the fork, the join
  before *Receive*, "Order Forecast Accepted ?" as the decision's question,
  *Forecast Revision (order)* one box for the two revisions (paired), and
  *Forecast (order - positive response)* out to Identify/Resolve. One drawing
  fault, fixed: the reading ended the two "No" lines short and a few pixels
  off at each end, so they were drawn slanting with a twisted head; now
  straight down onto the bar as drawn (`draw-15`, `draw-16`).
- *VMI Initial Stocking (17 of 78).* Model correct and complete (19 flows).
  Standing rule (the TC, 2026-09-28): **a lane divider is always drawn as one
  straight line**, not copying the artwork's small leans and offset
  stretches. The layout keeps what was read (the rule and, beside it, the
  pieces where the line leans, on nine CRP, ROCD and VMI figures); a piece
  lying along a rule is drawn as part of it, the rule running over both at
  its own position (spec_from_model.py). The checker takes the artwork's
  divider strokes (runs of 40px or more along the rule, within 12px of it) to
  lie where the SVG's are, row by row where both have one, so the lean is not
  counted and a missing divider still is (verify_conversion.py). Over the 78
  this took 2,500 px of line-work findings off, 2,900 on VMI Price
  Adjustment alone.
- *Fulfilment Receipt Advice (18 of 78).* Model correct and complete (24
  flows; the three guarded branches of Determine Action; *Cancel receipt
  notification* and *Send Receipt Advice* in a loop). Two drawing faults,
  fixed: the two dashed flows had gaps four times too long - each line is too
  short for the reading to measure its own pattern, and it took one from
  elsewhere - now dashes of 23 and gaps of 8 as on the original, starting
  with a dash (`draw-17`, `draw-18`; the upper one also straight down, its
  ends read 7px apart); and two of the three branches left the diamond from
  its edges instead of from its bottom corner (`draw-19`, `draw-20`).
- *VMI Returns by Producer (19 of 78).* Model correct and complete (17
  flows); SVG faithful. It raised the line jumps. Every crossing in the 78
  was found from the models and looked at on the originals: 35 flows cross a
  lane divider, 20 a CPFR phase boundary, and 13 cross another flow. The
  artwork draws most of them plain, and jumps at eight, in two ways: a curl
  on the divider (three goods lines: CRP Initial Stocking by Retailer, ROCD
  and VMI Initial Stocking) and a clean half circle, the "hop" (two goods
  lines over the divider, on VMI Permanent Replenishment and this figure;
  three flows over another flow, on Self Billing with Credit Note and Billing
  with Credit and with Debit Note). Standing rule (the TC, 2026-09-28): **a
  hop is drawn only where two solid flows cross** - never at a lane divider
  or a phase boundary, which no one reads as joining a flow, and never where
  either line is dashed, whose gaps already show it. The steeper line hops
  (at a right angle, the vertical one), as on all three of the artwork's hops
  between flows; the half circle bows up, or right on an upright line; its
  radius is half the arrowhead's length. That is five hops in four figures:
  the artwork's three, and two on Procurement, where diagonals cross near the
  diamonds with nothing to show they do not meet. The hops are worked out
  from the drawn lines (build_diagram.py) and carried on the flow in the SVG
  (`data-hops`); the checker leaves the disc of each out on both sides
  (verify_conversion.py), since it is a deliberate difference. draw.io's own
  line jumps are not used: it jumps every crossing, dashed or not.
  Where a flow crosses a lane divider, the checker does not count the
  crossing's neighbourhood (a disc the size of the arrowhead), since the
  artwork's curls and hops there are left out on purpose.
- *VMI Permanent Replenishment (20 of 78).* Model correct and complete (21
  flows). One drawing fault, fixed: the decision's question is set on two
  lines in the artwork; the reading took it as one line with the diamond's
  corner in its box, and it was drawn as one squeezed line over the diamond
  (`draw-21`). Its goods line's hop over the divider is drawn as a plain
  crossing (standing rule above).
- *Tender Contract Information Notification (21 of 78), Fulfilment
  Despatch Advice (22 of 78).* Models correct and complete; SVGs faithful.
  On 22 the gaps the artwork leaves (no way into *Receive Order Item(s)*,
  none out of *Adjust Order*, Determine Action's branches without guards)
  are recorded as unstated.
- *Goods Item Passport Return (23 of 78).* Model correct and complete (23
  flows). One drawing fault, fixed: the last step, *Receive Goodsitem
  Passport*, was drawn bold where every step is regular (`draw-22`). The
  weight reading mixes bold and regular steps on only two other figures,
  Goods Item Passport Approval and Billing with Debit Note, to be looked at
  when they come up.
- *Goods Item Passport Presentation (24 of 78).* Model correct and complete
  (23 flows); SVG faithful.
- *Goods Item Passport Approval (25 of 78).* Model correct and complete (23
  flows). Weight misread three times: *Draft Goodsitem Passport*, the
  Exporting Customs Party's *Apply Stamps And Signature* and the "OK?" in the
  diamond were drawn bold where the artwork sets them regular (`draw-23` to
  `draw-25`). "OK?" was read bold on two more figures, Export Customs
  Declaration and Goods Certificate Export, and is set regular there too
  (`draw-26`, `draw-27`); no other decision's words were read bold.
- *Tender Contract pre-award (26 of 78).* Model correct and complete; SVG
  faithful.
- *Self Billing with Credit Note (27 of 78).* Model correct and complete (22
  flows). Two drawing faults, fixed: the [incorrect information] branch from
  Validate Invoice to the bar was drawn dashed and with a corner - the guard's
  words cross the solid line, and the reading took the breaks for a dash
  pattern (`draw-28`); and "Reconcile" in the supplier's diamond was measured
  from its second letter, the "R" touching the diamond's edge, and drawn
  squeezed (`draw-29`; the reading's word was "econcile", put right before).
- *Billing with Credit Note (28 of 78).* Model correct and complete (20
  flows); SVG faithful. The branch from the customer's Reconcile Charges to
  *Send Account Response* is the unguarded otherwise case, recorded.
- *Billing with Debit Note (29 of 78).* Model correct and complete (20
  flows); SVG faithful. The two debit-note steps are set in regular type
  where every other step (and both credit-note steps on the twin figure) is
  bold: the artwork's own inconsistency, kept, and recorded in
  `tools/artwork-faults.json` (`drawn`). For a future release: the supplier's
  Reconcile Charges sends [initial charges or under charged] to *Raise
  Invoice* and [under charged] to *Raise Debit Note* - the two guards overlap,
  so "under charged" does not say which way to go (on the credit-note twin
  the second branch is [over charged]). The fault is new in 2.5: UBL 2.0 to
  2.4 draw a different process, the Customer raising the Debit Note when
  [over charged] (os-UBL-2.4 art/UBL-2.0-BillingwithDebitNoteProcess.png,
  the same drawing since 2.1, and in 2.0 as a JPEG), with the Supplier's
  diamond sending only [initial charges or under charged] to *Raise
  Invoice*. The 2.5 figure moves the Debit Note to the Supplier (the text
  after it now says the Supplier specifies the tax requirements) and was
  redrawn from the credit-note figure, keeping that guard; most likely the
  invoice branch should read [initial charges]. The figure is published
  unchanged in the OASIS Standard (os-UBL-2.5, 12 August 2026, the same
  guards; the file there is a different export of the same drawing). The TC
  (2026-09-28): to be fixed in UBL 2.6. (Approved Errata, TC Process 2.9, are
  limited to corrections that are not a Material Change, which a changed
  guard in a process diagram arguably is.)
- *Tender Qualification Information (30 of 78).* Model correct and complete
  (8 flows). The document names came out a fifth too tall, squeezed into
  their width: every node's words were set at one size, the steps', where
  some figures set documents smaller or larger than steps (Tender
  Qualification Application and Unsubscribe from Procedure 20-24% larger,
  Self Billing with Self Billed Credit Note's steps 19% smaller). Node words
  are now set per kind (the TC, 2026-09-28, "as long as the texts stay inside
  the boxes"): steps, documents and decisions each at the median size of
  their kind's label lines on the figure, from the letters' height, each line
  where its letters stand, and capped so every line stays inside its box
  (spec_from_model.py). Checked on all 78: no line outside its box, 14,000 px
  of line-work findings fewer (Enquiry and Tender Status 4,500 each,
  Procurement 2,800), no verdict changed.

**The notes for a person, all 266 settled by eye (2026-09-27).** The sweep
leaves, per diagram, notes where the reading could not be sure; each was looked at
beside the original and our render (side by side, crops of the place). Most are
the reading being careful, not something wrong, so they are summarised by kind
with one example, and only what is wrong is itemised - in `pendingTextFixes` and
`pendingDrawingFixes` in `tools/model-corrections.json`, to be fixed in the one
pass at the end.

| kind | n | what it turned out to be | example |
|---|---|---|---|
| dropped region | 78 | blank space closed in by connectors, dividers and the frame; never a missing shape | Create Catalogue: the rectangle between *Application Response* and *Catalogue* formed by two flows |
| arrowhead unmeasurable | 48 | the head is drawn and points the way the model says; it was unmeasurable because another line meets it. Two were not: see below | Billing with Credit Note: the four heads meeting on *Reconcile Charges* |
| sub-character region | 35 | the inside of a letter (O, D, Q) in a lane title or decision | "OK?" on the Tender figures |
| kept on outline | 31 | a real node with flows on every side | *Reminder* on Reminder for Payment |
| unexplained line-work | 24 | strokes of letters, and a dashed corner of a phase box, all drawn | the "T" of "Transport" on Certification of Origin |
| no weight split | 21 | the documents are found by shape instead of stroke weight, and all are there; the note's wording ("no object node could be identified") is out of date | Business Card |
| ring stroke unreadable, arrowhead size | 10 | finals and heads drawn right | the finals on the 2.3 customs figures |
| empty box, rule through shape | 8 | blank space closed in by lines; a connector arriving from the previous figure | Payment Notification; CPFR Exception Handling |
| edge direction, isolated node, mark across rule | 11 | already settled: 11.1 (directions), 11.4 (Fig 28), `q11` (the break marks) | - |

What was wrong, found this way and not by the checks: two model errors
(Fulfilment Despatch Advice has the flow between *Send Despatch Advice* and
*Adjust supply status* reversed, its head read as the text "AN"; CPFR Create Joint
Business Plan has an invented second flow made from the top of a "No" arrow), two
misread texts ("information" for "information]", "Above P" for "Above"), three
text lines measured to take in a neighbouring shape and drawn stretched, the
upright document labels of six 2.3/2.5 figures drawn italic, "(from Business
Processes)" squashed onto one line, and the notched arrowheads of ten 2.3 figures
drawn as plain triangles. The verifier missed them because each costs few pixels
and the text check accepts a close reading; a side-by-side look found them.

**Misread text is noted, not yet fixed.** A text fix changes what is drawn, and
so the verifier's findings; the TC's instruction is to make them all in one pass
at the end. They are collected in `pendingTextFixes` in
`tools/model-corrections.json` as they are found - 22 so far, seven of them the
degraded labels of Fig C.1 - each ready to become a `retext` correction. The
machinery is in place and was tried on all 17: every one changed exactly its
words and nothing else, and for the diagrams it touches `model_io.py` writes a
`-graph-corrected.json` for the verifier, the model sheet and the review marks,
which would otherwise report a correct render as a text error.


**Points for a future UBL release, not for this conversion.** Some questions go
beyond what a drawing says into whether it says the right thing. The model
stays faithful to the artwork, and these are kept here for the TC to take up
when the diagrams themselves are next revised.

- *Fig 37, Punch-out Sourcing (raised 2026-09-27 with `q7`):*
  - **Who builds the basket?** The artwork puts *Build shopping basket* in the
    Seller Supplier Party's column. But in punch-out it is the Originator who
    browses the catalogue and fills the basket, on the Seller's system. UBL.xml
    says so itself: "The Originators leave ... their system and interact with the
    Seller's catalogue to locate and order products". The column may be showing
    whose system it is rather than who acts. A revised diagram could say this
    plainly, for instance with the action in the Originator's column and the
    Seller's catalogue application named as where it happens.
  - **UBL.xml's text reads "Seller" where "Originator" seems meant.** It says
    punch-out lets an Originator access a Seller's catalogue application "from
    within the Seller's own procurement application", which by the rest of the
    paragraph should be the Originator's own. Whose procurement application
    "transparently gathers pertinent information" is unclear for the same
    reason.
- *Fig 14, CPFR Exception Monitor (with `q9`):* redraw the connector from the
  Buyer's *Send Exception* to *Exception Notification (positive)* like its mirror
  on the Seller's side. A layout matter, for the session that re-lays diagrams.
- *Goods Item Passport figures (found 2026-09-27):* the artwork writes the name
  both "GoodsItem" and "Goodsitem". The model follows the artwork in each place;
  a revision could make them all "GoodsItem".
- *Utility Billing (with `q12`):* drop "(from Business Processes)" in a redraw:
  the package means nothing to a reader of the specification; if the link
  matters, refer to the billing section instead.
- *Documents across an intermediate lane (with `q14`):* the artwork puts such a
  box next to the receiver 5 times and next to the sender 4 times. A redraw
  could agree a convention - simplest, always on the divider next to the
  receiver.
- *Freight Status Reporting (with `q15`):* "Receiver Party" is a questionable
  name for a party that both receives a request and sends the status report;
  and the divider marking off the self-initiated start could go - in BPMN it
  would be a timer start inside the Receiver Party's lane.
- *Waste Movement and Waste Notification (with `q15`):* the column titles read
  "Senderparty" and "ReceiverParty"; UBL.xml says "Sender Party" and "Receiver
  Party".
- *CPFR phase boxes:* size each to its steps and the words that belong to it,
  with the same margin on every figure (Fig 9 is far too wide; Fig 7's "Retail
  Event Accepted ?" pokes out of its box).
- *Decisions (completeness sweep):* guard every branch and give every diamond its
  question. Fig C.1, Certification of Origin and Fulfilment Despatch Advice can
  take their guards from the step each branch leads to; Create Catalogue's
  diamond can say "Respond to Request" as its Update Catalogue siblings do; the
  2.5 billing figures' unlabelled branch out of *Reconcile Charges* can read
  [otherwise] or [dispute charges].
- *Intermodal Freight Management:* split *Provide Transportation Network
  Information* into one step per phase (Planning, Execution).
- *Party names:* one style across the figures, and one name per role (Buyer /
  Buyer Party / Originator Customer Party ...), checked against the party roles
  UBL.xml gives for each document.
- *Self Billing (text sweep):* the choice after *Raise Self Billed Invoice*
  - accepted, or a reply comes - drawn as a branch, in BPMN an event-based
  gateway: an Application Response, a Credit Note, or no reply meaning the
  charges are accepted.
- *Tender Contract Information Preparation (text sweep):* "Publish Official
  Journal" would read "Publish in Official Journal"; and the box says *Prior
  Information Notice* where both steps call it a *Simplified Notice*.
- *Ends and starts (actions sweep):* an end after each of the 19 steps a path
  stops at, and a start before the 4 it begins at. On Fulfilment Despatch
  Advice a goods flow from *Despatch Order Item(s)* to *Receive Order
  Item(s)* (as in 11.6), and on Fig C.1 one into *receive goods*; on Utility
  Billing connect *Report usage*, for
  instance alongside *Raise Invoice*.
- *Tender Award Notification (documents sweep):* draw the two notifications as
  two exchanges, or with a decision (won / not won), rather than two boxes on
  one line.
- *CPFR two-way documents (documents sweep):* draw one box per direction, or
  say plainly that either party may send it to the other.
- *Document names (documents sweep):* use UBL's document type names as they
  are ("Import Customs Declaration", "Proof Of Reexportation Request",
  "Digital Capability", "Trade Item Location Profile"), one spelling of
  "GoodsItem"; and on Initiate Freight Management "Send Bill of Lading to
  Consignor" and "Send Waybill to Consignor" send to the Consignee as well.
- *Export Customs Declaration (documents sweep):* the stamped declaration is
  returned from the Customs Party to the Exporter; UBL lists the document as
  sent by the Exporter only. Either the roles in UBL.xml grow a second
  direction, or the return is drawn as a different document.
- *Tender Guarantee Deposit (with `q8`):* obtaining the guarantee from a
  financial institution is shown as one step with no document. Should UBL ever
  cover that exchange, the financial institution would become a party with its
  own column.
