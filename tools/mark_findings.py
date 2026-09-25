#!/usr/bin/env python3
"""Number the findings on the difference image, and write the list that goes with it.

    mark_findings.py <diff.png> <report.json> <marked.png> [<line-work-diff.png>]

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

import numpy as np
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
    lw_png = argv[3] if len(argv) > 3 else None
    report = json.load(open(report_path))
    im = Image.open(diff_png).convert("RGB")
    d = ImageDraw.Draw(im)
    size = max(18, im.width // 70)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        font = ImageFont.load_default()
    pen = max(2, im.width // 900)

    # The same picture with only what the SVG *lost*. On a busy diagram the two
    # colours and their boxes overlap until neither can be read, and missing
    # line-work is the half that matters first: an invented line is a line drawn
    # in the wrong place, a missing one may be a whole start event that is not
    # there at all. Blue and the findings that go with it are left out here; they
    # are still in the full image and in the list.
    # from the line-work difference where one was given: the raw pixel difference
    # is mostly type, because a redrawn label differs from the original everywhere,
    # and a page of red glyphs hides the missing arrowhead in the corner
    src = Image.open(lw_png).convert("RGB") if lw_png else im
    px = np.asarray(src).astype(np.int16)
    lost = (px[:, :, 0] - np.maximum(px[:, :, 1], px[:, :, 2])) > 24
    only = np.full(px.shape, 255, np.uint8)
    only[lost] = (208, 0, 0)
    miss = Image.fromarray(only)
    dm = ImageDraw.Draw(miss)

    review = []
    for i, (f, is_check) in enumerate(order(report), start=1):
        colour, what = (CHECK, "check") if is_check else \
            COLOURS.get(f.get("kind"), ((120, 120, 120), f.get("kind", "?")))
        x, y = f.get("x"), f.get("y")
        w, h = f.get("w"), f.get("h")
        boxed = None not in (x, y, w, h)
        if boxed:
            pad = size // 2
            # order the corners rather than trusting the report's own: this draws
            # geometry it did not measure, and a finding that arrives with a
            # negative width should not be able to stop the whole step. One did -
            # a mark across a partition rule, whose ends are given along the
            # stroke - and the numbered images for that diagram were never written.
            x0, x1 = sorted((x, x + w))
            y0, y1 = sorted((y, y + h))
            x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
            x1, y1 = min(im.width - 1, x1 + pad), min(im.height - 1, y1 + pad)
            tx, ty = x0, max(0, y0 - size - 4)
            for draw, wanted in ((d, True), (dm, f.get("kind") == "element-absent")):
                if not wanted:
                    continue
                draw.rectangle([x0, y0, x1, y1], outline=colour, width=pen)
                # the number sits on the box's top-left corner, on a solid patch so
                # it is readable over whatever the diagram has there
                draw.rectangle([tx, ty, tx + size * (1 + len(str(i))) // 1,
                                ty + size + 4], fill=colour)
                draw.text((tx + 3, ty + 2), str(i), fill=(255, 255, 255), font=font)
        review.append({
            "n": i,
            "what": what,
            "where": ("%d,%d %dx%d" % (x, y, w, h)) if boxed else "",
            "detail": (f.get("detail") or f.get("reason") or "")[:160],
            "check": (f.get("check") or "")[:120] if is_check else "",
        })

    im.save(out_png)
    lost_png = (out_png[:-4] if out_png.endswith(".png") else out_png) + "-lost.png"
    miss.save(lost_png)
    report["review"] = review
    json.dump(report, open(report_path, "w"), indent=1)
    print("%s + %s  (%d finding(s) numbered)" % (out_png, lost_png, len(review)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
