#!/usr/bin/env python3
"""Number the findings on the difference image, and write the list that goes with it.

    mark_findings.py <diff.png> <report.json> <marked.png>

A reviewer looking at a page that says "3 absent, 3 to check" has no way of
telling which of the red marks those are, or where to look for the three things a
person has to settle. This draws a numbered box around each one on a copy of the
difference image and writes the same numbering back into the report, as `review`,
so the deck's caption list and the picture cannot drift apart: the list is
generated from what was drawn.

    red     line-work the SVG lost           blue   line-work it invented
    orange  a label missing or misread       amber  something a person must check

A check that names no region - "no object node could be identified", say - is
still numbered and listed, without a box, because there is nowhere to point.
"""
import json
import sys

from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None

COLOURS = {
    "element-absent":      ((208, 0, 0), "absent"),
    "element-invented":    ((0, 96, 208), "invented"),
    "text-absent":         ((214, 122, 0), "label absent"),
    "text-differs":        ((214, 122, 0), "label differs"),
    "label-missing":       ((214, 122, 0), "label missing"),
    "label-mismatch":      ((214, 122, 0), "label differs"),
    "arrow-reversed":      ((160, 0, 160), "arrow reversed"),
    "node-isolated":       ((160, 0, 160), "node isolated"),
    "shape-kind-conflict": ((160, 0, 160), "shape conflict"),
}
CHECK = (150, 110, 0)

# the order a reviewer wants them in: what is missing first, then what was
# invented, then the text, then the questions
RANK = {"element-absent": 0, "element-invented": 1, "text-absent": 2,
        "text-differs": 2, "label-missing": 2, "label-mismatch": 2,
        "arrow-reversed": 3, "node-isolated": 3, "shape-kind-conflict": 3}


def order(report):
    items = []
    for f in report.get("blocking", []):
        items.append((RANK.get(f.get("kind"), 4), -f.get("area", 0), f, False))
    seen = {(i[2].get("kind"), i[2].get("x"), i[2].get("y")) for i in items}
    for f in report.get("coherence", []):
        if (f.get("kind"), f.get("x"), f.get("y")) not in seen:
            items.append((RANK.get(f.get("kind"), 4), -f.get("area", 0), f, False))
    items.sort(key=lambda t: (t[0], t[1]))
    out = [(f, False) for _, _, f, _ in items]
    out += [(h, True) for h in report.get("human", [])]
    return out


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    diff_png, report_path, out_png = argv[0], argv[1], argv[2]
    report = json.load(open(report_path))
    im = Image.open(diff_png).convert("RGB")
    d = ImageDraw.Draw(im)
    size = max(18, im.width // 70)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        font = ImageFont.load_default()
    pen = max(2, im.width // 900)

    review = []
    for i, (f, is_check) in enumerate(order(report), start=1):
        colour, what = (CHECK, "check") if is_check else \
            COLOURS.get(f.get("kind"), ((120, 120, 120), f.get("kind", "?")))
        x, y = f.get("x"), f.get("y")
        w, h = f.get("w"), f.get("h")
        boxed = None not in (x, y, w, h)
        if boxed:
            pad = size // 2
            x0, y0 = max(0, x - pad), max(0, y - pad)
            x1, y1 = min(im.width - 1, x + w + pad), min(im.height - 1, y + h + pad)
            d.rectangle([x0, y0, x1, y1], outline=colour, width=pen)
            # the number sits on the box's top-left corner, on a solid patch so it
            # is readable over whatever the diagram has there
            tx, ty = x0, max(0, y0 - size - 4)
            d.rectangle([tx, ty, tx + size * (1 + len(str(i))) // 1, ty + size + 4],
                        fill=colour)
            d.text((tx + 3, ty + 2), str(i), fill=(255, 255, 255), font=font)
        review.append({
            "n": i,
            "what": what,
            "where": ("%d,%d %dx%d" % (x, y, w, h)) if boxed else "",
            "detail": (f.get("detail") or f.get("reason") or "")[:160],
            "check": (f.get("check") or "")[:120] if is_check else "",
        })

    im.save(out_png)
    report["review"] = review
    json.dump(report, open(report_path, "w"), indent=1)
    print("%s  (%d finding(s) numbered)" % (out_png, len(review)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
