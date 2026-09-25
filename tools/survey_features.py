#!/usr/bin/env python3
"""Survey the UML PNGs for features the conversion pipeline has to cope with.

    python3 survey_features.py <art-dir> [name-filter]

Counts, per diagram: lane dividers, node shapes by kind, fork/join bars (solid
thin rectangles, which have no interior so the flood-fill never sees them),
dashed line-work, and the canvas aspect. Used to choose validation cases that
exercise something the earlier examples did not.
"""
import sys, os, glob
import numpy as np
import scipy.ndimage as ndi
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def ink_of(path):
    im = Image.open(path)
    bg = Image.new("RGB", im.size, "white")
    bg.paste(im, mask=im.split()[-1] if im.mode in ("RGBA", "LA") else None)
    return np.asarray(bg.convert("L")) < 128


def features(path):
    ink = ink_of(path)
    H, W = ink.shape
    # lane dividers: full-height vertical rules that are not the frame
    cols = ink.sum(axis=0)
    v = np.where(cols > H * 0.85)[0]
    groups, cur = [], []
    for x in v:
        if cur and x - cur[-1] > 3:
            groups.append(cur); cur = []
        cur.append(x)
    if cur: groups.append(cur)
    dividers = [g for g in groups if 6 < g[0] < W - 12]

    # node interiors
    free = ~ink
    lbl, _ = ndi.label(free)
    border = set(lbl[0, :]) | set(lbl[-1, :]) | set(lbl[:, 0]) | set(lbl[:, -1])
    border.discard(0)
    enclosed = free & ~np.isin(lbl, list(border))
    l2, _ = ndi.label(enclosed)
    kinds = dict(action=0, object=0, decision=0, final=0, other=0)
    for i, sl in enumerate(ndi.find_objects(l2), start=1):
        if sl is None: continue
        area = int((l2[sl] == i).sum())
        if area < 1200: continue
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if w > W * 0.35 and h > H * 0.8: continue          # lane
        f, ar = area / (w * h), w / h
        if 0.40 <= f <= 0.56: kinds["decision"] += 1
        elif 0.56 < f <= 0.80 and 0.75 < ar < 1.3: kinds["final"] += 1
        elif f > 0.93: kinds["object"] += 1
        elif f > 0.80: kinds["action"] += 1
        else: kinds["other"] += 1

    # fork / join bars: solid, very wide or very tall, no interior
    li, _ = ndi.label(ink)
    bars = 0
    for i, sl in enumerate(ndi.find_objects(li), start=1):
        if sl is None: continue
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if h == 0 or w == 0: continue
        area = int((li[sl] == i).sum())
        fill = area / (w * h)
        ar = max(w / h, h / w)
        if fill > 0.80 and ar > 6 and max(w, h) > W * 0.03 and min(w, h) > 4 and max(w, h) < W * 0.5:
            bars += 1

    # dashed line-work: short isolated ink runs on otherwise empty rows
    dashes = 0
    for y in range(0, H, 17):
        row = ink[y]
        d = np.diff(row.astype(np.int8))
        starts = np.where(d == 1)[0]; ends = np.where(d == -1)[0]
        n = min(len(starts), len(ends))
        if n >= 4:
            runs = ends[:n] - starts[:n]
            if ((runs > 3) & (runs < 40)).sum() >= 4:
                dashes += 1
    return dict(w=W, h=H, aspect=round(W / H, 2), dividers=len(dividers), bars=bars,
                dashes=dashes, **kinds)


def main(art, filt=None):
    rows = []
    for p in sorted(glob.glob(os.path.join(art, "*.png"))):
        n = os.path.basename(p)[:-4]
        if filt and filt not in n: continue
        try:
            rows.append((n, features(p)))
        except Exception as e:
            print("  !! %s: %s" % (n, e))
    print("%-50s %10s %5s %5s %4s %4s %4s %4s %4s %5s" %
          ("diagram", "pixels", "asp", "lanes", "act", "obj", "dec", "fin", "bar", "dash"))
    for n, f in rows:
        print("%-50s %10s %5.2f %5d %4d %4d %4d %4d %4d %5d" %
              (n, "%dx%d" % (f["w"], f["h"]), f["aspect"], f["dividers"] + 1,
               f["action"], f["object"], f["decision"], f["final"], f["bars"], f["dashes"]))
    return rows


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
