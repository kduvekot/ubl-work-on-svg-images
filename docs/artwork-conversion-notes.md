# UBL artwork conversion — working notes

Handover notes for the effort to recover **editable sources** for the UBL
specification artwork. Written at the end of a working session so the next one
does not have to rediscover any of it.

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
art/NAME.png  ─▶ extract_graph.py    ─▶ NAME-graph.json   (semantic graph)
              ─▶ spec_from_extract.py ─▶ NAME-spec.json    (build spec)
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
part of this work. Geometry can be re-laid-out and the notation re-rendered as
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

---

## 10. Open items

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

### 11.5 Still to walk through

- the 15 "work crossing between parties goes through a document" findings
- the 11 dead-end actions and 7 unlabelled branches (sampled and faithful:
  *Receive Bill of Lading*, *Receive application response*, *Endorse CoO* are
  drawn with nothing leaving the box; 34 of 40 unlabelled branches have no word
  anywhere near them in the artwork)
