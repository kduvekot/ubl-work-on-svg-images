#!/usr/bin/env python3
"""The house-style demonstration: the same figures three ways, on A4.

    python3 house_demo.py <work-dir> <out.html> <figure> ...

For each figure <work-dir> holds <figure>-spec.json (the house spec,
house_style.py), <figure>-faithful-spec.json (the spec as measured) and
<figure>-house.png (the house drawing rendered at RENDER_SCALE). The page is
printed to PDF by house-demo.sh.

1. As published today: the committed SVG, at the column's width (145 mm), as
   the specification sets every figure.
2. The house style, fitted to the column: the same, with one look.
3. The house style at one scale: labels the same size on paper in every
   figure; the page grows to what the figure needs (A4, A4 landscape, A3).
"""
import html, json, os, sys

COLUMN_MM = 145.0              # 3425 px at 600 dpi: the width of 71 of the 78 PNGs
PT_MM = 25.4 / 72
LABEL_PT = 7.0                 # about the median printed label today (6.9 pt)
HOUSE_EM = 12.0
PAGES = [("a4", 180, 257), ("a4l", 267, 170), ("a3l", 390, 257), ("a3", 267, 390)]


def esc(s):
    return html.escape(s, quote=True)


def main(work, out, figures):
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    items = []
    for n in figures:
        f = json.load(open(os.path.join(work, n + "-faithful-spec.json")))
        h = json.load(open(os.path.join(work, n + "-spec.json")))
        acts = [x for x in f["nodes"] if x["kind"] in ("action", "object")]
        sizes = sorted(l["size"] for x in acts for l in x.get("labelLines", []))
        em = sizes[len(sizes) // 2] if sizes else f["font"]["node"]
        today_pt = em * COLUMN_MM / f["canvas"]["w"] / PT_MM
        fit_pt = HOUSE_EM * COLUMN_MM / h["canvas"]["w"] / PT_MM
        mm_per_px = LABEL_PT * PT_MM / HOUSE_EM
        w1, h1 = h["canvas"]["w"] * mm_per_px, h["canvas"]["h"] * mm_per_px
        page = next((p for p in PAGES if w1 <= p[1] and h1 <= p[2]), PAGES[-1])
        items.append(dict(n=n, nodes=len(f["nodes"]), flows=len(f["edges"]),
                          svg=os.path.relpath(os.path.join(root, "diagrams", n, n + ".svg"), os.path.dirname(out)),
                          png=os.path.relpath(os.path.join(work, n + "-house.png"), os.path.dirname(out)),
                          today_pt=today_pt, fit_pt=fit_pt, w1=w1, h1=h1, page=page[0],
                          fit_h=COLUMN_MM * h["canvas"]["h"] / h["canvas"]["w"],
                          today_h=COLUMN_MM * f["canvas"]["h"] / f["canvas"]["w"]))
    o = ["""<!doctype html><html><head><meta charset="utf-8"><title>UBL figures: a uniform set</title>
<style>
@page { size: A4; margin: 20mm 15mm; }
@page a4l { size: A4 landscape; margin: 20mm 15mm; }
@page a3l { size: A3 landscape; margin: 20mm 15mm; }
@page a3 { size: A3; margin: 20mm 15mm; }
body { font-family: "Liberation Sans", Helvetica, Arial, sans-serif; font-size: 9.5pt; color: #111; margin: 0; }
h1 { font-size: 18pt; margin: 0 0 4mm; } h2 { font-size: 13pt; margin: 0 0 3mm; }
.col { width: 145mm; margin: 0 auto; }
.sec { break-before: page; }
.fig { break-inside: avoid; margin: 0 0 7mm; }
.fig img { display: block; border: 0.2mm solid #bbb; }
.cap { font-size: 8.5pt; color: #333; margin: 1.5mm 0 0; }
.cap b { color: #111; }
table { border-collapse: collapse; font-size: 8.5pt; margin: 3mm 0; }
td, th { border-bottom: 0.2mm solid #ccc; padding: 1mm 2mm; text-align: left; vertical-align: top; }
.a4l { page: a4l; break-before: page; } .a3l { page: a3l; break-before: page; }
.a3 { page: a3; break-before: page; } .a4 { break-before: page; }
.note { color: #555; }
</style></head><body>"""]
    o.append("""<div class="col"><h1>UBL figures: a uniform set</h1>
<p>A demonstration for the TC, not a decision. Five of the 78 activity diagrams, from the simplest to
the most complex, shown three ways.</p>
<ol>
<li><b>As published today.</b> Each figure is the committed SVG, faithful to its artwork, and shown
at the column's full width, as the specification shows every figure. So a figure with a few boxes
has large boxes and large text, and a figure with many has small ones.</li>
<li><b>In a house style, fitted to the column.</b> The same element looks the same in every
figure: one label size, one line weight, one arrowhead, one shape for each kind of node. It is
still shown at the column's width, so its size on paper still depends on how much the figure
holds: its labels print at exactly the size they do today, since each figure keeps its layout and
is scaled as a whole.</li>
<li><b>In the house style, at one scale for all.</b> Every figure is printed at the same scale, so
a label is the same size on paper (%.0f pt) in every figure. A simple figure is small; a complex
one needs a larger page, or a new layout that fits the page.</li>
</ol>
<p>In draw.io this is natural. A draw.io page is not a fixed size: the drawing is made in its own
units, the same for every figure, and the page and the export scale decide how large it prints.
What the TC has to choose is which of the two kinds of uniform it wants on paper: the same
<i>look</i> (2), or the same <i>size</i> as well (3).</p>
<h2>The house style proposed</h2>
<p class="note">The median of what the 78 artworks draw, relative to their own label size
(poc-drawio/census.md).</p>
<table>
<tr><th>element</th><th>house style</th></tr>
<tr><td>labels</td><td>12 px Helvetica; actions bold, documents bold italic, decisions, guards and lane titles plain</td></tr>
<tr><td>lines</td><td>flows and outlines 0.10 of the label size, documents 0.16, dividers 0.11, frame 0.18</td></tr>
<tr><td>arrowheads</td><td>open, 1.35 label sizes long</td></tr>
<tr><td>action</td><td>its words, plus 1 label size each side and 0.8 above and below; corners rounded to 0.45 of its height</td></tr>
<tr><td>document</td><td>its words, plus 1 each side and 1.2 above and below</td></tr>
<tr><td>decision</td><td>around its question, or 2 label sizes across when the question stands beside it</td></tr>
<tr><td>start, end</td><td>draw.io's UML start and end states, 1.8 label sizes across</td></tr>
<tr><td>fork bar</td><td>0.5 label sizes thick</td></tr>
<tr><td>grey rules</td><td>none: one line per divider</td></tr>
</table>
<p class="note">Each figure keeps its layout: every element stays where its artwork puts it, scaled
so its labels come out at the house size. Over all 78, 66 take the house style with nothing
overlapping; 12 need a box or a guard moved (see census.md).</p>
</div>""" % LABEL_PT)
    o.append('<div class="sec col"><h2>1. As published today: faithful, each at the column&#8217;s width</h2>')
    for it in items:
        o.append('<div class="fig"><img src="%s" style="width:145mm"><p class="cap"><b>%s</b>: %d nodes, %d flows. '
                 'Labels print at about %.1f pt.</p></div>' % (esc(it["svg"]), esc(it["n"]), it["nodes"], it["flows"], it["today_pt"]))
    o.append('</div><div class="sec col"><h2>2. House style, each fitted to the column&#8217;s width</h2>')
    for it in items:
        o.append('<div class="fig"><img src="%s" style="width:145mm"><p class="cap"><b>%s</b>: labels print at %.1f pt.</p></div>'
                 % (esc(it["png"]), esc(it["n"]), it["fit_pt"]))
    o.append('</div>')
    first = True
    for it in items:
        cls = it["page"]
        head = ('<h2>3. House style at one scale: labels %.0f pt on paper in every figure</h2>' % LABEL_PT) if first else ""
        first = False
        o.append('<div class="%s">%s<div class="fig"><img src="%s" style="width:%.1fmm"><p class="cap"><b>%s</b>: '
                 '%.0f &#215; %.0f mm; needs %s.</p></div></div>'
                 % (cls, head, esc(it["png"]), it["w1"], esc(it["n"]), it["w1"], it["h1"],
                    {"a4": "A4, within the column" if it["w1"] <= COLUMN_MM else "A4, wider than the column",
                     "a4l": "an A4 landscape page", "a3l": "an A3 landscape page", "a3": "an A3 page"}[cls]))
    o.append("</body></html>")
    open(out, "w", encoding="utf-8").write("\n".join(o))
    for it in items:
        print("  %-50s today %.1f pt | fitted %.1f pt | one scale %3.0f x %3.0f mm (%s)"
              % (it["n"], it["today_pt"], it["fit_pt"], it["w1"], it["h1"], it["page"]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
