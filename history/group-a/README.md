# Group A: the four figures that had a source

Done 2026-10-05. The four of the UBL repository's other 12 figures
(`history/../remaining-figures.md`) that are not UML activity diagrams but already
had a source in the UBL repository's `images/`: two BPMN collaborations, and two
maps of phases. They are drawings in `diagrams/`, exported to `to-ubl-repo/` like
the other 85: **89 figures now**.

| figure | notation | the source it came from | how the drawing was made |
|---|---|---|---|
| `UBL-2.3-OrderingProcess` | BPMN: 2 pools, 14 tasks, 2 gateways, 7 events, 11 sequence flows, 6 message flows | `images/UBL-2.3-OrderingProcess.svg`, made with bpmn.io (bpmn-js), 2019 | **redrawn** from that SVG's elements and places, as draw.io's BPMN shapes: `build_ordering.py` |
| `UBL-2.4-BusinessInformation` | BPMN: 3 pools, 8 tasks, events, message flows | `images/UBL-2.4-BusinessInformation.drawio`, draw.io 20.8.4, 2023 | **adopted**: the same drawing, uncompressed, in the editor's form, with ids and kinds: `adopt_businessinformation.py` |
| `UBL-2.3-Pre-awardProcess` | phase map: 13 steps of 3 parties, 15 lists of documents | `images/UBL-2.3-Pre-awardProcess.drawio`, draw.io 13.0.3, 2020 | **rebuilt** from its places at 0.3 of its scale: `build_preaward.py` |
| `UBL-2.3-ProcurementProcess` | phase map: 2 phases and a milestone | `images/UBL-2.3-ProcurementProcess.drawio`, draw.io 13.0.3, 2020 | **rebuilt** at 0.3 of its scale: `build_procurement.py` |

The four sources are in `sources/`, as the UBL repository has them (`ubl-2.5` at
`3d81e8a`, identical on `main`, `ubl-2.4-os`, `ubl-2.3-os-iso`, `review` and
`tsc-ubl-2.5-experimental`). The PNGs they replace are not copied (`art/` in the UBL repository).

## Why one was adopted and two rebuilt

- **BusinessInformation** was already a proper draw.io BPMN drawing (pools and lanes
  with stack layout, tasks as containers, flows attached). Nothing to improve but
  the form, so it is kept as drawn, and only given the model's ids and kinds.
- **Pre-award** and **Procurement** were drawn in a way that does not edit well: at
  3425 px wide with 60 px text and 8 px lines (so, not at the scale the 85 others are
  drawn at), the outline of each arrow-shaped phase as five loose lines, each
  dashed list of documents as two loose lines, groups nested five deep. They are
  rebuilt with draw.io's own shapes (a chevron `step`, a pentagon as a `singleArrow`
  of full arrow width, a rhombus) and one dashed corner line per list of documents.
  The scale is 0.3: the 70, 60 and 40 px text becomes 21, 18 and 12 px, and 12 px is
  draw.io's own size, which the lists of documents (the most text) now use without
  setting it. The 8 px lines become 2 px: line weights stay whole (README, "drawn at").
- **Ordering** has no draw.io source, only the bpmn-js SVG. The SVG says where
  everything is (it is an export of the model), so it is read and drawn again as
  draw.io BPMN shapes: same places, sizes and bends; the BPMN ids (`Task_1bnlp2b`,
  `MessageFlow_0w3w0y5`, ...) are kept as `ubl-bpmn-id`. Its original BPMN 2.0 XML
  would be better still (below).

## Decisions to show the TC

- **The grey bars of BusinessInformation's tasks are white.** The drawings are black
  and white only, and the print PNG is 1 bit, where the light grey (`#C0C0C0`) would
  vanish; the rules that bound the bars stay. The htmlart PNG and the SVG show them white.
- **BPMN arrowheads stay BPMN's:** a filled head for a sequence flow, an open
  triangle for a message flow with a circle at its sender (which the UML figures'
  one open 10 px head would take away). The "3 times its head" rule is not applied
  to these four.
- **BPMN line weights:** Ordering's lines are 2 px as in its SVG (its message flows
  1.5 there, 2 here); BusinessInformation's are the 1 px of its source.
- **Flow names are texts beside the flow** (a `text` with `ubl-for` naming the flow), as in
  BusinessInformation's source, not the flow's own label.

## How they are checked

`tools/check_drawio.py` knows a figure of another notation: it is marked by
`ubl-notation` (`bpmn`, `phase-map`) on one element, and is checked for ids and kinds,
flows attached at both ends, and that what a text, a bracket or a list of documents
is for (`ubl-for`, `ubl-steps`) is in the drawing. `check_svg.py` checks the export
as it does the others (89 of 89 `ok`).

Against the UBL PNGs (`compare_png.py`: the export put where the PNG has its ink, then
the share of ink with no ink of the other within 4 px at the PNG's size), 2026-10-05:

| figure | PNG ink not in the export | export ink not in the PNG |
|---|---|---|
| Ordering | 2.1 % | 3.6 % |
| Pre-award | 8.2 % | 6.0 % |
| Procurement | 1.8 % | 1.3 % |
| BusinessInformation | 0.7 % | 13.2 % |

All of it is letter shapes (Helvetica of the Mac that made the PNGs, against Liberation
Sans here) and dash phases, but for BusinessInformation, where the 1 px lines of the PNG
are antialiased and the 1 bit print of the export draws them 2 px wide, which is where
the 13 % is. Nothing is missing, moved or misdrawn in any of the four: each
`<figure>-diff.png` that `compare_png.py` writes was looked at.

## Run again

```sh
python3 history/group-a/build_ordering.py        # each writes diagrams/<figure>/<figure>.drawio
python3 history/group-a/build_preaward.py
python3 history/group-a/build_procurement.py
python3 history/group-a/adopt_businessinformation.py
python3 tools/check_drawio.py diagrams/UBL-2.3-*/*.drawio diagrams/UBL-2.4-BusinessInformation/*.drawio
NODE_PATH=$(npm root -g) node tools/export_drawio.js to-ubl-repo diagrams/UBL-2.3-OrderingProcess/*.drawio ...
python3 history/group-a/compare_png.py <ubl>/art to-ubl-repo/art <out> <figure> ...
```

After that the drawings are the source: edit them in draw.io; the scripts are how they
were made, and need not be run again (they would overwrite an edit).

## Where the originals might still be (searched 2026-10-05)

- **UBL repository, all 31 branches:** the four above, nothing else, and no `.bpmn` file.
- **docs.oasis-open.org** (`UBL-2.x/art/`, the release directories): the PNGs only.
- **The UBL JIRA** (issues.oasis-open.org, reachable; its REST API answers): UBL-171
  ("Accepted order are canceled") is where the Ordering diagram was redrawn in 2019. It has
  no attachment ("we can not attach documents to Jira Issues directly") and says, 2019-05-06,
  that the sources of the original swim-lane diagrams are not available. No issue mentions
  draw.io, Visio or the other figures' sources.
- **The `ubl` mailing list, 2019-05-07,** "UBL-171 - BPMN diagram + SVG"
  (<https://lists.oasis-open.org/archives/ubl/201905/msg00011.html>, also on
  groups.oasis-open.org): **attaches `UBL-2.3-OrderingProcess.bpmn`**, the BPMN 2.0 XML
  made in bpmn.io, and the SVG. The attachments could not be fetched from here:
  lists.oasis-open.org and lists-archive.oasis-open.org (the new archive) answer a script, and
  headless Chromium too, with Cloudflare's "verify you are not a bot" check (403), and
  groups.oasis-open.org lists the attachment names only, without a link, for a visitor
  who is not logged in. **If the `.bpmn` is found (its author has it, or a TC member's
  mail), put it in `sources/`:** it has the model, and `build_ordering.py` can read the
  elements from it instead of from the SVG (the SVG's ids are the BPMN ids).
