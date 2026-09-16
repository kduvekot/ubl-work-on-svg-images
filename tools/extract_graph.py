#!/usr/bin/env python3
"""Recover a diagram's structure from the original PNG.

    python3 extract_graph.py <original.png> [--json out.json]

Produces a NOTATION-NEUTRAL semantic graph, not just geometry:

    partitions : the lane / band grid, with titles
    nodes      : id, kind, label, geometry, the partition cell it sits in
    edges      : source -> target, routing (orthogonal | straight | diagonal),
                 contact points, guard label where one could be matched
    text       : anything left over, with position

The graph is the durable part. Geometry can be re-laid-out and the notation
re-rendered (UML now, BPMN later) as long as who-connects-to-what survives.

Everything is derived from the pixels. The PNG is the source of truth.
"""
import sys, json, math
import numpy as np
import scipy.ndimage as ndi
from PIL import Image
import pytesseract

Image.MAX_IMAGE_PIXELS = None
MIN_NODE_AREA = 1200
EDGE_MIN_AREA = 150
TEXT_MIN_AREA = 60
ARROW_PROBE_R = 45


def load_ink(path):
    im = Image.open(path)
    bg = Image.new("RGB", im.size, "white")
    bg.paste(im, mask=im.split()[-1] if im.mode in ("RGBA", "LA") else None)
    return np.asarray(bg.convert("L")) < 128, bg


def ocr(bg, x, y, w, h, inset=0):
    x0, y0, x1, y1 = x + inset, y + inset, x + w - inset, y + h - inset
    if x1 - x0 < 10 or y1 - y0 < 10:
        return ""
    crop = bg.crop((x0, y0, x1, y1)).convert("L")
    crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
    t = pytesseract.image_to_string(crop, config="--psm 6")
    # keep the line breaks: the artwork wraps its labels deliberately and a
    # single-line re-render would not sit where the original does
    return "\n".join(" ".join(l.split()) for l in t.splitlines() if l.strip())


def label_lines(ink, n, pad):
    """Where each line of a node's label actually sits. Nothing here assumes the
    label is centred in its box: several UBL activity boxes carry the text near
    the top, and a note left-aligns it."""
    y0, x0 = n["y"] + pad, n["x"] + pad
    sub = ink[y0:n["y"] + n["h"] - pad, x0:n["x"] + n["w"] - pad]
    if sub.size == 0 or not sub.any():
        return []
    rows = sub.any(axis=1)
    out, r = [], 0
    while r < len(rows):
        if not rows[r]:
            r += 1
            continue
        s = r
        while r < len(rows) and rows[r]:
            r += 1
        band = sub[s:r]
        cols = np.where(band.any(axis=0))[0]
        out.append(dict(x=int(x0 + cols[0]), y=int(y0 + s),
                        w=int(cols[-1] - cols[0] + 1), h=int(r - s)))
    return out


def enclosed_regions(ink):
    free = ~ink
    lbl, _ = ndi.label(free)
    border = set(lbl[0, :]) | set(lbl[-1, :]) | set(lbl[:, 0]) | set(lbl[:, -1])
    border.discard(0)
    enc = free & ~np.isin(lbl, list(border))
    l2, _ = ndi.label(enc)
    out = []
    for i, sl in enumerate(ndi.find_objects(l2), start=1):
        if sl is None:
            continue
        area = int((l2[sl] == i).sum())
        if area < MIN_NODE_AREA:
            continue
        y0, x0 = sl[0].start, sl[1].start
        h, w = sl[0].stop - y0, sl[1].stop - x0
        # the label glyphs punch holes in the interior; fill them so that `solid`
        # measures the shape itself and not how much text it happens to carry
        solid = ndi.binary_fill_holes(l2[sl] == i)
        # corner radii, read straight off the shape: the top row of a rounded
        # rectangle starts rx in from the left, the left column ry down from the top
        rx = int(np.argmax(solid[0])) if solid[0].any() else 0
        ry = int(np.argmax(solid[:, 0])) if solid[:, 0].any() else 0
        out.append(dict(x=int(x0), y=int(y0), w=int(w), h=int(h),
                        area=area, fill=round(area / (w * h), 3),
                        solid=round(float(solid.sum()) / (w * h), 3),
                        rx=rx, ry=ry, mask=solid))
    return out


def border_coverage(ink, n, pad=3):
    """fraction of the bbox perimeter that sits on ink - a stroked box is ~1.0,
    white merely trapped between other shapes is much lower"""
    H, W = ink.shape
    x0, y0 = max(0, n["x"] - pad), max(0, n["y"] - pad)
    x1, y1 = min(W - 1, n["x"] + n["w"] + pad), min(H - 1, n["y"] + n["h"] + pad)
    xs = np.arange(x0, x1 + 1); ys = np.arange(y0, y1 + 1)
    band = 2 * pad + 1
    def cov(strip):
        return strip.any(axis=0) if strip.shape[0] < strip.shape[1] else strip.any(axis=1)
    top = ink[max(0, y0):y0 + band, xs].any(axis=0)
    bot = ink[max(0, y1 - band):y1 + 1, xs].any(axis=0)
    lft = ink[ys, max(0, x0):x0 + band].any(axis=1)
    rgt = ink[ys, max(0, x1 - band):x1 + 1].any(axis=1)
    tot = top.size * 2 + lft.size * 2
    return float(top.sum() + bot.sum() + lft.sum() + rgt.sum()) / max(1, tot)


def sides_continue(ink, n, t=12, near=12, far=45):
    """How many of the four bbox sides are formed by a line that runs on past the
    box. A node's own outline turns the corner and stops; a partition rule or a
    long connector that merely helps trap some whitespace keeps going."""
    H, W = ink.shape
    x, y, w, h = n["x"], n["y"], n["w"], n["h"]

    def any_ink(y0, y1, x0, x1):
        y0, y1, x0, x1 = max(0, y0), min(H, y1), max(0, x0), min(W, x1)
        return y1 > y0 and x1 > x0 and bool(ink[y0:y1, x0:x1].any())

    c = 0
    for ey, up in ((y, True), (y + h, False)):
        r0, r1 = (ey - t, ey + 1) if up else (ey, ey + t + 1)
        if any_ink(r0, r1, x - far, x - near) or any_ink(r0, r1, x + w + near, x + w + far):
            c += 1
    for ex, left in ((x, True), (x + w, False)):
        c0, c1 = (ex - t, ex + 1) if left else (ex, ex + t + 1)
        if any_ink(y - far, y - near, c0, c1) or any_ink(y + h + near, y + h + far, c0, c1):
            c += 1
    return c


def is_note(ink, n):
    """UML note: a rectangle with the top-right corner folded away. Test that the
    area missing from the bounding box really is that one corner and nothing
    else - plenty of trapped whitespace is 90% solid too."""
    m = n.get("mask")
    if m is None or not (0.80 <= n.get("solid", n["fill"]) <= 0.995):
        return False
    h, w = m.shape
    missing = ~m
    if missing.sum() < 0.008 * w * h:      # a plain rectangle, bar a stray pixel
        return False
    yy, xx = np.mgrid[0:h, 0:w]
    # a rounded rectangle also loses area at the top-right, but only a quarter of
    # what it loses in total - the other three corners are rounded too
    for f in (0.3, 0.45, 0.6, 0.8, 1.0):
        s = f * min(w, h)
        corner = ((w - 1 - xx) + yy <= s)          # above the top-right anti-diagonal
        if (missing & corner).sum() >= 0.65 * missing.sum():
            return True
    return False


def shape_iou(n):
    """Best overlap between the interior and the UML node outlines: rectangle,
    rounded rectangle, rhombus (decision) and ellipse. Whitespace trapped between
    other shapes is concave or notched and matches none of them."""
    m = n.get("mask")
    if m is None:
        return 1.0, "?"
    h, w = m.shape
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx, ry, rx = (h - 1) / 2.0, (w - 1) / 2.0, max(h / 2.0, .5), max(w / 2.0, .5)
    cands = [("rect", np.ones((h, w), bool)),
             ("rhombus", (np.abs(yy - cy) / ry + np.abs(xx - cx) / rx) <= 1.02),
             ("ellipse", ((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2 <= 1.02)]
    for f in (0.15, 0.3, 0.5):
        r = f * min(h, w)
        t = np.ones((h, w), bool)
        for oy, ox in ((0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)):
            ky = oy + (r if oy == 0 else -r); kx = ox + (r if ox == 0 else -r)
            quad = ((yy <= ky) if oy == 0 else (yy >= ky)) & ((xx <= kx) if ox == 0 else (xx >= kx))
            t &= ~(quad & ((yy - ky) ** 2 + (xx - kx) ** 2 > r * r))
        cands.append(("rounded", t))
    best = max(((name, (m & t).sum() / float((m | t).sum())) for name, t in cands),
               key=lambda p: p[1])
    return best[1], best[0]


def is_final_ring(ink, n, W):
    """activity final: white ring between the outer circle and the filled disc"""
    ar = n["w"] / n["h"]
    if not (0.75 < ar < 1.35 and n["w"] < W * 0.06):
        return False
    return bool(ink[n["y"] + n["h"] // 2, n["x"] + n["w"] // 2])


def drop_phantoms(ink, regs, cells=(), min_iou=0.88, max_open=2):
    """White trapped between boxes, partition rules and connectors looks like a
    shape. Four tests, in order: it must not be a partition cell, it must not
    enclose another region, and unless it is recognisably a note or an activity
    final it has to be solid (rectangle, rounded rectangle, rhombus...) and be
    bounded by line-work that stops at its own edges."""
    keep = []
    for a in regs:
        why = None
        iou, a["shape"] = shape_iou(a)
        if any(abs(a["x"] - c[0]) <= 10 and abs(a["y"] - c[1]) <= 10 and
               abs(a["x"] + a["w"] - c[2]) <= 10 and abs(a["y"] + a["h"] - c[3]) <= 10
               for c in cells):
            why = "is a partition cell"
        elif any(b is not a and b["x"] >= a["x"] - 2 and b["y"] >= a["y"] - 2 and
                 b["x"] + b["w"] <= a["x"] + a["w"] + 2 and
                 b["y"] + b["h"] <= a["y"] + a["h"] + 2 for b in regs):
            why = "encloses another region"
        elif is_final_ring(ink, a, ink.shape[1]) or is_note(ink, a):
            why = None
        else:
            open_sides = sides_continue(ink, a)
            if iou < min_iou:
                why = "outline matches no UML node shape (best %s %.2f)" % (a["shape"], iou)
            elif open_sides > max_open:
                why = "%d of 4 sides are pass-through line-work" % open_sides
        if why:
            print("   (dropped x=%-5d y=%-5d %4dx%-4d  %s)" % (a["x"], a["y"], a["w"], a["h"], why))
            continue
        keep.append(a)
    return keep


def stroke_of(ink, n):
    # probe down onto the top edge. A box is sampled at several x so that an
    # incoming connector cannot inflate the result; a round or pointed shape only
    # has its outline at the bbox top in the middle, so there it is sampled once.
    ts = []
    for f in ((0.25, 0.4, 0.6, 0.75) if n.get("shape") in (None, "rect", "rounded") else (0.5,)):
        cx = int(n["x"] + n["w"] * f)
        y, t = n["y"] - 1, 0
        while y >= 0 and ink[y, cx] and t < 60:
            t += 1; y -= 1
        ts.append(t)
    return min(ts)


def heavy_stroke(strokes):
    """UBL draws object nodes with a heavier border than action nodes, but the
    absolute weight differs per diagram (6 vs 3 in one, 8 vs 4 in another), so
    the split has to come from the diagram's own two line weights: sort them and
    cut at the widest gap. No clear gap means there are no object nodes."""
    s = sorted(set(x for x in strokes if x >= 2))
    if len(s) < 2:
        return 10 ** 6
    i = max(range(1, len(s)), key=lambda k: s[k] - s[k - 1])
    if s[i] - s[i - 1] < 2 or s[i] < s[i - 1] * 1.5:
        return 10 ** 6
    return (s[i] + s[i - 1]) / 2.0


def classify(n, W, H, ink=None, heavy=9):
    # `solid` is the interior with the label glyphs filled back in, so it measures
    # the outline's shape: ~1.0 rectangle, ~0.79 ellipse, ~0.5 rhombus
    f, ar = n.get("solid", n["fill"]), n["w"] / n["h"]
    if n["w"] > W * 0.30 and n["h"] > H * 0.70:
        return "partition"
    # an activity-final is a ring around a filled disc: ink at the centre, and
    # roughly square. A rhombus of the same fill ratio is white at the centre.
    if ink is not None and is_final_ring(ink, n, W):
        return "final"
    if ink is not None and is_note(ink, n):
        return "note"
    if 0.40 <= f <= 0.56:
        return "decision"
    if 0.56 < f <= 0.80 and 0.75 < ar < 1.35:
        return "final"
    if n.get("stroke", 0) >= heavy:
        return "object"
    return "action"


def solid_blobs(ink, W, H):
    """solid ink with no interior: initial nodes and fork/join bars"""
    core = ndi.binary_erosion(ink, np.ones((7, 7)))     # lines vanish, solids survive
    lbl, _ = ndi.label(core)
    discs, bars = [], []
    for i, sl in enumerate(ndi.find_objects(lbl), start=1):
        if sl is None:
            continue
        y0, x0 = sl[0].start, sl[1].start
        h, w = sl[0].stop - y0, sl[1].stop - x0
        if w < 5 or h < 5 or w > W * 0.5 or h > H * 0.5:
            continue
        area = int((lbl[sl] == i).sum())
        fill, ar = area / (w * h), max(w / h, h / w)
        # the erosion shrank the shape by 3px on every side - restore it
        d = dict(x=int(x0) - 3, y=int(y0) - 3, w=int(w) + 6, h=int(h) + 6,
                 area=area, fill=round(fill, 3))
        if fill > 0.70 and ar < 1.35 and 6 < w < W * 0.06:
            discs.append(dict(d, kind="initial"))
        elif fill > 0.70 and ar > 3 and min(w, h) <= 60 and max(w, h) > W * 0.012:
            bars.append(dict(d, kind="fork"))
    return discs, bars


def find_rules(ink, frac=0.40):
    """Straight full-span rules: the frame and the partition dividers.

    Coverage alone cannot separate a divider from the edge of a tall node - both
    sit around 0.55 once the boxes that straddle the divider have punched holes
    in it. What does separate them is where the line *ends*: a divider runs from
    one side of the frame to the other, so it is unbroken for the first and last
    stretch of the interior, while a node edge starts and stops well inside it.
    (Counting gaps does not work either: objects drawn on a divider, as UBL draws
    them, interrupt it a dozen times.)"""
    H, W = ink.shape

    def frame_span(profile, span):
        """first and last index whose line is solid right across - the frame"""
        solid = np.where(profile > span * 0.98)[0]
        if not len(solid):
            return 0, len(profile) - 1
        lo, hi = int(solid[0]), int(solid[-1])
        while lo + 1 < len(profile) and profile[lo + 1] > span * 0.98:
            lo += 1
        while hi - 1 >= 0 and profile[hi - 1] > span * 0.98:
            hi -= 1
        return lo, hi

    def scan(profile, span, axis, lo, hi, reach=30, near=1):
        idx = np.where(profile > span * frac)[0]
        groups, cur = [], []
        for p in idx:
            if cur and p - cur[-1] > 3:
                groups.append(cur); cur = []
            cur.append(p)
        if cur:
            groups.append(cur)
        out = []
        for g in groups:
            line = (ink[:, g[0]:g[-1] + 1].any(axis=1) if axis == "v"
                    else ink[g[0]:g[-1] + 1, :].any(axis=0))
            if line[lo + near:lo + reach].all() and line[hi - reach:hi - near].all():
                out.append((int(g[0]), int(g[-1] - g[0] + 1)))
        return out

    vprof, hprof = ink.sum(axis=0), ink.sum(axis=1)
    vlo, vhi = frame_span(hprof, W)          # vertical rules end on the horizontal frame
    hlo, hhi = frame_span(vprof, H)
    return (scan(vprof, H, "v", vlo, vhi), scan(hprof, W, "h", hlo, hhi))


def main(path, out_json=None):
    ink, bg = load_ink(path)
    H, W = ink.shape
    print("image %dx%d" % (W, H))

    vr, hr = find_rules(ink)
    inner_v = [r for r in vr if 6 < r[0] < W - 12]
    inner_h = [r for r in hr if 6 < r[0] < H - 12]
    vb = [0] + [x + w / 2 for x, w in inner_v] + [W]
    hb = [0] + [y + h / 2 for y, h in inner_h] + [H]
    # a first strip too narrow to hold a node is the gutter carrying the sideways
    # band titles; the same in the other direction is the column-title header
    strip = len(vb) > 2 and (vb[1] - vb[0]) < W * 0.04
    header = len(hb) > 2 and (hb[1] - hb[0]) < H * 0.04
    print("\nPARTITION RULES")
    print("   vertical  : %s" % (vr,))
    print("   horizontal: %s" % (hr,))
    print("   -> %d column(s) x %d band(s)%s%s"
          % (len(vb) - 1 - strip, len(hb) - 1 - header,
             ", sideways title gutter" if strip else "",
             ", column-title header" if header else ""))
    cells = [(round(vb[c]), round(hb[r]), round(vb[c + 1]), round(hb[r + 1]))
             for r in range(len(hb) - 1) for c in range(len(vb) - 1)]

    regs = drop_phantoms(ink, enclosed_regions(ink), cells)
    for n in regs:
        n["stroke"] = stroke_of(ink, n)
    # only the box-shaped nodes take part in the weight split: a decision rhombus
    # and a final ring are measured across a slanted or curved edge
    heavy = heavy_stroke([n["stroke"] for n in regs
                          if n.get("shape") in (None, "rect", "rounded")])
    print("   object nodes are those stroked heavier than %.1fpx" % heavy
          if heavy < 10 ** 6 else "   one line weight only - no object nodes")
    nodes, partitions = [], []
    for n in regs:
        k = classify(n, W, H, ink, heavy)
        (partitions if k == "partition" else nodes).append(dict(n, kind=k))
    discs, bars = solid_blobs(ink, W, H)
    nodes += bars
    for d in discs:
        if not any(n["x"] <= d["x"] and n["y"] <= d["y"] and
                   n["x"] + n["w"] >= d["x"] + d["w"] and
                   n["y"] + n["h"] >= d["y"] + d["h"] for n in nodes):
            nodes.append(d)

    nodes.sort(key=lambda n: (n["y"], n["x"]))
    print("\nNODES")
    for i, n in enumerate(nodes):
        n["id"] = "n%d" % (i + 1)
        inset = 0
        if n["kind"] == "action":
            inset = int(min(n["h"] * 0.22, n["w"] * 0.12))     # clear the rounded ends
        elif n["kind"] in ("object", "note"):
            inset = max(6, n.get("stroke", 6))
        if n["kind"] == "decision":
            # a rhombus only has room for text across its middle
            n["label"] = ocr(bg, n["x"] + n["w"] // 4, n["y"] + n["h"] // 4,
                             n["w"] // 2, n["h"] // 2)
        else:
            n["label"] = ocr(bg, n["x"], n["y"], n["w"], n["h"], inset) \
                if n["kind"] in ("action", "object", "note") else ""
        # pair each OCR line with the row band it was read from, so the rebuild can
        # put every line back where the original has it
        if n["label"]:
            got = n["label"].split("\n")
            boxes = label_lines(ink, n, max(inset, max(4, n.get("stroke", 4)) + 2))
            n["labelLines"] = [dict(b, text=t) for b, t in zip(boxes, got)] \
                if len(boxes) == len(got) else []
        print("   %-4s %-9s x=%-5d y=%-5d w=%-5d h=%-5d stroke=%-3d fill=%.2f  %r"
              % (n["id"], n["kind"], n["x"], n["y"], n["w"], n["h"],
                 n.get("stroke", 0), n["fill"], n["label"]))

    # font size, measured rather than assumed: the tallest glyphs inside the node
    # labels are capitals, whose cap height is ~0.70 em in Helvetica
    caps = []
    for n in nodes:
        if n["kind"] not in ("action", "object", "note"):
            continue
        p = max(8, n.get("stroke", 6)) + 2
        sub = ink[n["y"] + p:n["y"] + n["h"] - p, n["x"] + p:n["x"] + n["w"] - p]
        if sub.size == 0:
            continue
        l, _ = ndi.label(sub)
        for sl in ndi.find_objects(l):
            if sl is None:
                continue
            gh, gw = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
            if 6 < gh < H * 0.05 and 3 < gw < W * 0.05:
                caps.append(gh)
    font_px = round(float(np.percentile(caps, 90)) / 0.70, 1) if caps else 0.0
    print("\nTYPE  cap height %.0fpx over %d glyphs -> font %.1fpx"
          % (np.percentile(caps, 90) if caps else 0, len(caps), font_px))

    mask = ink.copy()
    for n in nodes:
        m = 14
        mask[max(0, n["y"] - m):n["y"] + n["h"] + m, max(0, n["x"] - m):n["x"] + n["w"] + m] = False
    for x, w in vr:
        mask[:, max(0, x - 2):x + w + 2] = False
    for y, h in hr:
        mask[max(0, y - 2):y + h + 2, :] = False

    # a connector that crosses a partition rule has just been cut in two, and
    # neither half then touches both of its nodes. Bridge the cut back wherever
    # line-work continues on both sides of the erased band.
    for x, w in vr:
        a, b = max(0, x - 3), min(W, x + w + 3)
        if a > 0 and b < W:
            both = mask[:, a - 1] & mask[:, b]
            mask[both, a:b] = True
    for y, h in hr:
        a, b = max(0, y - 3), min(H, y + h + 3)
        if a > 0 and b < H:
            both = mask[a - 1, :] & mask[b, :]
            mask[a:b, both] = True

    lbl, _ = ndi.label(mask, structure=np.ones((3, 3)))
    edges, textbits = [], []
    print("\nEDGES")
    for i, sl in enumerate(ndi.find_objects(lbl), start=1):
        if sl is None:
            continue
        comp = (lbl[sl] == i)
        n_px = int(comp.sum())
        if n_px < TEXT_MIN_AREA:
            continue
        ys, xs = np.where(comp)
        ys, xs = ys + sl[0].start, xs + sl[1].start
        T = 34
        touch = [n for n in nodes
                 if (((xs >= n["x"] - T) & (xs <= n["x"] + n["w"] + T) &
                      (ys >= n["y"] - T) & (ys <= n["y"] + n["h"] + T)).sum() > 3)]
        if len(touch) != 2 or n_px < EDGE_MIN_AREA:
            textbits.append([int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())])
            continue

        def contact(node):
            cx, cy = node["x"] + node["w"] / 2, node["y"] + node["h"] / 2
            k = int(np.argmin((xs - cx) ** 2 + (ys - cy) ** 2))
            px, py = int(xs[k]), int(ys[k])
            r = ARROW_PROBE_R
            return int(mask[max(0, py - r):py + r, max(0, px - r):px + r].sum()), (px, py)

        (da, pa), (db, pb) = contact(touch[0]), contact(touch[1])
        src, dst = (touch[0], touch[1]) if da < db else (touch[1], touch[0])
        p_from, p_to = (pa, pb) if da < db else (pb, pa)
        vx, vy = p_to[0] - p_from[0], p_to[1] - p_from[1]
        L = math.hypot(vx, vy) or 1
        dist = np.abs((xs - p_from[0]) * vy - (ys - p_from[1]) * vx) / L
        straight = float(dist.mean()) < 6.0
        routing = ("diagonal" if straight and abs(vx) > 8 and abs(vy) > 8
                   else "straight" if straight else "orthogonal")
        lo, hi = min(da, db), max(da, db)
        ratio = hi / max(1, lo)
        conf = "high" if ratio >= 2.5 else "medium" if ratio >= 1.6 else "LOW"
        if any(set((e["from"], e["to"])) == set((src["id"], dst["id"])) and
               abs(e["fromPoint"][0] - p_from[0]) + abs(e["fromPoint"][1] - p_from[1]) < 80
               for e in edges):
            continue                       # the same connector, found in two pieces
        edges.append({"from": src["id"], "to": dst["id"], "routing": routing,
                      "fromPoint": list(p_from), "toPoint": list(p_to),
                      "arrowInk": [lo, hi], "directionConfidence": conf})
        print("   %-4s -> %-4s  %-11s arrowhead %5d vs %-5d  ratio %.1f  %s"
              % (src["id"], dst["id"], routing, hi, lo, ratio,
                 "<-- CHECK DIRECTION" if conf == "LOW" else conf))

    def merge(bs, gx=70, gy=max(16, int(font_px * 0.9))):
        out = []
        for b in sorted(bs, key=lambda b: (b[1], b[0])):
            for o in out:
                if b[0] <= o[2] + gx and b[2] >= o[0] - gx and b[1] <= o[3] + gy and b[3] >= o[1] - gy:
                    o[0], o[1] = min(o[0], b[0]), min(o[1], b[1])
                    o[2], o[3] = max(o[2], b[2]), max(o[3], b[3])
                    break
            else:
                out.append(list(b))
        return out
    lines = textbits
    for _ in range(4):
        lines = merge(lines)

    print("\nTEXT (titles, guards, notes)")
    texts = []
    for b in lines:
        w, h = b[2] - b[0] + 1, b[3] - b[1] + 1
        if w < 25 or h < 14:
            continue
        t = ocr(bg, b[0], b[1], w, h, -6)
        if not t:
            continue
        item = dict(text=t, x=b[0], y=b[1], w=w, h=h)
        got = t.split("\n")
        boxes = label_lines(ink, dict(x=b[0], y=b[1], w=w, h=h), -4)
        if len(boxes) == len(got):
            item["lines"] = [dict(bx, text=s2) for bx, s2 in zip(boxes, got)]
        if t.startswith("[") or t.endswith("]"):
            cx, cy = b[0] + w / 2, b[1] + h / 2
            best, bd = None, 1e18
            for e in edges:
                for p in (e["fromPoint"], e["toPoint"]):
                    d = (p[0] - cx) ** 2 + (p[1] - cy) ** 2
                    if d < bd:
                        bd, best = d, e
            if best is not None and bd < (W * 0.12) ** 2:
                best["guard"] = t
                item["attachedTo"] = "%s->%s" % (best["from"], best["to"])
        texts.append(item)
        print("   %-40r x=%-5d y=%-5d %s" % (t, b[0], b[1], item.get("attachedTo", "")))

    # column titles live in the header band, band titles sideways in the gutter
    c0, r0 = (1 if strip else 0), (1 if header else 0)
    grid = []
    for c in range(c0, len(vb) - 1):
        box = None
        if header:
            t = ocr(bg, round(vb[c]), 0, round(vb[c + 1] - vb[c]), round(hb[r0]), 6)
        else:
            # no header band: the title is simply the topmost text in the column
            cand = [x for x in texts if vb[c] <= x["x"] + x["w"] / 2 <= vb[c + 1]
                    and x["y"] < H * 0.08]
            box = min(cand, key=lambda x: x["y"]) if cand else None
            t = box["text"] if box else ""
        g = dict(axis="column", index=c - c0,
                 x0=round(vb[c]), x1=round(vb[c + 1]), title=t)
        if not header and box:
            g["titleBox"] = [box["x"], box["y"], box["w"], box["h"]]
        grid.append(g)
    for r in range(r0, len(hb) - 1):
        t = ""
        if strip:
            x0, y0 = round(vb[c0 - 1]), round(hb[r])
            w0, h0 = round(vb[c0] - vb[c0 - 1]), round(hb[r + 1] - hb[r])
            t = ocr(bg.crop((x0 + 4, y0 + 4, x0 + w0 - 4, y0 + h0 - 4)).rotate(-90, expand=True),
                    0, 0, h0 - 8, w0 - 8)
        grid.append(dict(axis="band", index=r - r0, y0=round(hb[r]), y1=round(hb[r + 1]), title=t))
    for n in nodes:
        cx, cy = n["x"] + n["w"] / 2, n["y"] + n["h"] / 2
        n["col"] = sum(1 for b in vb[1:-1] if cx > b) - c0
        n["row"] = sum(1 for b in hb[1:-1] if cy > b) - r0
    print("\nPARTITIONS")
    for g in grid:
        print("   %-6s %d  %r" % (g["axis"], g["index"], g["title"]))

    if out_json:
        for n in nodes + partitions:
            n.pop("mask", None)
        json.dump(dict(source=path, size=[W, H], fontPx=font_px, rules=dict(v=vr, h=hr),
                       partitions=grid, nodes=nodes, edges=edges, text=texts),
                  open(out_json, "w"), indent=1)
        print("\nwrote %s   (%d nodes, %d edges)" % (out_json, len(nodes), len(edges)))


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    oj = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    main(a[0], oj)
