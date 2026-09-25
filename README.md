# ubl-work-on-svg-images

We are working on converting all the current art work for UBL to SVG files going forward.

The `imageSummary.xsl` stylesheet is executed from the UBL repository directory, reading the local `UBL.xml` file and local `art/` directory to produce the result:
```
xslt2pe UBL.xml utilities/images/imageSummary.xsl ~/t/compare.fo new-dir=/Users/admin/t/new-images/ ; AHFCmd -d ~/t/compare.fo -o ~/t/compare.pdf -silent ; open ~/t/compare.pdf
```

## Converting the artwork

`tools/` holds a pipeline that reads a 600-dpi `art/` PNG and writes an editable
SVG plus a structural model, then renders that SVG back and compares it to the
original pixel for pixel. It covers the 78 UML activity diagrams.

```sh
git clone --branch ubl-2.5 https://github.com/oasis-tcs/ubl.git
JOBS=4 tools/verdict-sweep.sh ubl/art out tools/uml78-bycomplexity.txt
```

- **[`docs/running.md`](docs/running.md)** — how to run it: the artwork, what has
  to be installed, every entry point, and the numbers a run should reproduce.
- **[`docs/artwork-conversion-notes.md`](docs/artwork-conversion-notes.md)** — the
  working record: what each rule is for, what it was measured against, and what
  was tried and rejected.



