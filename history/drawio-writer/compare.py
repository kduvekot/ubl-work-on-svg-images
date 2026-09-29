#!/usr/bin/env python3
"""Hold a draw.io render against the SVG's render of the same figure.

    python3 compare.py <svg.png> <drawio.png> <spec.json> <overlay.png> [radius]

Both renders are the figure's own size (render-svg.js, render-drawio.js). Ink
is any pixel darker than mid grey. Ink of one render with no ink of the other
within `radius` pixels (default 2, as run-pipeline.sh) is a difference: red in
the overlay where the SVG has ink and draw.io has none, blue where draw.io has
ink and the SVG none, grey where both agree. Each difference is put down to
the element of the spec whose box it falls in, so the report says which kinds
of element differ and by how much.
"""
import json, sys
import numpy as np
from PIL import Image
from scipy import ndimage


def ink(path, shape=None):
    a = np.asarray(Image.open(path).convert("L"), dtype=np.uint8)
    if shape is not None:
        h, w = shape
        b = np.full((h, w), 255, np.uint8)
        b[:min(h, a.shape[0]), :min(w, a.shape[1])] = a[:h, :w]
        a = b
    return a < 128


def boxes(spec):
    """(kind, id, x0, y0, x1, y1), smallest boxes first so a text inside a box
    is counted as the text"""
    out = []
    for n in spec["nodes"]:
        out.append((n["kind"], n["id"], n["x"], n["y"], n["x"] + n["w"], n["y"] + n["h"]))
    for g in spec.get("guards", []):
        out.append(("guard", g["id"], g["x"] - 4, g["y"] - 6, g["x"] + g["w"] + 4, g["y"] + g["h"] + 6))
    for l in spec["lanes"]:
        if l.get("cx") is not None:
            hw = (l.get("textWidth") or 100) / 2 + 20
            out.append(("lane title", l.get("id"), l["cx"] - hw, 0, l["cx"] + hw, 2 * l["cy"] + 6))
    return sorted(out, key=lambda b: (b[4] - b[2]) * (b[5] - b[3]))


def main(svg_png, drawio_png, spec_path, overlay, radius=2):
    a = ink(svg_png)
    b = ink(drawio_png, a.shape)
    disc = ndimage.generate_binary_structure(2, 1)
    near_a = ndimage.binary_dilation(a, disc, iterations=radius)
    near_b = ndimage.binary_dilation(b, disc, iterations=radius)
    only_a = a & ~near_b            # the SVG's ink draw.io lacks
    only_b = b & ~near_a            # draw.io's ink the SVG lacks
    img = np.full(a.shape + (3,), 255, np.uint8)
    img[a | b] = (190, 190, 190)
    img[only_a] = (220, 30, 30)
    img[only_b] = (30, 60, 220)
    Image.fromarray(img).save(overlay)

    spec = json.load(open(spec_path, encoding="utf-8"))
    bx = boxes(spec)
    per = {}
    ys, xs = np.nonzero(only_a | only_b)
    for y, x in zip(ys, xs):
        k = "lines (flows, frame, dividers)"
        for kind, ident, x0, y0, x1, y1 in bx:
            if x0 <= x <= x1 and y0 <= y <= y1:
                k = kind
                break
        m = per.setdefault(k, [0, 0])
        m[0 if only_a[y, x] else 1] += 1
    total = int(a.sum())
    print("SVG ink %d px, draw.io ink %d px (radius %d)" % (total, int(b.sum()), radius))
    print("  SVG ink draw.io lacks (red):   %6d px  %.3f%% of the SVG's ink"
          % (only_a.sum(), 100.0 * only_a.sum() / total))
    print("  draw.io ink the SVG lacks (blue): %6d px  %.3f%%"
          % (only_b.sum(), 100.0 * only_b.sum() / total))
    print("  by element kind (red / blue px):")
    for k, (r, bl) in sorted(per.items(), key=lambda kv: -sum(kv[1])):
        print("    %-32s %6d / %6d" % (k, r, bl))


if __name__ == "__main__":
    main(*sys.argv[1:5], *(int(v) for v in sys.argv[5:6]))
