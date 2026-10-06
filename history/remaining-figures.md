# The figures that were still to do

Written 2026-10-05, after Group A, for the sessions that carried on: what was left then (the 8:
the 3 of Group B, the 4 of Group C and the one no longer used), what each figure is, what source
it had, and how to go about it. All but that one are done. The same rules as for the others
(README, "The export's rules": draw.io as the source, an SVG that is real vector, black and
white print PNGs, one text size) applied, and `history/group-a/README.md` is the worked example
of a figure that is not a UML activity diagram.

**State:** 96 of the UBL repository's 97 figures are drawings in `diagrams/` (78 UML activity
diagrams, 7 illustrations, 4 of Group A: three the TC's own drawings as they are, and Ordering
redrawn from the TC's bpmn-js SVG; 3 of Group B and 4 of Group C, done 2026-10-05:
`history/group-b/`, `history/group-c/`). **1 is left**: the one that is no longer used.

How the figures were found: the 97 files of `history/svg-images/` (Ken Holman's conversion) against
`diagrams/`; the PNGs are in the UBL repository's `art/` (clone `ubl-2.5`, see `history/docs/running.md`),
and `UBL.xml` there says which figures the specification uses. Sizes below are the PNGs'.

## Group B: phase and overview figures (3 figures, one session) - DONE 2026-10-05, `history/group-b/README.md`

| figure | PNG | what it is | source |
|---|---|---|---|
| `UBL-2.2-IMFM-GenericIntermodalFreightProcess` | 3425x798, greyscale | chevrons for the phases of an intermodal freight process, with their names; the smallest of the 8 | none in the UBL repository. Ken Holman's `history/svg-images/` SVG is a hand-made Inkscape file of chevrons with 6 texts (a start, not the truth: the PNG is) |
| `UBL-2.2-Open-edi-Overview` | 3425x2667, RGB | Open-edi's overview: boxes, arrows and text (ISO/IEC 14662); likely coloured | none; `history/svg-images/` has the PNG in an SVG |
| `UBL-2.2-Open-edi-Application` | 3425x3184, RGB | the Open-edi application figure; the biggest | none; the same |

**Approach:** no source exists, so these are drawn from the PNG (for Group A
the TC's own sources existed and were adopted unchanged). **The basis is always the PNG of the
UBL repository's `art/`** (`ubl-2.5`, `3d81e8a`), never Ken Holman's `history/svg-images/`: his
two Open-edi SVGs only wrap that very PNG (checked byte for byte, 2026-10-05), and his IMFM SVG is
a hand-made copy that is **not** the figure (it has 3 captions where the PNG has 7 lines, and
the chevrons differ). Read the PNG (the measuring
tools of `history/tools/` and `history/illustrations/` help: `extract.py`, `fit.py`), draw
with draw.io's shapes at a scale where the text is 12 px (the 12 px rule: the PNG's text
height in pixels over 12 is the scale), compare with `history/group-a/compare_png.py`.

**Colour (checked 2026-10-05): there is none.** IMFM's PNG is 8 bit greyscale; the two
Open-edi PNGs are stored as RGB but every pixel is a pure grey (largest difference from its
greyscale value: 0), and the only tones are black, white and the grey of antialiased edges. So
nothing carries a meaning and nothing is asked of the TC: the drawings are black and white, as
the 78 are, with 1 bit print PNGs. The three are one session because they are all boxes,
chevrons and plain arrows.

## Group C: reference figures (4 figures) - DONE 2026-10-05, `history/group-c/README.md`

| figure | PNG | what it is | source |
|---|---|---|---|
| `UBL-2.2-DefaultValidation` | 3425x2248, greyscale | the default validation: a chain of boxes (schema, code lists, business rules) | none |
| `UBL-2.2-SchemaDependencies` | 3425x1957, RGBA | the dependency of the UBL schemas on one another (documents, the common library, ...) | none |
| `UBL-2.2-UDT-QDT` | 3425x2200, RGBA | UDT and QDT: the unqualified and qualified data types, boxes and relations | none; probably a UML class diagram |
| `UBL-2.3-ModelRealization` | 3425x2013, RGBA | how the model is realised: the largest share of text and boxes | none |

**Approach:** these are not process flows; they are tables, class-like boxes and dependency
arrows, so draw them with draw.io's own shapes (UML class, rectangles, plain arrows) with
the text live: do not trace them. In `history/svg-images/` each is only the PNG in an SVG
(`<image>`), so the PNG is the only reference. The question before the session, if one of
them were really a screenshot (a schema fragment, a generated diagram), whether to redraw it
or keep it as an image with an SVG wrapper (the ISO would not accept it: README, "The export's
rules"), did not arise: all four are boxes and arrows, and are drawn
(`history/group-c/README.md`). (The order advised then: `UDT-QDT` and `SchemaDependencies`
first, as the most likely to be pure boxes and arrows, then `DefaultValidation` and `ModelRealization`.)

## Not to do

`UBL-2.0-BillingwithCreditNoteProcess` (3425x1813) is in the UBL repository's `art/` and not
used: `UBL.xml` does not cite it. Ken Holman's SVG of it is real vector (34 texts). Whether it
stays, and what then: README, "Questions for the TC", A5.

`UBL-2.2-UseCase` and `UBL-2.2-UseCaseOverview` (checked 2026-10-06): `UBL.xml` names them only inside
an XML comment, and no branch of the UBL repository has ever had a PNG or a source of them. Nothing to do.

## Where the originals may still be

Searched 2026-10-05 (details: `history/group-a/README.md`): the UBL repository (all 31
branches), docs.oasis-open.org, the UBL JIRA. None has a source for these 8 figures; JIRA's
UBL-171 says the sources of the original swim-lane diagrams are not available. **Not looked at,
because the OASIS mailing-list archives (`lists.oasis-open.org`, `lists-archive.oasis-open.org`)
refuse a script (Cloudflare's bot check) and need a person in a browser:** the `ubl` list's
posts of 2016-2020 around the figures' creation (UBL 2.2: the IMFM, Open-edi, Schema
Dependencies and UDT/QDT figures; UBL 2.3: Model Realization), where an attachment may be
a source. The search, by someone with a browser: README, "Questions for the TC", C4. If one is
found, put it in `history/<group>/sources/` and say so here.

## Before the UBL repository gets any of it

The export (`to-ubl-repo/`) adds or replaces per figure `images/<figure>.drawio`, `.svg`,
`art/<figure>.png`, `htmlart/<figure>.png` (README, "The export's rules"). For Group A
the sources are the UBL repository's own, so the commit **changes three of them only in form** (the
`.drawio` uncompressed and in the editor's form with one added property; Procurement's stray line out)
and **replaces Ordering's bpmn-js SVG** by a draw.io BPMN drawing made from it, with that drawing's
export (`history/group-a/README.md`, "Ordering as a draw.io BPMN diagram"); and it replaces the PNGs
by black and white print ones (Business Information's: grey): say so in the message.
**Future session, required by the UBL editor, Kees Duvekot:** real BPMN 2.0 files for the BPMN figures (Ordering,
Business Information) - `history/group-a/README.md`, "Future session".
**To decide with the TC first:** README, "Questions for the TC", A.
