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
LABEL_PAD = 6          # breathing room around a label crop; tesseract reads a
                       # tightly clipped glyph as a different glyph


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
    the top, and a note left-aligns it.

    The region's own interior mask is used to exclude the border where it is
    available, which a rectangular inset cannot do: inset far enough to clear a
    rounded box's corner arcs and you cut into the label of a short box, inset
    less and the arcs read as extra lines of text. The mask is the enclosed white
    area, so the stroke is outside it whatever the shape - rounded, rhombus or
    ring - and only the glyphs remain."""
    m = n.get("mask")
    if m is not None and m.shape == (n["h"], n["w"]):
        # erode so the anti-aliased inner lip of the stroke is not read as ink
        core = ndi.binary_erosion(m, np.ones((3, 3), bool), iterations=max(1, pad // 2))
        y0, x0 = n["y"], n["x"]
        sub = ink[y0:y0 + n["h"], x0:x0 + n["w"]] & core
    else:
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


def endpoint_nodes(xs, ys, cands):
    """The two nodes a connector actually runs between, given everything it passes
    near. Its ends are approximated by the usual two-pass diameter - farthest
    pixel from the centroid, then farthest from that - and each end claims the
    candidate whose box it is nearest. Returns None if both ends claim the same
    node, which means this component is not a connector between two of them."""
    cx, cy = xs.mean(), ys.mean()
    i = int(np.argmax((xs - cx) ** 2 + (ys - cy) ** 2))
    j = int(np.argmax((xs - xs[i]) ** 2 + (ys - ys[i]) ** 2))
    picks = []
    for px, py in ((xs[i], ys[i]), (xs[j], ys[j])):
        best, bd = None, None
        for n in cands:
            dx = max(n["x"] - px, 0, px - (n["x"] + n["w"]))
            dy = max(n["y"] - py, 0, py - (n["y"] + n["h"]))
            d = dx * dx + dy * dy
            if bd is None or d < bd:
                best, bd = n, d
        picks.append(best)
    return None if picks[0] is picks[1] else picks


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
        # Corner radii, read straight off the shape: the top row of a rounded
        # rectangle starts rx in from the left, the left column ry down from the
        # top - plus a correction, because that reading is biased small and the
        # bias is geometric, not noise. An arc of radius r stays within one pixel
        # of its own tangent for about sqrt(r) pixels either side of the top, so
        # those pixels are not yet distinguishable from the straight edge and the
        # raw reading lands at r - sqrt(r). Measured against rects rendered at
        # known radii: r=30 reads 23-25, r=80 reads 67-69, r=120 reads 105-107.
        # Leaving it uncorrected made the pipeline subtract the bias twice - once
        # reading the original, once again when the render was measured - so every
        # action box was drawn with a corner ~10px tighter than the artwork's.
        rx = int(np.argmax(solid[0])) if solid[0].any() else 0
        ry = int(np.argmax(solid[:, 0])) if solid[:, 0].any() else 0
        rx += int(round(math.sqrt(rx))) if rx else 0
        ry += int(round(math.sqrt(ry))) if ry else 0
        out.append(dict(x=int(x0), y=int(y0), w=int(w), h=int(h),
                        area=area, fill=round(area / (w * h), 3),
                        solid=round(float(solid.sum()) / (w * h), 3),
                        rx=rx, ry=ry, mask=solid))
    return out


def glyph_height(bg, min_conf=30):
    """Median height of a word in this diagram's own type, read once off the
    original.

    The phantom filter needs to know how big a letter is before it can tell a
    node's own label from a node: the counters of letters - the holes in O, Q, R -
    are enclosed regions like any other, and a box that encloses one would
    otherwise delete itself. The type size measured later comes from node labels,
    which is circular here, so this reads it independently. Returns 0 if nothing
    legible was found, and the caller falls back to a relative-area test."""
    try:
        d = pytesseract.image_to_data(bg, config="--psm 11",
                                      output_type=pytesseract.Output.DICT)
    except Exception:
        return 0.0
    hs = []
    for i, t in enumerate(d["text"]):
        try:
            conf = float(d["conf"][i])
        except (TypeError, ValueError):
            continue
        if t.strip() and conf >= min_conf:
            hs.append(d["height"][i])
    return float(np.median(hs)) if hs else 0.0


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


def ring_stroke(ink, n):
    """Thickness of an activity final's outer ring.

    The generic probe walks down onto the top edge and keeps going, so on a ring
    it measures ring + gap + inner disc: 60px of "stroke" on a 137px node. Every
    node is then inflated by its stroke, so the final was drawn half as wide
    again as the original. Only the first unbroken run of ink is the line."""
    H, W = ink.shape
    cx, cy = n["x"] + n["w"] // 2, n["y"] + n["h"] // 2
    # Node geometry is the enclosed white annulus, so the ring lies just outside
    # it. Probe all four sides and take the median: a connector almost always
    # meets the final from one side, and walking outward there runs straight up
    # the arrow - one probe measured 322px of "ring" on a 137px node.
    starts = ((cy, n["x"] - 1, 0, -1), (cy, n["x"] + n["w"], 0, 1),
              (n["y"] - 1, cx, -1, 0), (n["y"] + n["h"], cx, 1, 0))
    runs = []
    for y, x, dy, dx in starts:
        t = 0
        while 0 <= y < H and 0 <= x < W and ink[y, x]:
            t += 1
            y += dy
            x += dx
        runs.append(t)
    t = int(np.median(runs))
    # a ring line is a line; anything approaching the node's own size means the
    # probe escaped along line-work on more than one side, so refuse it rather
    # than inflate the node by it
    return t if 0 < t <= n["w"] * 0.25 else 0


def inner_disc_ratio(ink, n):
    """The filled disc inside an activity final, as a fraction of the outer radius.

    Measured, not assumed: UBL's finals run from 0.43 to 0.71 of the outer radius
    across the artwork, so a fixed ratio draws a disc of the wrong size on most
    diagrams and less than half the right area on the widest ones. Walks out from
    the centre in four directions and takes the median, so one clipped side or a
    connector meeting the ring cannot skew it."""
    H, W = ink.shape
    cy, cx = n["y"] + n["h"] // 2, n["x"] + n["w"] // 2
    lim = max(2, min(n["w"], n["h"]) // 2)
    runs = []
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        r = 0
        while r < lim:
            y, x = cy + dy * (r + 1), cx + dx * (r + 1)
            if not (0 <= y < H and 0 <= x < W) or not ink[y, x]:
                break
            r += 1
        runs.append(r)
    return round(float(np.median(runs)) / (n["w"] / 2.0), 3)


def is_final_ring(ink, n, W):
    """activity final: white ring between the outer circle and the filled disc"""
    ar = n["w"] / n["h"]
    if not (0.75 < ar < 1.35 and n["w"] < W * 0.06):
        return False
    return bool(ink[n["y"] + n["h"] // 2, n["x"] + n["w"] // 2])


def interior_ink(ink, n, inset=20):
    """fraction of the region's interior that carries ink - i.e. does it hold a
    label. Whitespace merely trapped between other shapes holds nothing."""
    sub = ink[n["y"] + inset:n["y"] + n["h"] - inset,
              n["x"] + inset:n["x"] + n["w"] - inset]
    return float(sub.mean()) if sub.size else 0.0


def in_title_band(n, bands, tol=10):
    """does the region sit inside the column-title header or the sideways band-title
    gutter - those hold partition titles, never nodes"""
    hy, gx = bands
    if hy is not None and n["y"] + n["h"] <= hy + tol:
        return "the column-title header"
    if gx is not None and n["x"] + n["w"] <= gx + tol:
        return "the band-title gutter"
    return None


def drop_phantoms(ink, regs, cells=(), min_iou=0.88, max_open=2,
                  own_iou=0.97, own_cov=0.97, own_iou_curved=0.95, min_interior=0.01,
                  title_bands=(None, None), glyph_h=0.0, flags=None):
    """White trapped between boxes, partition rules and connectors looks like a
    shape. Four tests, in order: it must not be a partition cell, it must not
    enclose another region, and unless it is recognisably a note or an activity
    final it has to be solid (rectangle, rounded rectangle, rhombus...) and be
    bounded by line-work that stops at its own edges.

    The pass-through test cannot veto a region that carries a complete outline of
    its own (`own_iou`/`own_cov`). UBL draws object nodes *on* the partition rule
    and *on* the connector, so all four of their sides have line-work running past
    them - that is the house style, not evidence of a phantom. Trapped whitespace
    is concave, notched, or bounded only in part, so it fails one of the two.

    Every drop, and every region kept only by that override, is appended to
    `flags` so the caller can report it rather than discard it silently."""
    keep = []
    for a in regs:
        why = None
        kept_by_outline = False
        iou, a["shape"] = shape_iou(a)
        cov = border_coverage(ink, a)
        if any(abs(a["x"] - c[0]) <= 10 and abs(a["y"] - c[1]) <= 10 and
               abs(a["x"] + a["w"] - c[2]) <= 10 and abs(a["y"] + a["h"] - c[3]) <= 10
               for c in cells):
            why = "is a partition cell"
        elif in_title_band(a, title_bands):
            why = "lies in %s" % in_title_band(a, title_bands)
        elif any(b is not a and b["x"] >= a["x"] - 2 and b["y"] >= a["y"] - 2 and
                 b["x"] + b["w"] <= a["x"] + a["w"] + 2 and
                 b["y"] + b["h"] <= a["y"] + a["h"] + 2 and
                 # ...but the counters of its own label are enclosed regions too,
                 # so a box whose label holds a closed letter would delete itself.
                 # Three action nodes vanished from Tender-QualificationInfo that
                 # way and the only decision node from Tender-ContractInfoNotify,
                 # and the drops looked principled enough that nothing was
                 # reported. A counter is by definition smaller than the letter
                 # around it, so measure the type and require the enclosed region
                 # to be at least the height of a word. Relative area is a poor
                 # stand-in: the hole in a "Q" is 0.6% of a wide action box but
                 # the "O" of "OK?" is 3.4% of its own small rhombus.
                 (b["h"] >= 0.9 * glyph_h if glyph_h else
                  (b["w"] * b["h"]) >= 0.02 * (a["w"] * a["h"]))
                 for b in regs):
            why = "encloses another region"
        elif is_final_ring(ink, a, ink.shape[1]) or is_note(ink, a):
            why = None
        else:
            open_sides = sides_continue(ink, a)
            if iou < min_iou:
                why = "outline matches no UML node shape (best %s %.2f)" % (a["shape"], iou)
            elif open_sides > max_open:
                # A complete outline of its own *and* something inside it. Trapped
                # whitespace can be bounded on all four sides by its neighbours, but
                # it never holds a label.
                #
                # How "a complete outline" is established depends on the shape. For
                # a rectangle the bbox *is* the outline, so border coverage settles
                # it. For a rhombus, an ellipse or a rounded box the bbox corners
                # are white by construction - a decision diamond measures 0.07
                # coverage - so coverage says nothing and the outline match has to
                # carry it alone. Requiring coverage of everything cost UBL-2.2-
                # DigitalAgreement two of its three decision nodes: every diamond
                # there matched its outline at 0.964 and held a label, and the two
                # that were dropped differed from the one that survived only in
                # having connectors on three sides - which is what a decision node
                # is for.
                curved = a["shape"] in ("rhombus", "ellipse", "rounded")
                outline_ok = (iou >= own_iou_curved) if curved else \
                             (iou >= own_iou and cov >= own_cov)
                if outline_ok and interior_ink(ink, a) >= min_interior:
                    kept_by_outline = True
                else:
                    why = "%d of 4 sides are pass-through line-work" % open_sides
        note = dict(x=a["x"], y=a["y"], w=a["w"], h=a["h"],
                    shape=a["shape"], iou=round(float(iou), 3), border=round(float(cov), 3))
        if why:
            print("   (dropped x=%-5d y=%-5d %4dx%-4d  %s)" % (a["x"], a["y"], a["w"], a["h"], why))
            # a partition cell, a region enclosing others, or a title strip is a
            # confident drop with a reason that names itself - only the judgement
            # calls are worth a person's time, or the list drowns in routine
            if flags is not None and not why.startswith(("is a partition cell",
                                                         "encloses another region",
                                                         "lies in ")):
                flags.append(dict(note, kind="dropped-region", reason=why,
                                  check="a shape here would be missing from the SVG"))
            continue
        if kept_by_outline:
            print("   (kept    x=%-5d y=%-5d %4dx%-4d  own outline, iou %.2f border %.2f,"
                  " despite pass-through line-work)" % (a["x"], a["y"], a["w"], a["h"], iou, cov))
            if flags is not None:
                flags.append(dict(note, kind="kept-on-outline",
                                  reason="every side has pass-through line-work, but the"
                                         " region carries a complete outline of its own",
                                  check="confirm this is a node and not trapped whitespace"))
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


def classify(n, W, H, ink=None, heavy=9, has_rounded=False):
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
    # UML notation *is* the outline: an action is a rounded rectangle, an object
    # node a plain one. The stroke-weight split is a proxy for the same thing and
    # it fails whenever a diagram draws both at one weight - the whole Tender
    # family does, so every rounded box there was called an object and then drawn
    # with square corners. Measured curvature is the direct evidence, so it wins;
    # weight only separates the boxes that really are rectangular.
    if n.get("shape") == "rounded" and max(n.get("rx") or 0, n.get("ry") or 0) > 2:
        return "action"
    # Where the weight split found nothing, the artwork is not distinguishing the
    # two by weight - so read the distinction it *is* making. A diagram holding
    # both rounded and square boxes at one stroke weight is separating them by
    # shape, and the square ones are the object nodes. UBL-2.3-Tender-Contract-Post
    # draws every box at 8px and came out as 14 actions and no object node at all,
    # so its three "Tender Contract" object nodes were rendered with round corners.
    if heavy >= 10 ** 6 and has_rounded and n.get("shape") == "rect":
        return "object"
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

    uncertain = []
    gh = glyph_height(bg)
    print("   type measured off the page: a word is %.0fpx tall" % gh
          if gh else "   no legible type found; enclosure falls back to relative area")
    regs = drop_phantoms(ink, enclosed_regions(ink), cells, flags=uncertain,
                         title_bands=(hb[1] if header else None,
                                      vb[1] if strip else None),
                         glyph_h=gh)
    for n in regs:
        n["stroke"] = stroke_of(ink, n)
    # only the box-shaped nodes take part in the weight split: a decision rhombus
    # and a final ring are measured across a slanted or curved edge
    has_rounded = any(r.get("shape") == "rounded" and
                      max(r.get("rx") or 0, r.get("ry") or 0) > 2 for r in regs)
    box_strokes = [n["stroke"] for n in regs if n.get("shape") in (None, "rect", "rounded")]
    heavy = heavy_stroke(box_strokes)
    print("   object nodes are those stroked heavier than %.1fpx" % heavy
          if heavy < 10 ** 6 else "   one line weight only - no object nodes")
    if heavy >= 10 ** 6 and len(box_strokes) > 1:
        # object vs action is a *relative* weight, so one weight means either the
        # diagram genuinely has no object nodes or a heavier box was never seen
        uncertain.append(dict(kind="no-weight-split",
                              reason="all %d box strokes are one weight (%s), so no object"
                                     " node could be identified"
                                     % (len(box_strokes), sorted(set(box_strokes))),
                              check="confirm the diagram really has no object nodes"))
    nodes, partitions = [], []
    for n in regs:
        k = classify(n, W, H, ink, heavy, has_rounded)
        rec = dict(n, kind=k)
        if k == "final":
            rec["innerRatio"] = inner_disc_ratio(ink, n)
            rs = ring_stroke(ink, n)
            if rs:
                rec["stroke"] = rs
            else:
                rec["stroke"] = 0
                uncertain.append(dict(kind="ring-stroke-unreadable", x=n["x"], y=n["y"],
                                      w=n["w"], h=n["h"],
                                      reason="line-work runs off this activity final on"
                                             " more than one side, so its ring thickness"
                                             " could not be measured",
                                      check="confirm this is an activity final and how"
                                            " thick its ring is"))
        (partitions if k == "partition" else nodes).append(rec)
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
        # Read the text from where the text actually is. A fixed geometric inset
        # clips it: 22% of the height off the top and the bottom of a short box
        # leaves too little for its own label, and half-height glyphs OCR as
        # nonsense ("Draft" -> "Uiall", "Declaration" -> "Narlaratinn"). Find the
        # line bands off the ink first, then read the block they span.
        boxes = label_lines(ink, n, max(4, n.get("stroke", 4)) + 2) \
            if n["kind"] in ("action", "object", "note") else []
        if n["kind"] == "decision":
            # A rhombus only has room for text across its middle. Reading it off
            # the interior mask the way a box is read was tried and is worse: the
            # slanted border survives the erosion and sits in the crop, so
            # "Reconcile Charges" came back as "xeconcile ~harges". The small
            # rhombus labels ("OK?") are misread either way and need their own
            # treatment.
            n["label"] = ocr(bg, n["x"] + n["w"] // 4, n["y"] + n["h"] // 4,
                             n["w"] // 2, n["h"] // 2)
        elif boxes:
            bx0 = min(b["x"] for b in boxes); by0 = min(b["y"] for b in boxes)
            bx1 = max(b["x"] + b["w"] for b in boxes); by1 = max(b["y"] + b["h"] for b in boxes)
            n["label"] = ocr(bg, bx0, by0, bx1 - bx0, by1 - by0, -LABEL_PAD)
        else:
            n["label"] = ""
        # pair each OCR line with the row band it was read from, so the rebuild can
        # put every line back where the original has it
        if n["label"]:
            got = n["label"].split("\n")
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

    # The counters of letters - the holes in O, D, R - are enclosed white regions
    # too, and on a diagram with large type they clear the minimum node area. They
    # then get masked out as if they were nodes, which cuts the lane title they sit
    # in: "TENDERER" was being read as "TEN". Nothing smaller than one character of
    # the diagram's own type can be a node, so measure that and drop them. Shapes
    # found as solid blobs (initial, fork bars) never reach here.
    if font_px > 0:
        keep = []
        for n in nodes:
            if (not n.get("label") and n.get("mask") is not None
                    and n["w"] < font_px and n["h"] < font_px):
                print("   (dropped x=%-5d y=%-5d %4dx%-4d  smaller than one character"
                      " of %.0fpx type - a letter counter, not a node)"
                      % (n["x"], n["y"], n["w"], n["h"], font_px))
                uncertain.append(dict(kind="sub-character-region", x=n["x"], y=n["y"],
                                      w=n["w"], h=n["h"],
                                      reason="enclosed region smaller than one character of"
                                             " the diagram's type",
                                      check="confirm this is glyph interior and not a node"))
                continue
            keep.append(n)
        nodes = keep

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
    edges, textbits, unexplained = [], [], []
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
        if len(touch) > 2:
            # A connector that merely runs close to a third node is still an edge.
            # UBL routes inter-lane flows directly under the notes, so demanding
            # exactly two nodes within T threw those away - and worse, dropped
            # them into the text bin, where they were read as text and became
            # part of a partition title. Keep the two nodes nearest the
            # component's own ends instead.
            touch = endpoint_nodes(xs, ys, touch) or touch
        if len(touch) != 2 or n_px < EDGE_MIN_AREA:
            bx0, by0 = int(xs.min()), int(ys.min())
            bx1, by1 = int(xs.max()), int(ys.max())
            # Only bin this as text if it is the size and shape of text. A
            # rejected connector is neither, and letting one into the text bin
            # is not harmless: the blocks are merged by proximity in four
            # cascading passes, so a single long fragment chains unrelated
            # labels into one block. That is how a partition title came out 764
            # characters long, carrying half the diagram's words.
            if (by1 - by0 + 1) <= font_px * 2.2 and (bx1 - bx0 + 1) <= font_px * 20:
                textbits.append([bx0, by0, bx1, by1])
            else:
                unexplained.append(dict(kind="unexplained-line-work",
                                        x=bx0, y=by0, w=bx1 - bx0 + 1, h=by1 - by0 + 1,
                                        reason="line-work that is neither a connector"
                                               " between two nodes nor the size of text",
                                        check="decide what this is; the SVG does not draw it"))
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
        # every edge the direction probe could not read confidently is a human-check
        # item too, so the one list is the whole of what this run is unsure about
        uncertain.extend(unexplained)
        for e in edges:
            if e.get("directionConfidence") == "LOW":
                uncertain.append(dict(kind="edge-direction", reason="arrowhead ink is ambiguous"
                                      " where several connectors meet",
                                      edge=[e.get("from"), e.get("to")],
                                      check="confirm which way this edge points"))
        json.dump(dict(source=path, size=[W, H], fontPx=font_px, rules=dict(v=vr, h=hr),
                       partitions=grid, nodes=nodes, edges=edges, text=texts,
                       uncertain=uncertain),
                  open(out_json, "w"), indent=1)
        print("\nwrote %s   (%d nodes, %d edges, %d flagged for a human)"
              % (out_json, len(nodes), len(edges), len(uncertain)))


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    oj = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    main(a[0], oj)
