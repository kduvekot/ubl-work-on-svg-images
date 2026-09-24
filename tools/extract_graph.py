#!/usr/bin/env python3
"""Recover a diagram's structure from the original PNG.

    python3 extract_graph.py <original.png> [--json out.json]

Produces a NOTATION-NEUTRAL semantic graph, not just geometry:

    partitions : the lane / band grid, with titles
    nodes      : id, kind, label, geometry, the partition cell it sits in
    edges      : source -> target, routing (orthogonal | straight | diagonal),
                 contact points, the corners an orthogonal route turns at,
                 guard label where one could be matched
    text       : anything left over, with position

The graph is the durable part. Geometry can be re-laid-out and the notation
re-rendered (UML now, BPMN later) as long as who-connects-to-what survives.

Everything is derived from the pixels. The PNG is the source of truth.
"""
import sys, os, re, json, math
import numpy as np
import scipy.ndimage as ndi
from PIL import Image
import pytesseract

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ocr_cache

Image.MAX_IMAGE_PIXELS = None
MIN_NODE_AREA = 1200
EDGE_MIN_AREA = 150
TEXT_MIN_AREA = 60     # a flat floor, kept only for the diagrams whose type this
                       # run never measured; text_floor() scales it with the type
ARROW_PROBE_R = 45
TEXT_CONF = 45         # below this tesseract is reading line-work, not words:
                       # every real label on UpdateCatalogueItemSpecification
                       # scores 83-96 and the three arrowheads it read as text
                       # score 39, 0 and 0. The floor sits below the gap rather
                       # than in the middle of it because a real word can land
                       # low - CRP-BaseArticleCatalogue's "Retailer" reads 58,
                       # and a threshold at 55 is a coin toss for it
LABEL_PAD = 6          # breathing room around a label crop; tesseract reads a
                       # tightly clipped glyph as a different glyph


def load_ink(path):
    im = Image.open(path)
    bg = Image.new("RGB", im.size, "white")
    bg.paste(im, mask=im.split()[-1] if im.mode in ("RGBA", "LA") else None)
    return np.asarray(bg.convert("L")) < 128, bg


def text_floor(font_px):
    """The smallest piece of ink that can still be a letter of this diagram's type.

    A flat 60 pixels is right for artwork set at 40px and wrong at both ends of the
    range this set covers. The "o" of the "No" beside a decision on
    GoodsItemPassportApproval, whose type is 26px, is 59 pixels - one short - so it
    was discarded, its "N" was left alone and then too small to be a text block, and
    the guard went missing from four transport diagrams. A letter's area goes with
    the square of the type size, so the floor does too."""
    return max(20, int(0.05 * font_px * font_px)) if font_px else TEXT_MIN_AREA


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


def line_like(ink, box, font_px):
    """Is this band a stroke of line-work rather than words.

    Tesseract is confident about shapes that are not letters: the arrowhead and
    the line it sits on came back as "\\ Ne" at 78 out of 100 on
    SelfBillingwithCreditNote, well clear of any floor a real short label like
    "No" has to pass. The ink settles it instead. A word is a row of small marks,
    none of them much longer than the type is tall; a stroke of line-work is one
    long thin mark, and nothing in this artwork's text ever is."""
    sub = ink[box["y"]:box["y"] + box["h"], box["x"]:box["x"] + box["w"]]
    if sub.size == 0 or font_px <= 0:
        return False
    lbl, n = ndi.label(sub, structure=np.ones((3, 3), bool))
    if n == 0:
        return False
    total = int(sub.sum())
    long_ink = 0
    for sl in ndi.find_objects(lbl):
        if sl is None:
            continue
        yy, xx = np.where(lbl[sl] > 0)
        if yy.size < 12:
            continue
        cx, cy = float(xx.mean()), float(yy.mean())
        cov = np.cov(np.vstack([xx - cx, yy - cy]))
        ev = np.linalg.eigvalsh(cov)
        if ev[0] < 0.05 or ev[1] < 16.0 * ev[0]:      # 4:1 or it is not a stroke
            continue
        span = max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start)
        if span >= 0.75 * font_px:
            long_ink += int(yy.size)
    return long_ink >= 0.3 * max(total, 1)


def word_groups(ink, box, font_px):
    """A line band split into the runs of ink a reader would call words.

    The text blocks are merged by proximity, so an arrowhead lying beside a label
    joins its band and rides in on the label's good name - "[accept credit]" came
    back as "[accept credit] \\ Ne" on SelfBillingwithCreditNote. Splitting the
    band at the gaps lets each run be judged on its own."""
    sub = ink[box["y"]:box["y"] + box["h"], box["x"]:box["x"] + box["w"]]
    if sub.size == 0:
        return []
    col = sub.any(axis=0)
    gap = max(6, int(round(0.55 * font_px)))
    out, i = [], 0
    while i < col.size:
        if not col[i]:
            i += 1
            continue
        j = i
        run = 0
        while j < col.size and run <= gap:
            run = 0 if col[j] else run + 1
            j += 1
        end = j - run
        out.append(dict(box, x=box["x"] + i, w=max(1, end - i)))
        i = j
    return out


def ocr_best_conf(bg, x, y, w, h, inset=0):
    """How sure tesseract is of the best word it found in this block.

    Free line-work that is not a node and not a connector gets read as text, and
    an arrowhead that the node erasure cut away from its own line reads as "TZ",
    "L" or "\\V/" - three of them on UpdateCatalogueItemSpecification alone,
    drawn on the page as text the artwork does not have. Tesseract knows: every
    real label on that diagram scores 83 to 96 and those three score 39, 0 and 0.
    So ask it, and take the best word rather than the average, so that one word
    misread inside a real label does not throw the label away."""
    x0, y0, x1, y1 = x + inset, y + inset, x + w - inset, y + h - inset
    if x1 - x0 < 10 or y1 - y0 < 10:
        return 0
    crop = bg.crop((x0, y0, x1, y1)).convert("L")
    crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
    d = pytesseract.image_to_data(crop, config="--psm 6",
                                  output_type=pytesseract.Output.DICT)
    best = [int(float(c)) for t, c in zip(d["text"], d["conf"]) if t.strip()]
    return max(best) if best else 0


def ocr_inside(bg, ink, n, pad=6):
    """Read a node's label with the node's own outline taken out of the picture.

    A rhombus writes its label straight across the middle, where its two slanted
    edges run within a few pixels of the glyphs, and tesseract joins them up: the
    "OK?" on Tender-ContractInfoPrep came back as "DK'" and "JK'" - the O picking
    up the left edge as a D, the ? picking up the right edge as an apostrophe.
    Insetting a rectangle cannot help, because the border is diagonal and crosses
    every rectangle that holds the text.

    The interior mask can, and exactly: it is the enclosed white area, so the
    stroke is outside it whatever the shape. Everything outside it is painted
    white, which leaves the glyphs alone on the page. Returns "" when the shape
    holds no glyphs, which is how an unlabelled diamond reads."""
    m = n.get("mask")
    if m is None or m.shape != (n["h"], n["w"]):
        return None                      # caller falls back to reading a rectangle
    g = m & ink[n["y"]:n["y"] + n["h"], n["x"]:n["x"] + n["w"]]
    ys, xs = np.nonzero(g)
    if xs.size < 10:
        return ""
    x0, x1 = max(0, int(xs.min()) - pad), min(n["w"], int(xs.max()) + pad + 1)
    y0, y1 = max(0, int(ys.min()) - pad), min(n["h"], int(ys.max()) + pad + 1)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return ""
    crop = np.asarray(bg.crop((n["x"] + x0, n["y"] + y0,
                               n["x"] + x1, n["y"] + y1)).convert("L"))
    crop = np.where(m[y0:y1, x0:x1], crop, 255).astype(np.uint8)
    im = Image.fromarray(crop)
    im = im.resize((im.width * 3, im.height * 3), Image.LANCZOS)
    t = pytesseract.image_to_string(im, config="--psm 6")
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


def enclosed_regions(ink, min_area=MIN_NODE_AREA, min_dim=0.0):
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
        y0, x0 = sl[0].start, sl[1].start
        h, w = sl[0].stop - y0, sl[1].stop - x0
        # An area floor is a proxy for "big enough to be a symbol", and it reads a
        # ring or a diamond - mostly hole - as smaller than it is. The activity
        # final on UBL-1.0-ProcurementProcess is a 23x23 annulus of 285 pixels
        # against a floor of 470, so the only end event on the diagram was never
        # a candidate. A symbol is also wide *and* tall, which a letter's counter
        # is not: those run 11x16 against 28px type on the same page.
        if area < min_area and not (min_dim and min(w, h) >= min_dim):
            continue
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
        # ...read off the first row and column that are actually the shape's edge.
        # Taking row 0 as given is what this did, and row 0 of "Prepare Prior
        # Notice" on Tender-ContractInfoPrep is a single anti-aliased pixel 780
        # columns in: the corner then measured 808 on an 877-wide box, SVG clamped
        # it to half the width, and a stadium was drawn as an ellipse. One pixel
        # is not an edge; ask for a few.
        def first_edge(lines):
            for i in range(min(4, len(lines))):
                if lines[i].sum() >= 3:
                    return int(np.argmax(lines[i]))
            return 0
        rx = first_edge(solid) if solid.any() else 0
        ry = first_edge(solid.T) if solid.any() else 0
        rx += int(round(math.sqrt(rx))) if rx else 0
        ry += int(round(math.sqrt(ry))) if ry else 0
        out.append(dict(x=int(x0), y=int(y0), w=int(w), h=int(h),
                        area=area, fill=round(area / (w * h), 3),
                        solid=round(float(solid.sum()) / (w * h), 3),
                        rx=rx, ry=ry, mask=solid))
    return out


def glyph_height(bg, min_conf=30, path=None):
    """Median height of a word in this diagram's own type, read once off the
    original.

    The phantom filter needs to know how big a letter is before it can tell a
    node's own label from a node: the counters of letters - the holes in O, Q, R -
    are enclosed regions like any other, and a box that encloses one would
    otherwise delete itself. The type size measured later comes from node labels,
    which is circular here, so this reads it independently. Returns 0 if nothing
    legible was found, and the caller falls back to a relative-area test."""
    try:
        words = ocr_cache.word_boxes(bg, path=path, config="--psm 11",
                                     min_conf=min_conf)
    except Exception:
        return 0.0
    hs = [h for _, _, _, h, _, _ in words]
    return float(np.median(hs)) if hs else 0.0


def _across(m, row, col, cap):
    """how far the ink at (row, col) reaches across the line, counted up to cap+1"""
    H, W = m.shape
    if not (0 <= row < H) or not m[row, col]:
        return cap + 1
    n, c = 1, col - 1
    while c >= 0 and m[row, c] and n <= cap:
        n, c = n + 1, c - 1
    c = col + 1
    while c < W and m[row, c] and n <= cap:
        n, c = n + 1, c + 1
    return n


def bridge_runs(mask, forbidden, gap, minrun, maxw, axis):
    """Rejoin a straight line that a label interrupts.

    A guard label is set ON the connector it belongs to, with a white halo, so the
    connector arrives as two or three separate components. Neither piece then
    touches two nodes, so the edge is dropped - and the edge really is gone from
    the SVG, which is what the structural check reports as an absent element.

    So close the gap, but only where it is certainly one line: the ink either side
    continues for at least `minrun`, it is no more than `maxw` across (a stroke,
    not the flank of something solid), the whole span is at most `gap`, and no
    erased node lies in it - the two sides of a node are two different edges and
    joining them would invent a connection. Runs shorter than `minrun` between the
    two are stepped over: those are the glyphs sitting on the line.

    Returns the spans to fill as (axis, line, start, end), so that the caller can
    join the *components* the span links without redrawing the page: filling the
    pixels and re-labelling would also swallow any glyph that happens to touch the
    new ink, and those glyphs are the label, which still has to be read.

    axis=0 rejoins vertical lines, axis=1 horizontal."""
    m = mask if axis == 0 else mask.T
    f = forbidden if axis == 0 else forbidden.T
    H, _ = m.shape
    joined = []
    for c in np.where(m.sum(axis=0) >= 2 * minrun)[0]:
        col = m[:, c]
        d = np.diff(col.astype(np.int8))
        starts, ends = list(np.where(d == 1)[0] + 1), list(np.where(d == -1)[0] + 1)
        if col[0]:
            starts.insert(0, 0)
        if col[-1]:
            ends.append(H)
        longs = [(s, e) for s, e in zip(starts, ends) if e - s >= minrun]
        for k in range(len(longs) - 1):
            a, b = longs[k][1], longs[k + 1][0]
            if not (0 < b - a <= gap) or f[a:b, c].any():
                continue
            if _across(m, a - 1, c, maxw) > maxw or _across(m, b, c, maxw) > maxw:
                continue
            joined.append((axis, int(c), int(a), int(b)))
    return joined


def trace_corners(xs, ys, p_from, p_to, stroke, max_turns=8):
    """Where an orthogonal connector actually turns.

    Knowing only that an edge runs from A to B and that its routing is
    "orthogonal" is not enough to put it back: a loop-back that leaves a decision,
    runs to the right margin, climbs the page and comes in at the top gets redrawn
    with its corner wherever the router chooses, which in the diff is a line
    missing in one place and invented in another. The corners are in the pixels,
    so read them.

    Walk the connector's own ink from one end to the other (a breadth-first walk,
    so the route is the one the ink takes), split that walk into straight runs,
    and put each run back on the centre of the stroke it came from - the walk
    hugs the inside of every corner, which is half a stroke off. Returns the
    interior corners only, or [] when the ink does not resolve into a small number
    of clean straight runs."""
    from collections import deque
    x0, y0 = int(xs.min()), int(ys.min())
    W = int(xs.max()) - x0 + 1
    H = int(ys.max()) - y0 + 1
    if W * H > 40 * 10 ** 6:
        return []
    comp = np.zeros((H, W), bool)
    comp[ys - y0, xs - x0] = True

    start = (int(p_from[1]) - y0, int(p_from[0]) - x0)
    goal = (int(p_to[1]) - y0, int(p_to[0]) - x0)
    if not (comp[start] and comp[goal]):
        return []
    prev = np.full(H * W, -1, np.int64)
    si, gi = start[0] * W + start[1], goal[0] * W + goal[1]
    prev[si] = si
    q = deque([si])
    while q:
        i = q.popleft()
        if i == gi:
            break
        r, c = divmod(i, W)
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1),
                       (1, 1), (1, -1), (-1, 1), (-1, -1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < H and 0 <= cc < W and comp[rr, cc]:
                j = rr * W + cc
                if prev[j] < 0:
                    prev[j] = i
                    q.append(j)
    if prev[gi] < 0:
        if os.environ.get("UBL_TRACE_DEBUG"):
            print("      trace: no path from %s to %s" % (p_from, p_to))
        return []
    path, i = [], gi
    while i != si:
        r, c = divmod(i, W)
        path.append((c, r))
        i = prev[i]
    path.append((start[1], start[0]))
    path.reverse()

    # split into runs that hold one axis still; anything shorter than a few
    # strokes is the diagonal shortcut the walk takes across a corner
    tol = max(2, int(stroke))
    minrun = max(12, 4 * tol)
    runs, i, npt = [], 0, len(path)
    while i < npt - 1:
        # which way a run goes has to be read from a stretch of it, not from the
        # next step: every step is one pixel, so the first step of a horizontal
        # run looks vertical as well, and seeding the axis from it cut every
        # horizontal run off after a few pixels
        k = min(i + minrun, npt - 1)
        ax = ("v" if abs(path[k][1] - path[i][1]) >= abs(path[k][0] - path[i][0])
              else "h")
        j = i
        while j + 1 < npt:
            off = (abs(path[j + 1][0] - path[i][0]) if ax == "v"
                   else abs(path[j + 1][1] - path[i][1]))
            if off > tol:
                break
            j += 1
        if j - i >= minrun:
            runs.append((ax, path[i:j + 1]))
        i = j + 1
    if os.environ.get("UBL_TRACE_DEBUG"):
        print("      trace: path %d px, %d run(s) %s"
              % (len(path), len(runs), [(a, len(sg)) for a, sg in runs]))
    if not (2 <= len(runs) <= max_turns + 1):
        return []
    # the straight runs have to account for nearly all of the walk. Where two
    # lines cross they arrive as one component, and a diagonal that crosses
    # another line is read as "orthogonal" because the pixels of both are in the
    # fit; tracing that gives a staircase the artwork does not have. A real
    # orthogonal route is covered by its runs but for the corners.
    if sum(len(seg) for _, seg in runs) < 0.8 * len(path):
        return []

    # put each run on the centre of its own stroke, measured where the run is
    # clear of its corners
    fixed = []
    for ax, seg in runs:
        mid = seg[len(seg) // 2]
        if ax == "v":
            row = comp[mid[1]]
            c = mid[0]
            a = b = c
            while a > 0 and row[a - 1]:
                a -= 1
            while b + 1 < W and row[b + 1]:
                b += 1
            fixed.append(("v", (a + b) / 2.0 + x0,
                          (seg[0][1] + y0, seg[-1][1] + y0)))
        else:
            col = comp[:, mid[0]]
            r = mid[1]
            a = b = r
            while a > 0 and col[a - 1]:
                a -= 1
            while b + 1 < H and col[b + 1]:
                b += 1
            fixed.append(("h", (a + b) / 2.0 + y0,
                          (seg[0][0] + x0, seg[-1][0] + x0)))

    # One straight line can arrive as two runs on the same axis, split where the
    # walk steps around a crossing line or into the arrowhead. If they lie on the
    # same line, they are the same run and are merged; if they do not, this is a
    # jog the trace has not resolved and nothing is claimed.
    merged = []
    for run in fixed:
        if merged and merged[-1][0] == run[0]:
            if abs(merged[-1][1] - run[1]) > 2 * max(1, tol):
                return []
            prev = merged[-1]
            merged[-1] = (prev[0], (prev[1] + run[1]) / 2.0,
                          (min(prev[2][0], run[2][0]), max(prev[2][1], run[2][1])))
            continue
        merged.append(run)
    if len(merged) < 2:
        return []

    corners = []
    for (a1, v1, _), (a2, v2, _) in zip(merged, merged[1:]):
        corners.append([int(round(v1)), int(round(v2))] if a1 == "v"
                       else [int(round(v2)), int(round(v1))])
    return corners


def corridor(ink, node_fill, pa, pb, pad):
    """The original's own ink along a connector, with the nodes taken out.

    The head has to be measured on the page, not on the connector component: the
    component has the node boxes erased from around it, and where two elements sit
    close together - "Send Exception Criteria" and the document beside it, 99px
    apart - that erasure takes most of the arrowhead with it, leaving the
    direction to be decided by whatever ink happens to remain. Node outlines are
    excluded so that a box's own edge, which lies across the probe at every
    contact, cannot be read as a head."""
    x0 = max(0, min(pa[0], pb[0]) - pad)
    x1 = min(ink.shape[1], max(pa[0], pb[0]) + pad + 1)
    y0 = max(0, min(pa[1], pb[1]) - pad)
    y1 = min(ink.shape[0], max(pa[1], pb[1]) + pad + 1)
    sub = ink[y0:y1, x0:x1] & ~node_fill[y0:y1, x0:x1]
    ys, xs = np.where(sub)
    if xs.size == 0:
        return np.array([]), np.array([])
    xs, ys = xs + x0, ys + y0
    vx, vy = pb[0] - pa[0], pb[1] - pa[1]
    L = math.hypot(vx, vy) or 1.0
    dx, dy = vx / L, vy / L
    t = (xs - pa[0]) * dx + (ys - pa[1]) * dy
    u = np.abs(-(xs - pa[0]) * dy + (ys - pa[1]) * dx)
    keep = (t >= -pad) & (t <= L + pad) & (u <= pad)
    return xs[keep], ys[keep]


def wedge(shape, apex, dx, dy, length, width, pad=2.0, inner=0.0, outer=None):
    """The triangle an arrowhead occupies, as a mask and the box holding it.

    One definition, used by the extractor to ask whether the head is filled and by
    the referee to ask whether the rebuild drew one at all. Two definitions would
    drift apart, and the referee would then be measuring a region the drawing
    never claimed."""
    L = max(float(length), 1.0)
    y0, y1 = int(max(0, apex[1] - L - pad)), int(min(shape[0], apex[1] + L + pad + 1))
    x0, x1 = int(max(0, apex[0] - L - pad)), int(min(shape[1], apex[0] + L + pad + 1))
    if y1 <= y0 or x1 <= x0:
        return None, (0, 0, 0, 0)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    t = -((xx - apex[0]) * dx + (yy - apex[1]) * dy)      # back from the point
    u = np.abs(-(xx - apex[0]) * dy + (yy - apex[1]) * dx)
    # `inner` leaves the shaft out. The connector runs up the middle of its own
    # arrowhead and is drawn whether or not the head is, so counting it answers
    # a question nobody asked: with the shaft in, a head that is plainly there and
    # one that was never drawn differ by a fifth, and with it out they differ by
    # everything.
    # `outer` widens the triangle into the sector behind the point - everywhere a
    # head of this length could have put ink, whatever angle it was drawn at. The
    # triangle is the right region for asking how a head is drawn, because it is
    # where a filled one differs from an open one; it is the wrong region for
    # asking *whether* one is drawn, because a head a few pixels wider or set a
    # few pixels along falls outside it and reads as absent.
    lim = float(outer) if outer else (width / 2.0) * np.clip(t / L, 0, 1)
    return (t >= -pad) & (t <= L + pad) & (u >= inner) & (u <= lim + pad), \
           (y0, y1, x0, x1)


def dash_run(ink, node_fill, pa, pb, stroke, trim=0.0):
    """Is this connector drawn dashed, and to what pattern.

    UBL draws one kind of flow as a dashed line - the "prior exchange of public
    keys" that the two Tender-Contract diagrams put across their lane divider -
    and drawing it solid states something the artwork does not. The pattern is in
    the ink: walk the line and record where there is ink under it, then read off
    the runs. A solid connector has one run, a dashed one has several with gaps of
    the same size between them.

    `trim` keeps the arrowheads out of it; they are solid whatever the line does.
    Returns (dash, gap) in pixels, or None."""
    L = math.hypot(pb[0] - pa[0], pb[1] - pa[1])
    if L < 60:
        return None
    ux, uy = (pb[0] - pa[0]) / L, (pb[1] - pa[1]) / L
    half = max(3, int(round(2 * stroke)))
    lo, hi = int(max(0, trim)), int(min(L, L - trim))
    if hi - lo < 40:
        return None
    ts = np.arange(lo, hi + 1)
    ofs = np.arange(-half, half + 1)
    xx = np.clip(np.rint(pa[0] + ux * ts[:, None] - uy * ofs[None, :]).astype(int),
                 0, ink.shape[1] - 1)
    yy = np.clip(np.rint(pa[1] + uy * ts[:, None] + ux * ofs[None, :]).astype(int),
                 0, ink.shape[0] - 1)
    # the node boxes stay in: a connector that runs over one is not dashed, and
    # taking them out left a gap exactly where it crossed. Tender-AwardPublication
    # draws a solid line the length of the page over three of them, and it read as
    # a 115/101 dash pattern.
    occ = ink[yy, xx].any(axis=1)

    runs, i = [], 0
    while i < occ.size:
        j = i
        while j < occ.size and occ[j] == occ[i]:
            j += 1
        runs.append([bool(occ[i]), j - i])
        i = j
    # a one-pixel break in a dash, or a one-pixel speck in a gap, is anti-aliasing
    merged = []
    for v, n in runs:
        if merged and n <= 2:
            merged[-1][1] += n
        elif merged and merged[-1][0] == v:
            merged[-1][1] += n
        else:
            merged.append([v, n])
    gaps = [n for v, n in merged[1:-1] if not v]
    dashes = [n for v, n in merged[1:-1] if v]
    if len(gaps) < 3 or not dashes:
        return None
    # ...allowing for one gap that another line happens to run through: the dashed
    # diagonal on FulfilmentDespatchAdvice crosses a solid one, and the crossing
    # fills a gap, which a strict evenness test reads as "not dashed at all".
    if min(gaps) < max(4, stroke) or max(gaps) > 3.0 * min(gaps):
        return None
    if sum(gaps) < 0.15 * (hi - lo):
        return None
    return round(float(np.median(dashes)), 1), round(float(np.median(gaps)), 1)


def arrow_size(xs, ys, tip, back, stroke, limit=None, need_point=False, min_len=0.0,
               ahead=0, max_wide=0.0):
    """How big the arrowhead at `tip` is, in the original's own pixels.

    The rebuild drew every arrowhead at one hard-coded size, so the same head
    appeared on artwork drawn at 26px type and at 84px type: on the small
    diagrams it swamped the node it pointed at. The head is in the pixels like
    everything else - it is the stretch just behind the tip where the connector is
    wider than its own stroke.

    `tip` is where the *trace* ended, which is not where the head's point is: the
    walk down the centre of a connector stops as soon as the ink fans out, so it
    stops inside the head and the point carries on ahead of it to the node's
    border. Measured only backwards from there, a 26px head on
    GoodsItemPassportApproval reads as 13px - and the rebuild then drew every head
    at half the artwork's size, which no pixel difference could name because a
    half-size head still sits inside the original's. Pass `ahead` to walk forward
    to the real point as well, as far as the ink keeps narrowing; the direction
    tests do not, so what decides which end carries the head is untouched.

    Returns (length, width) or None when the ink near the tip says nothing useful
    (crossing line-work, or a connector that has no head at this end)."""
    dx, dy = tip[0] - back[0], tip[1] - back[1]
    L = math.hypot(dx, dy)
    if L < 1:
        return None
    dx, dy = dx / L, dy / L
    rel_x, rel_y = xs - tip[0], ys - tip[1]
    t = -(rel_x * dx + rel_y * dy)             # distance back from the tip
    u = np.abs(-rel_x * dy + rel_y * dx)       # distance across the line
    # never probe further than halfway along the connector: past that the probe
    # reaches the head at the *other* end, and then the tail also looks like ink
    # that widens away from it - which flipped seventeen edges the wrong way round
    cap = int(max(30.0, 16.0 * stroke))
    if limit:
        cap = int(min(cap, max(8.0, 0.5 * limit)))
    # only ink that could belong to a wedge with its point here: a barb leaves the
    # tip at an angle, so at distance t it is at most about t across. A line
    # running parallel a fixed distance away - a second connector converging on
    # the same node, which UBL draws often - is outside that cone and no longer
    # counts as this head, which it did before, complete with a convincing taper.
    body0 = max(0.5, stroke / 2.0)
    sel = (t >= -2) & (t <= cap) & (u <= 1.2 * np.maximum(t, 0.0) + 3 * body0)
    if sel.sum() < 8:
        return None
    # how far the ink reaches across the line, a pixel-step at a time back from
    # the tip
    half = np.zeros(cap + 2)
    ti = np.clip(t[sel].astype(int), 0, cap + 1)
    np.maximum.at(half, ti, u[sel])

    # `stroke` is the connector's own weight, measured by the caller at the middle
    # of the line where there is no head. Estimating it from the far end of this
    # probe instead - which is what this did - fails whenever the head is longer
    # than a fraction of the probe, because then the "far end" is still head: on
    # this artwork that silently measured no head at all on most connectors.
    body = max(0.5, stroke / 2.0)
    thresh = max(body * 1.6, body + 1.5)

    # A point is narrow. Where several connectors converge on one node the ink at
    # the far end of a probe fans out and looks like a wedge from either side, so
    # the test that settles it is the tip itself: an arrowhead begins at the width
    # of its own line and widens from there. Ink that is already several strokes
    # across where the point should be is not a point.
    if need_point and float(half[0:3].max()) > max(2.5 * body, body + 3.0):
        return None

    # An open "V" head is two strokes that meet at the tip, so at the tip itself
    # the ink is no wider than the line: walk outward and take the last step that
    # is still clearly wider, allowing a short break for the anti-aliased join.
    gap, run, length = max(4, int(2 * body)), 0, 0
    for i in range(1, cap + 1):
        if half[i] >= thresh:
            length, run = i, 0
        else:
            run += 1
            if run > gap:
                break
    if length < 2:
        return None
    # the tip usually lands on the node's own border, which runs across the probe
    # and would otherwise be measured as an enormously wide head
    width = min(2.0 * float(half[1:length + 1].max()), 2.5 * length)
    if length < 2 * body or width < 2 * body:
        return None

    # Everything that judges what this ink *is* - whether it clears the size floor
    # below, and which way it tapers - keeps reading the stretch behind the tip,
    # so adding the forward walk cannot make a join pass for a head or turn an
    # edge round. It only makes the head that is there measure its full length.
    back_len = length

    # Forward, to the point. Beyond the trace's end the head is still narrowing,
    # so take every step that stays ink and stays no wider than the step before
    # it. The node's border is the wall that stops this: it crosses the probe and
    # widens it again in a single step, and the head ends there, which is exactly
    # where the artwork draws the point.
    front = 0
    if ahead > 0:
        w0 = max(float(half[0:3].max()), body)
        fwd = (t < 0) & (t >= -ahead) & (u <= w0 + 2.0)
        if fwd.any():
            fi = np.clip((-t[fwd]).astype(int), 0, ahead)
            fh = np.zeros(ahead + 1)
            seen = np.zeros(ahead + 1, bool)
            np.maximum.at(fh, fi, u[fwd])
            seen[fi] = True
            prev = w0
            for j in range(1, ahead + 1):
                if not seen[j] or fh[j] > prev + 1.0:
                    break
                front, prev = j, min(prev, fh[j])
            length += front
    # An arrowhead is a mark of the diagram's own size. Ten pixels of ink where a
    # connector meets a box is a join or a corner, not a head - and taken for one
    # it pointed "Send Trade Item Location Profile" at the wrong element. It has an
    # upper bound for the same reason: across all 78 diagrams a head is 0.6 to 1.8
    # times the type size across, so ink three times that is the box's own edge
    # lying across the probe. Where two lines converge on one point - the apex of
    # a decision diamond, which takes three at once - that is the only thing
    # telling the two ends apart, and without it the solid diagonal on
    # FulfilmentDespatchAdvice pointed away from the diamond its head is drawn at.
    if back_len < min_len or (max_wide and width > max_wide):
        return None
    # Which end is the point. An arrowhead is a wedge, so its ink is narrow at the
    # tip and wide away from it; probed from the *other* end the same ink is wide
    # at the near end and narrow further along. Width alone therefore reads the
    # same at both ends of a head - which is how "Send Exception Criteria" came
    # out pointing at the wrong element, its head being nearly as long as the
    # 99px gap it sits in. The taper is what tells them apart.
    lo = half[1:max(2, back_len // 3) + 1]
    hi = half[max(1, 2 * back_len // 3):back_len + 1]
    taper = (float(hi.mean()) / max(float(lo.mean()), 0.5)) if lo.size and hi.size else 1.0
    # the fourth value is how far in front of `tip` the point turned out to be, so
    # a caller that wants to look at the head's own pixels knows where it is; the
    # fifth says the walk backwards ran to the end of its probe without finding
    # where the head stops, which makes the length the probe's and not the head's
    return round(length, 1), round(width, 1), round(taper, 2), front, back_len >= cap - 1


def is_fold(a, b):
    """Is `b` the folded corner of the note `a` rather than a region inside it.

    A note is a rectangle with one corner turned over, and the turned corner traps
    a small triangle of white in that corner. It is small, it is about as wide as
    it is tall, it is roughly half the ink of its own box, and it sits in a corner
    - so it is nothing like the enclosed region the test around this is for, which
    is a node drawn inside another node."""
    if b["area"] > 0.06 * a["w"] * a["h"]:
        return False
    if not (0.25 <= b.get("fill", 1.0) <= 0.75):
        return False
    if max(b["w"], b["h"]) > 1.6 * max(1, min(b["w"], b["h"])):
        return False
    tol = max(8.0, 0.05 * min(a["w"], a["h"]))
    return ((abs(b["y"] - a["y"]) <= tol
             or abs(b["y"] + b["h"] - a["y"] - a["h"]) <= tol)
            and (abs(b["x"] - a["x"]) <= tol
                 or abs(b["x"] + b["w"] - a["x"] - a["w"]) <= tol))


def cross_stub(xs, ys, vr, hr, font_px):
    """Half of a short stroke drawn across a partition rule, or None.

    UBL puts a pair of diagonal strokes across the lane divider under the document
    box on BusinessCard and DigitalCapability. They belong to no node and no
    connector, so they were binned with the text, failed to read as text, and
    vanished off the page. They do not even arrive whole: the rule's ink is taken
    out before the components are found, so each stroke comes in two halves, one
    either side of it.

    A half is straight, short, slanted - a divider's own ink is not, and a glyph is
    neither - and it stops at the rule. The caller puts the halves back together."""
    if xs.size < 20 or font_px <= 0:
        return None
    cx, cy = float(xs.mean()), float(ys.mean())
    cov = np.cov(np.vstack([xs - cx, ys - cy]))
    ev, evec = np.linalg.eigh(cov)
    if ev[0] < 0.05 or ev[1] < 12.0 * ev[0]:          # 3.5:1, or it is not a stroke
        return None
    ux, uy = float(evec[0, 1]), float(evec[1, 1])
    t = (xs - cx) * ux + (ys - cy) * uy
    half = float(t.max() - t.min()) / 2.0
    if not (0.5 * font_px <= 2.0 * half <= 3.0 * font_px):
        return None
    ang = math.degrees(math.atan2(uy, ux)) % 180.0
    # Slanted, and to both axes. A stub that runs along the rule is the rule; one
    # square to it is a connector that stopped there, and ProcurementProcess has
    # three of those. The mark this is for is drawn at a slant - 34 degrees on
    # BusinessCard - which is what makes it a mark rather than more line-work.
    if min(ang, 180.0 - ang) < 15.0 or abs(ang - 90.0) < 15.0:
        return None
    for axis, rules in (("v", vr), ("h", hr)):
        for start, w in rules:
            mid = start + w / 2.0
            side = (xs - mid) if axis == "v" else (ys - mid)
            near = min(abs(float(side.min())), abs(float(side.max())))
            if near <= w + 3 and (side.min() >= -w - 3 or side.max() <= w + 3):
                return dict(rule=axis, at=int(round(mid)), angle=round(ang, 1),
                            cx=cx, cy=cy, ux=ux, uy=uy, half=half,
                            x1=cx - ux * half, y1=cy - uy * half,
                            x2=cx + ux * half, y2=cy + uy * half,
                            weight=round(4.0 * math.sqrt(max(float(ev[0]), 0.05)), 1))
    return None


def join_stubs(stubs):
    """Put the halves of each stroke back together: same slant, same line, same
    rule. A half with no partner is still ink and is kept as it stands."""
    out, used = [], set()
    for i, a in enumerate(stubs):
        if i in used:
            continue
        best = None
        for j, b in enumerate(stubs):
            if j <= i or j in used or b["rule"] != a["rule"]:
                continue
            da = abs(a["angle"] - b["angle"])
            if min(da, 180.0 - da) > 12.0:
                continue
            # the same line: the other's centre lies on this one's axis
            off = abs(-(b["cx"] - a["cx"]) * a["uy"] + (b["cy"] - a["cy"]) * a["ux"])
            if off > 6.0:
                continue
            if best is None or off < best[1]:
                best = (j, off)
        pts = [(a["x1"], a["y1"]), (a["x2"], a["y2"])]
        if best is not None:
            b = stubs[best[0]]
            used.add(best[0])
            pts += [(b["x1"], b["y1"]), (b["x2"], b["y2"])]
        used.add(i)
        p0 = min(pts, key=lambda p: p[0] * a["ux"] + p[1] * a["uy"])
        p1 = max(pts, key=lambda p: p[0] * a["ux"] + p[1] * a["uy"])
        out.append(dict(rule=a["rule"], at=a["at"], angle=a["angle"],
                        weight=a["weight"], whole=best is not None,
                        x1=int(round(p0[0])), y1=int(round(p0[1])),
                        x2=int(round(p1[0])), y2=int(round(p1[1])),
                        length=round(math.hypot(p1[0] - p0[0], p1[1] - p0[1]), 1)))
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
    def score(t):
        # how well this template matches, against the best it could manage at this
        # size. Ranking on the raw overlap quietly prefers blunt shapes when the
        # shape is small, because a pointy one loses more of its area to the same
        # one-pixel uncertainty: UBL-1.0-ProcurementProcess's 29px decision nodes
        # read 0.818 as a rounded box and 0.816 as a rhombus, and were drawn with
        # round corners on a coin toss. Against each template's own ceiling the
        # same four read 1.10-1.14 rhombus and 0.98-0.99 rounded, which is not a
        # close call.
        inter = float((m & t).sum())
        raw = inter / float(max((m | t).sum(), 1))
        er = ndi.binary_erosion(t, np.ones((3, 3)))
        ceil = max(float(er.sum()) / float(max(t.sum(), 1)), 0.5)
        return raw / ceil, raw, ceil
    best = max(((name, t) + score(t) for name, t in cands), key=lambda p: p[2])
    # ...and how well the best template could possibly have been matched at this
    # size. A drawn outline is anti-aliased, so where its interior ends is uncertain
    # by about a pixel all round, and that pixel costs a small shape far more of its
    # own area than a large one: perimeter over area goes as 1/size. Eroding the
    # template by one pixel measures exactly that cost. UBL-1.0-ProcurementProcess
    # draws its four decision nodes 29px across, where a perfect rhombus can only
    # reach 0.81; they read 0.82-0.85 and a flat 0.88 floor discarded all four, and
    # the flows through them were then attributed to whatever stood at the far end.
    # The same floor read against this ceiling keeps them and still drops the
    # whitespace trapped between crossing connectors, which matches no outline at
    # any size (0.47-0.71 here, against ceilings of 0.96 and up).
    return best[3], best[0], best[4]


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
    if not ink[n["y"] + n["h"] // 2, n["x"] + n["w"] // 2]:
        return False
    # ...and the ink at the centre has to be the filled disc, not a word. The
    # "OK?" decision on Tender-AwardPublication is 203px square with its label
    # across the middle, so a pixel at the centre is a letter and the diamond was
    # called an end event - which then fixed the direction of both flows through
    # it the wrong way round. A disc runs a fifth of the radius out from the
    # centre in every direction; a glyph stroke stops at once.
    return inner_disc_ratio(ink, n) >= 0.2


def interior_ink(ink, n, inset=20):
    """fraction of the region's interior that carries ink - i.e. does it hold a
    label. Whitespace merely trapped between other shapes holds nothing.

    The inset keeps the shape's own outline out of the sample, so it has to be
    smaller than the shape: at a flat 20px every region 40px or less across
    sampled an empty array and read 0.0 - not "holds no label" but "was never
    looked at"."""
    inset = min(inset, max(1, min(n["w"], n["h"]) // 4))
    sub = ink[n["y"] + inset:n["y"] + n["h"] - inset,
              n["x"] + inset:n["x"] + n["w"] - inset]
    return float(sub.mean()) if sub.size else 0.0


def room_for_a_word(n, glyph_h):
    """could a label have been set inside this region at all.

    "It holds nothing" is evidence that a region is trapped whitespace and not a
    node - but only where something could have been written. A decision node drawn
    29px across, as UBL-1.0-ProcurementProcess draws all four of its own, has
    about 20px of clear width at its widest and the type is 28px tall: there is no
    room for a label, so its absence says nothing either way. Measured off the
    region's own mask rather than its bounding box, because the inscribed width of
    a rhombus is half its box."""
    m = n.get("mask")
    if m is None or not glyph_h:
        return True
    return 2.0 * float(ndi.distance_transform_edt(m).max()) >= glyph_h


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
        iou, a["shape"], ceiling = shape_iou(a)
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
                 # and it has to be big enough to be a node in its own right. The
                 # floor on a region's area now scales with the type, so that a
                 # small activity final's ring is not missed; letting those
                 # smaller regions veto a parent as well cost IMFM three object
                 # nodes, each vetoed by a 34x30 counter in its own bold label.
                 b["area"] >= MIN_NODE_AREA and
                 (b["h"] >= 0.9 * glyph_h if glyph_h else
                  (b["w"] * b["h"]) >= 0.02 * (a["w"] * a["h"])) and
                 # ...and a note's own folded corner is not a region it contains,
                 # it is what makes it a note. SourcingPunchout draws one around
                 # "Transaction accessing Seller's catalogue application" and the
                 # 59x59 triangle its fold encloses deleted the whole box, leaving
                 # the words standing on the page with nothing round them.
                 not is_fold(a, b)
                 for b in regs):
            why = "encloses another region"
        elif is_final_ring(ink, a, ink.shape[1]) or is_note(ink, a):
            why = None
        else:
            open_sides = sides_continue(ink, a)
            if iou < min_iou * ceiling:
                why = ("outline matches no UML node shape (best %s %.2f, and %.2f"
                       " is the most this shape can reach at this size)"
                       % (a["shape"], iou, ceiling))
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
                outline_ok = (iou >= own_iou_curved * ceiling) if curved else \
                             (iou >= own_iou * ceiling and cov >= own_cov)
                if outline_ok and (interior_ink(ink, a) >= min_interior
                                   or not room_for_a_word(a, glyph_h)):
                    kept_by_outline = True
                    a["keptOnOutline"] = True
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
        # a note's fold is measurable, so it is not drawn at a fixed fraction of
        # the box: SourcingPunchout turns a corner 59px across on a 533px box,
        # against the 0.30 of the shorter side the rebuild used to assume
        fold = next((b for b in regs
                     if b is not a and b["x"] >= a["x"] - 2 and b["y"] >= a["y"] - 2
                     and b["x"] + b["w"] <= a["x"] + a["w"] + 2
                     and b["y"] + b["h"] <= a["y"] + a["h"] + 2
                     and is_fold(a, b)), None)
        if fold is not None:
            a["fold"] = int(max(fold["w"], fold["h"]))
        keep.append(a)
    return keep


def stroke_of(ink, n):
    # probe down onto the top edge. A box is sampled at several x so that an
    # incoming connector cannot inflate the result; a round or pointed shape only
    # has its outline at the bbox top in the middle, so there it is sampled once.
    # A rhombus has no outline at the top of its bounding box except at the
    # vertex, where its two edges meet - probing down onto that measures the
    # corner, not the line. The "OK?" decision on Tender-AwardPublication came
    # back at 60px of stroke on a 203px node and was drawn as a blot. Walk out
    # across each edge at its middle instead, at right angles to it, which is
    # what a stroke width is.
    if n.get("shape") == "rhombus":
        H, W = ink.shape
        cx, cy = n["x"] + n["w"] / 2.0, n["y"] + n["h"] / 2.0
        hw, hh = n["w"] / 2.0, n["h"] / 2.0
        L = math.hypot(hw, hh) or 1.0
        runs = []
        for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            px, py = cx + sx * hw / 2.0, cy + sy * hh / 2.0
            nx, ny = sx * hh / L, sy * hw / L      # outward normal of that edge
            t, k = 0, 0
            while k < 60:
                x, y = int(round(px + nx * k)), int(round(py + ny * k))
                if not (0 <= x < W and 0 <= y < H) or not ink[y, x]:
                    if t:
                        break
                else:
                    t += 1
                k += 1
            runs.append(t)
        good = [t for t in runs if t]
        if good:
            return int(np.median(good))
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
    # ...and where the shape reading is unambiguous it beats the fill bands, which
    # are a proxy for it. A rhombus fills half its box in the limit, but a small
    # one fills more: the four 29px decision nodes on UBL-1.0-ProcurementProcess
    # measure 0.59-0.61 and fell through the band into "final", drawn as a
    # bullseye in the middle of a flow. The outline says rhombus at 1.10-1.14 of
    # what a rhombus can reach at that size, against 0.98 for every other shape.
    if n.get("shape") == "rhombus":
        return "decision"
    # an activity final is a ring *around a filled disc*, so there is ink at its
    # centre. Without that this band called anything roundish and half-filled a
    # final, decision nodes included.
    if 0.56 < f <= 0.80 and 0.75 < ar < 1.35 and (
            ink is None or bool(ink[n["y"] + n["h"] // 2, n["x"] + n["w"] // 2])):
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


def disc_blobs(ink, glyph_h, W, H):
    """Initial nodes, found by how thick the ink is rather than by its outline.

    A start node is a filled disc with its outgoing connector attached, and that
    connector survives the erosion that is meant to leave only solid shapes - so
    the component is a disc with a tail, its bounding box is far from square, and
    it was failing the roundness test. Fourteen diagrams had no start node at all
    for that reason, among them every Tender process.

    Thickness does not care about the tail: the distance to the nearest white
    pixel peaks at the disc's own radius in its centre, and at half a stroke
    anywhere along a line. Take the peaks, and keep the ones whose ink really does
    fill the circle they claim."""
    if glyph_h <= 0:
        return []
    dist = ndi.distance_transform_edt(ink)
    lo = max(6.0, 0.55 * glyph_h)                  # smaller than any start node here
    seeds = dist >= lo
    if not seeds.any():
        return []
    lbl, _ = ndi.label(seeds, structure=np.ones((3, 3)))
    out = []
    yy, xx = None, None
    for i, sl in enumerate(ndi.find_objects(lbl), start=1):
        if sl is None:
            continue
        sub = dist[sl] * (lbl[sl] == i)
        r = float(sub.max())
        if not (lo <= r <= 0.06 * W):
            continue
        k = np.unravel_index(int(np.argmax(sub)), sub.shape)
        cy, cx = sl[0].start + k[0], sl[1].start + k[1]
        y0, y1 = int(max(0, cy - r * 1.6)), int(min(H, cy + r * 1.6 + 1))
        x0, x1 = int(max(0, cx - r * 1.6)), int(min(W, cx + r * 1.6 + 1))
        patch = ink[y0:y1, x0:x1]
        if yy is None or yy.shape != patch.shape:
            yy, xx = np.mgrid[0:patch.shape[0], 0:patch.shape[1]]
        rr = np.hypot(yy[:patch.shape[0], :patch.shape[1]] - (cy - y0),
                      xx[:patch.shape[0], :patch.shape[1]] - (cx - x0))
        inside = rr <= r * 0.9
        ring = (rr > r * 1.25) & (rr <= r * 1.5)
        if not inside.any() or not ring.any():
            continue
        # solid inside, and mostly white just outside it: a bar or a thick corner
        # keeps its ink going in the ring, a disc only where its connector leaves
        if patch[inside].mean() > 0.95 and patch[ring].mean() < 0.35:
            out.append(dict(x=int(cx - r), y=int(cy - r), w=int(2 * r), h=int(2 * r),
                            area=int(math.pi * r * r), fill=1.0, kind="initial"))
    return out


def solid_blobs(ink, W, H, glyph_h=0.0):
    """solid ink with no interior: initial nodes and fork/join bars

    `glyph_h` is the height of a word in this diagram's type. A fork bar spans
    several nodes; the stem of an "I" or a "T" in a lane title is solid, thin and
    tall too, and without a length that beats the type it is indistinguishable
    from one - relaxing the fill test alone turned 5 letter stems in "CONTRACTING
    AUTHORITY" into fork bars."""
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
        # ...and a start node is a symbol, drawn at the scale of the page, not a
        # thickening where two strokes meet. Where an open arrowhead lands on the
        # side of a box its two strokes and the outline enclose a solid lump that
        # is round enough and filled enough to pass every other test here: three
        # of them on UBL-1.0-ProcurementProcess, which has no start node at all,
        # and each one then stood between a flow and the box it points at, so the
        # flow arrived as two edges through a node that is not there. Measured
        # across the set, a real start node runs 0.89 to 3.12 times the type size
        # and every phantom 0.41 or less, so the floor sits in open ground. Read
        # in glyph heights, which is what this function is given: the type size
        # the rest of the pipeline uses is about 1.4 glyph heights.
        if (fill > 0.70 and ar < 1.35 and 6 < w < W * 0.06
                and (glyph_h <= 0 or w >= 0.8 * glyph_h)):
            discs.append(dict(d, kind="initial"))
        # ...and the same arrowheads that spoil the fill spoil the aspect. The two
        # join bars on UBL-1.0-ProcurementProcess come out of the erosion 67x28
        # and 71x25 - 2.4:1 and 2.8:1 - because each carries the two arrowheads
        # that meet it, so neither was ever considered a bar and the four flows
        # through them were drawn as elbows between whatever stood at the ends.
        # Judge the band, not the box: find the run of nearly-full rows first, and
        # ask whether *that* is long and thin. The length floor still scales with
        # the type, which is what keeps a letter stem out.
        elif min(w, h) <= 60 and max(w, h) + 6 > max(W * 0.012, 2.5 * glyph_h):
            # A fork or join bar arrives with the arrowheads that meet it still
            # attached after erosion, so the bounding box is taller than the bar
            # and the fill of that box falls well below a solid shape's - 0.56 on
            # UBL-2.2-VMI-InitialStocking's join, against a 0.70 threshold, so the
            # bar was discarded and with it the four connectors that meet it.
            # Measure the bar rather than the box: the run of rows (or columns)
            # that are nearly full across the component's length.
            comp = (lbl[sl] == i)
            cov = comp.mean(axis=1) if w >= h else comp.mean(axis=0)
            dense = np.where(cov >= 0.8)[0]
            if dense.size >= 2:
                runs, s = [], dense[0]
                for a_, b_ in zip(dense, dense[1:]):
                    if b_ != a_ + 1:
                        runs.append((s, a_)); s = b_
                runs.append((s, dense[-1]))
                lo, hi = max(runs, key=lambda r: r[1] - r[0])
                if hi - lo + 1 >= 2 and max(w, h) > 3.0 * (hi - lo + 1):
                    # the erosion took 3px off each side; the long axis keeps the
                    # component's own extent, the short axis is the measured band
                    # keep both readings: the band is the bar, the box is the bar
                    # plus whatever meets it, and the difference between them is
                    # the evidence that anything does
                    band, box = int(hi - lo + 1) + 6, int(min(w, h)) + 6
                    # where along its length the component stands proud of the
                    # bar. A join has an arrowhead landing at two or more places;
                    # a plain connector that happens to be fused with a node at
                    # one end has exactly one, at the end.
                    thick = (comp.sum(axis=0) if w >= h else comp.sum(axis=1)) \
                        > (hi - lo + 1) + 1
                    lumps, run = 0, False
                    for v in thick:
                        if v and not run:
                            lumps += 1
                        run = bool(v)
                    if w >= h:
                        d = dict(d, y=int(y0) + int(lo) - 3, h=band)
                    else:
                        d = dict(d, x=int(x0) + int(lo) - 3, w=band)
                    bars.append(dict(d, kind="fork", band=band, box=box,
                                     lumps=lumps))
            elif fill > 0.70 and ar > 3:
                bars.append(dict(d, kind="fork"))
    return discs, bars


def dashed_boxes(ink, stroke, min_dashes=8, min_span=0.35):
    """The dashed rounded rectangle that encloses a whole diagram.

    The CPFR diagrams are each one phase of a larger process, and each is drawn
    inside a dashed rounded box carrying the phase name. Nothing was looking for
    it: its dashes are too short to be line-work and too regular to be text, so
    they were dropped, and the box - the largest single thing on the page - was
    missing from every one of those conversions.

    A dash is a small solid mark much longer than it is thick. Where eight or more
    of them share a row (or a column) and together span a third of the page, that
    is a dashed line; four such lines bound a box. The dash and gap lengths are
    measured too, so the rebuild can repeat the same pattern rather than invent
    one."""
    lbl, _ = ndi.label(ink, structure=np.ones((3, 3)))
    thick = max(3.0, 2.5 * stroke)
    rows, cols = {}, {}
    for i, sl in enumerate(ndi.find_objects(lbl), start=1):
        if sl is None:
            continue
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if min(w, h) > thick or not (2.0 * min(w, h) <= max(w, h) <= 14 * thick):
            continue
        if w > h:
            rows.setdefault((sl[0].start + h // 2) // 4, []).append(
                (sl[1].start, sl[1].stop, w, h))
        else:
            cols.setdefault((sl[1].start + w // 2) // 4, []).append(
                (sl[0].start, sl[0].stop, h, w))

    def lines(buckets, span):
        out = []
        for b, ds in buckets.items():
            if len(ds) < min_dashes:
                continue
            lo = min(d[0] for d in ds)
            hi = max(d[1] for d in ds)
            if hi - lo < min_span * span:
                continue
            ds = sorted(ds)
            gaps = [b0 - a1 for (_, a1, _, _), (b0, _, _, _) in zip(ds, ds[1:])]
            out.append(dict(at=b * 4 + 2, lo=lo, hi=hi, n=len(ds),
                            dash=float(np.median([d[2] for d in ds])),
                            weight=float(np.median([d[3] for d in ds])),
                            gap=float(np.median(gaps)) if gaps else 0.0))
        return sorted(out, key=lambda r: r["at"])

    H, W = ink.shape
    hs, vs = lines(rows, W), lines(cols, H)
    if len(hs) < 2 or len(vs) < 2:
        return []
    top, bot, left, right = hs[0], hs[-1], vs[0], vs[-1]
    if bot["at"] - top["at"] < 0.3 * H or right["at"] - left["at"] < 0.3 * W:
        return []
    # the horizontal runs stop short of the corner by the corner radius
    r = max(0, int(round(min(top["lo"] - left["at"], right["at"] - top["hi"]))))
    return [dict(x=int(left["at"]), y=int(top["at"]),
                 w=int(right["at"] - left["at"]), h=int(bot["at"] - top["at"]),
                 rx=r, dash=round(top["dash"], 1), gap=round(top["gap"], 1),
                 weight=round(float(np.median([top["weight"], bot["weight"],
                                               left["weight"], right["weight"]])), 1),
                 dashes=top["n"] + bot["n"] + left["n"] + right["n"])]


def dash_pixels(ink, boxes, stroke):
    """The marks that make up a dashed box, and nothing else.

    Erasing a band along the box's edges instead - which is the obvious thing -
    cuts every connector that crosses it, and in the CPFR diagrams several do:
    the flow leaves a phase, crosses its own boundary and runs on to the next.
    A dash is small; a connector crossing the boundary is not. Take the dashes
    themselves and leave the crossings alone."""
    m = np.zeros_like(ink)
    if not boxes:
        return m
    band = int(max(6, 3 * stroke))
    near_edge = np.zeros_like(ink)
    for d in boxes:
        for yy in (d["y"], d["y"] + d["h"]):
            near_edge[max(0, yy - band):yy + band,
                      max(0, d["x"] - band):d["x"] + d["w"] + band] = True
        for xx in (d["x"], d["x"] + d["w"]):
            near_edge[max(0, d["y"] - band):d["y"] + d["h"] + band,
                      max(0, xx - band):xx + band] = True
        # and the four rounded corners, which lie outside all four of those bands.
        # Left out, their dashes went on to be read as text, and the deck showed
        # "4 7 ? o" curving around the top left corner of every CPFR diagram.
        r = int(d.get("rx") or 0) + band
        for cy in (d["y"], d["y"] + d["h"] - r):
            for cx in (d["x"], d["x"] + d["w"] - r):
                near_edge[max(0, cy - band):cy + r + band,
                          max(0, cx - band):cx + r + band] = True
    lbl, _ = ndi.label(ink & near_edge, structure=np.ones((3, 3)))
    thick = max(3.0, 2.5 * stroke)
    for i, sl in enumerate(ndi.find_objects(lbl), start=1):
        if sl is None:
            continue
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if min(w, h) <= thick and max(w, h) <= 14 * thick:
            m[sl][lbl[sl] == i] = True
    return m


def grey_rules(gray, min_cov=0.45, min_w=3):
    """Dividers drawn in grey rather than black.

    Everything else here works from ink, which is luminance below 128 - and the
    lane divider of CreatingSalesForecast is drawn at 224, invisible at that
    threshold. It was not that the divider failed a test: nothing had ever seen
    it. A black line's own anti-aliased edge is grey too, so a grey rule has to be
    several pixels across with no black core.

    Returns position, thickness and the grey it is drawn in, so the rebuild can
    use the artwork's own tone instead of promoting the line to black."""
    g = gray.astype(np.int16)
    grey = (g >= 140) & (g <= 242)
    black = g < 140
    H, W = g.shape
    out = []
    for axis, span in (("v", W), ("h", H)):
        cov = (grey.sum(axis=0) / float(H)) if axis == "v" else (grey.sum(axis=1) / float(W))
        bcov = (black.sum(axis=0) / float(H)) if axis == "v" else (black.sum(axis=1) / float(W))
        groups, cur = [], []
        for p in np.where(cov >= min_cov)[0]:
            if cur and p - cur[-1] > 3:
                groups.append(cur); cur = []
            cur.append(p)
        if cur:
            groups.append(cur)
        for gr in groups:
            if len(gr) < min_w or not (6 < gr[0] < span - 12):
                continue
            mid = gr[len(gr) // 2]
            if bcov[mid] > 0.12:
                continue                       # a black line with grey edges
            line = g[:, mid][grey[:, mid]] if axis == "v" else g[mid, :][grey[mid, :]]
            out.append(dict(axis=axis, at=int(gr[0]), w=int(len(gr)),
                            level=int(np.median(line)),
                            coverage=round(float(cov[mid]), 2)))
    return out


def find_rules(ink, frac=0.40, partial=None):
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
        def reaches(line, a, b):
            # nearly all of the first (last) stretch, not every pixel of it: the
            # header rule of several transport diagrams starts two pixels short of
            # the frame, and demanding an unbroken run lost the whole rule - and
            # with it the header band, the column titles it separates, and a
            # line right across the page. A node edge has no ink here at all, so
            # the distinction this test makes survives the tolerance.
            seg = line[a:b]
            return seg.size > 0 and seg.mean() >= 0.85

        def widen(g):
            """the whole stroke, not the one column of it that is densest.

            A divider is not always drawn true: ROCD-InitialStocking's wanders
            across fifteen columns, so its best single column carries 44% of the
            page and every column beside it less, and nothing reached the frame at
            either end. Taken together they cover 90% and reach both. Only columns
            beside one already chosen are added, so this widens the candidates
            rather than adding any."""
            a, b = g[0], g[-1]
            while a - 1 >= 0 and profile[a - 1] > span * frac * 0.35:
                a -= 1
            while b + 1 < len(profile) and profile[b + 1] > span * frac * 0.35:
                b += 1
            return a, b

        def stroke_width(a, b):
            """where the rule is and how thick it is drawn, measured across it, so
            that a line that wanders is not recorded as being as wide as its
            wandering nor placed at the middle of where it wandered"""
            sub = (ink[lo:hi, a:b + 1] if axis == "v" else ink[a:b + 1, lo:hi].T)
            runs, starts = [], []
            for row in sub:
                e = np.flatnonzero(np.diff(np.r_[0, row.view(np.int8), 0]))
                if e.size:
                    k = int(np.argmax(e[1::2] - e[0::2]))
                    runs.append(int(e[1::2][k] - e[0::2][k]))
                    starts.append(a + int(e[0::2][k]))
            if not runs:
                return a, b - a + 1
            return (int(round(float(np.median(starts)))),
                    max(1, int(round(float(np.median(runs))))))

        out = []
        for g in groups:
            a, b = widen(g)
            line = (ink[:, a:b + 1].any(axis=1) if axis == "v"
                    else ink[a:b + 1, :].any(axis=0))
            ends = (reaches(line, lo + near, lo + reach),
                    reaches(line, hi - reach, hi - near))
            # A divider that reaches both frames is one on its own. Several lane
            # dividers stop short of one of them - the column rule of the CRP and
            # ROCD diagrams runs from the top frame down to the last object box
            # and no further - and those were lost entirely, which also cuts the
            # object nodes drawn *on* the divider into odd shapes. One end plus
            # ink down more than half the page between the frames is still a
            # divider: no node edge is half the page long.
            if all(ends) or (any(ends) and line[lo:hi].mean() >= 0.5):
                start, w = stroke_width(a, b)
                # two groups can widen onto the same stroke and report it twice,
                # which then draws the divider on top of itself and counts it as a
                # partition boundary twice over
                if out and abs(out[-1][0] - start) <= max(out[-1][1], w):
                    continue
                out.append((int(start), int(w)))
                if partial is not None and not all(ends):
                    partial.add((axis, start))
        return out

    vprof, hprof = ink.sum(axis=0), ink.sum(axis=1)
    vlo, vhi = frame_span(hprof, W)          # vertical rules end on the horizontal frame
    hlo, hhi = frame_span(vprof, H)
    return (scan(vprof, H, "v", vlo, vhi), scan(hprof, W, "h", hlo, hhi))


def main(path, out_json=None):
    ink, bg = load_ink(path)
    H, W = ink.shape
    print("image %dx%d" % (W, H))

    partial_rules = set()
    vr, hr = find_rules(ink, partial=partial_rules)
    greys = grey_rules(np.asarray(bg.convert("L")))
    for gr in greys:
        print("   grey %s rule at %d, %dpx wide, tone %d (covers %.0f%% of the page)"
              % ("column" if gr["axis"] == "v" else "band", gr["at"], gr["w"],
                 gr["level"], 100 * gr["coverage"]))
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
    gh = glyph_height(bg, path=path)
    print("   type measured off the page: a word is %.0fpx tall" % gh
          if gh else "   no legible type found; enclosure falls back to relative area")
    # The smallest thing that can be a node is not a fixed number of pixels: this
    # artwork runs from 26px type to 84px type, and at the small end an activity
    # final's ring encloses about 1000px of white - under the flat 1200 that was
    # asked for, so three of them in each GoodsItemPassport diagram lost their
    # ring and were drawn as plain initial discs. Scale the floor with the type,
    # and never above the flat figure, so nothing that used to be found is lost.
    min_area = min(MIN_NODE_AREA, max(200, int(0.6 * gh * gh))) if gh else MIN_NODE_AREA
    regs = drop_phantoms(ink, enclosed_regions(ink, min_area, 0.7 * gh if gh else 0.0),
                         cells, flags=uncertain,
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
    discs, bars = solid_blobs(ink, W, H, gh)
    # and the start nodes whose connector keeps them from looking round
    have = {(d["x"] // 20, d["y"] // 20) for d in discs}
    for d in disc_blobs(ink, gh, W, H):
        if not any(abs(d["x"] - e["x"]) < 0.6 * d["w"] and abs(d["y"] - e["y"]) < 0.6 * d["h"]
                   for e in discs):
            discs.append(d)
    # A fork bar is drawn much heavier than a line - across the 78 diagrams every
    # real one is at least four times the diagram's own stroke, 18px and up
    # against strokes of 3 to 6. What is merely as thick as a stroke is a stroke:
    # the top edge of a rounded box drawn at 8px survives the erosion that is
    # meant to make line-work vanish, and 27 such "bars" were found, every one of
    # them with no connector attached because there was no node there to connect.
    line_w = float(np.median(box_strokes)) if box_strokes else 0.0
    if line_w:
        # ...or, where the artwork draws its bars no heavier than its lines, by
        # what meets them. UBL-1.0-ProcurementProcess joins two flows into one
        # twice, and both bars are 8-10px against a 7px line, so the weight test
        # alone discarded them. The erosion that finds a bar keeps the arrowheads
        # that land on it, so its component stands two to four times taller than
        # the bar itself; a stroke that merely survived the erosion is exactly as
        # thick as its own band - the 312px connector on the same diagram measures
        # 8 and 8. That difference is the meeting, measured.
        real = [b for b in bars
                if min(b["w"], b["h"]) >= 2 * line_w
                or (b.get("box", 0) >= 2 * b.get("band", 10 ** 6)
                    and b.get("lumps", 0) >= 2)]
        for b in bars:
            if b not in real:
                print("   (dropped x=%-5d y=%-5d %4dx%-4d  only %.0fpx across against a"
                      " %.0fpx line - a stroke, not a fork bar)"
                      % (b["x"], b["y"], b["w"], b["h"], min(b["w"], b["h"]), line_w))
        bars = real
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
        # ...for a rhombus as well. The lines were never measured there, so every
        # decision's label was drawn centred in its box and nothing said where the
        # artwork actually sets it; the interior mask handles a rhombus as readily
        # as a rectangle, because it is the enclosed white area whatever the shape.
        boxes = label_lines(ink, n, max(4, n.get("stroke", 4)) + 2) \
            if n["kind"] in ("action", "object", "note", "decision") else []
        if n["kind"] == "decision":
            # A rhombus writes its label across its middle, with its two slanted
            # edges a few pixels from the glyphs. Eroding the interior does not
            # clear a diagonal stroke, and insetting a rectangle cannot either -
            # every rectangle that holds the text crosses the border somewhere.
            # Painting out everything outside the interior does clear it, whatever
            # the slant; the middle-half crop below is what is left when no
            # interior was measured.
            t = ocr_inside(bg, ink, n)
            n["label"] = ocr(bg, n["x"] + n["w"] // 4, n["y"] + n["h"] // 4,
                             n["w"] // 2, n["h"] // 2) if t is None else t
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
            # ...but a counter is a hole inside a letter, and the ink around it
            # stops at its own edge. A node this small is one UBL draws on the
            # flow - the four unlabelled decision nodes on UBL-1.0-Procurement-
            # Process are 29px against 39px type - and it was kept above only
            # because connectors run through it on three sides, which is what a
            # letter can never do.
            # ...nor is an end event, which is small on every diagram that has
            # one and carries no label by definition. What marks it out from a
            # counter is ink at its own centre - the filled disc inside the ring -
            # and that is what put it in this kind. UBL-1.0-ProcurementProcess
            # ends on a 23px activity final against 39px type, and dropping it
            # left the only end event on the page missing.
            if (not n.get("label") and n.get("mask") is not None
                    and not n.get("keptOnOutline")
                    and n["kind"] != "final"
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

    # One corner radius per kind of box, because that is how the artwork draws
    # them. The radius is read off each box separately, and where a connector
    # lands on the top edge or the first row of ink is a stray pixel the reading
    # runs away: on UBL-1.0-ProcurementProcess three of eighteen action boxes
    # measured 104, 173 and 175 against a median of 29, the SVG clamped each to
    # half the box width, and three of the stadiums came out as ellipses standing
    # among their square-shouldered neighbours.
    #
    # Two corrections, in order. A corner radius cannot exceed half the shorter
    # side - that is geometry, not style, and it alone catches all three. Then the
    # style: UBL gives every box of one kind the same corners, so a box whose own
    # reading is more than half again the median for its kind is taking the
    # median. Nothing moves where the readings already agree.
    for kind in ("action", "object", "note"):
        same = [n for n in nodes if n["kind"] == kind and n.get("rx") is not None]
        if len(same) < 3:
            continue
        broke = {}
        for n in same:
            # the region is the interior, so the box the artwork drew is a
            # stroke wider and taller than it - measure the limit against that,
            # or every fully rounded end reads a few pixels too tight
            lim = max(1.0, (min(n["w"], n["h"]) + (n.get("stroke") or 0)) / 2.0)
            for key in ("rx", "ry"):
                if n[key] > lim:
                    broke.setdefault(key, []).append(n)
                    n[key] = lim
        # A reading that had to be clamped is known to be wrong, not merely
        # different, so give it the diagram's own answer rather than the clamp.
        # Only those: where two boxes of a kind simply read a few pixels apart the
        # artwork may well have drawn them that way, and substituting the median
        # there made three boxes on Fulfilment-ReceiptAdvice rounder than the
        # original and cost more ink than it saved.
        for key, victims in broke.items():
            rest = [n[key] for n in same if n not in victims]
            if not rest:
                continue
            med = float(np.median(rest))
            for n in victims:
                print("   corner radius %s on %r could not be read (it came back"
                      " larger than the box) - taking the %.0f the rest of its kind"
                      " measures" % (key, (n.get("label") or "")[:28], med))
                n[key] = med

    # Bold or regular, measured rather than assumed. Every action label was drawn
    # bold, and on Tender-QualificationApplication the artwork sets them regular:
    # bold Helvetica at the measured size is wider than the box the artwork drew
    # around its regular type, so six labels ran out of both ends of their boxes.
    #
    # Weight is stem width. Take the length of every run of ink across a label's
    # own line band, and the middle of that distribution is how thick the strokes
    # are; against the diagram's type size it comes out at 0.08 for regular and
    # 0.13 to 0.18 for bold, with nothing in between anywhere in the 78. A short
    # label gives too few runs to be sure on its own, so it falls back to the
    # diagram's own reading for that kind of node.
    if font_px > 0:
        def stem_runs(b):
            sub = ink[b["y"]:b["y"] + b["h"], b["x"]:b["x"] + b["w"]]
            out = []
            for row in sub:
                idx = np.flatnonzero(np.diff(np.r_[0, row.view(np.int8), 0]))
                out.extend(idx[1::2] - idx[0::2])
            return out
        per_kind = {}
        for n in nodes:
            runs = []
            for l in (n.get("labelLines") or []):
                runs.extend(stem_runs(l))
            n["_stemRuns"] = runs
            per_kind.setdefault(n["kind"], []).extend(runs)
        kind_stem = {k: float(np.median(v)) / font_px
                     for k, v in per_kind.items() if len(v) >= 20}
        for n in nodes:
            runs = n.pop("_stemRuns", [])
            stem = (float(np.median(runs)) / font_px if len(runs) >= 20
                    else kind_stem.get(n["kind"]))
            if stem is not None:
                n["stem"] = round(stem, 3)
                n["bold"] = stem >= 0.11

    # An activity box, an object and a note are all there to carry words. White
    # trapped inside a loop-back connector is not, and it survives the phantom
    # tests: the corner a diagonal cuts off it reads as a note's folded corner,
    # which skips those tests altogether. VMI-PermanentReplenishment came out with
    # a 566x800 "action" over the loop below its decision, drawn as a great empty
    # shape in the middle of the page. Nothing was read from any of these seven,
    # while all 747 other boxes carry a label, so: no words and line-work running
    # past two or more sides means this is the space between things, not a thing.
    keep = []
    for n in nodes:
        if (n["kind"] in ("action", "object", "note") and not n.get("label", "").strip()
                and sides_continue(ink, n) >= 2):
            print("   (dropped x=%-5d y=%-5d %4dx%-4d  no text, and line-work runs past"
                  " %d of its sides - whitespace between shapes, not a %s)"
                  % (n["x"], n["y"], n["w"], n["h"], sides_continue(ink, n), n["kind"]))
            uncertain.append(dict(kind="empty-box", x=n["x"], y=n["y"], w=n["w"], h=n["h"],
                                  reason="a %s carrying no text, with line-work passing"
                                         " its sides" % n["kind"],
                                  check="confirm nothing is drawn here in the original"))
            continue
        keep.append(n)
    nodes = keep

    # A divider never runs through an activity or a decision. It may be straddled
    # by a document box - UBL draws those on the divider on purpose - but a
    # vertical that crosses a rounded box or a diamond is a connector that happens
    # to line up, not a rule. ExceptionHandling has one: the flow from "Receive
    # Sales Forecast & Wait for Exception Notification" down to its decision, with
    # the No branch continuing below, covers two thirds of the page in one column
    # and was read as a lane divider - which then erased that whole column from
    # the connector search, so the decision lost its connectors and kept only the
    # stray marks around them.
    def crosses_a_shape(at, w, axis):
        """the shape a rule would have to cut through, if any.

        A box drawn *on* a divider is the house style, so crossing one is not by
        itself disqualifying - what settles it is whether the line carries on past
        the box on both sides. A divider does; a connector leaving that box does
        not, because the box is where it starts."""
        mid = int(at + w / 2.0)
        line = (ink[:, max(0, mid - 1):mid + 2].any(axis=1) if axis == "v"
                else ink[max(0, mid - 1):mid + 2, :].any(axis=0))
        for n in nodes:
            if n["kind"] == "object":
                continue
            lo, hi = ((n["x"], n["x"] + n["w"]) if axis == "v"
                      else (n["y"], n["y"] + n["h"]))
            if not (lo + 4 < mid < hi - 4):
                continue
            a0, a1 = ((n["y"], n["y"] + n["h"]) if axis == "v"
                      else (n["x"], n["x"] + n["w"]))
            look = max(60, 4 * (line_w or 4))
            before = line[max(0, a0 - look):max(0, a0 - 2)]
            after = line[min(len(line), a1 + 2):min(len(line), a1 + look)]
            near_before = before.size and before.mean() > 0.3
            near_after = after.size and after.mean() > 0.3
            if near_before and near_after:
                continue                   # the line runs on past the box: a divider
            if not (near_before or near_after):
                continue                   # the line does not reach this box at all
            return n                       # it stops here, so this box is its source
        return None

    def keep_rules(rules, axis, span):
        out = []
        for at, w in rules:
            # A rule that runs frame to frame is a divider whatever it passes: the
            # swimlane grids draw tall boxes across their band lines on purpose.
            # Only the ones that reach a single frame have to answer for what they
            # cross, and those are the ones a connector can imitate.
            edge = at <= max(3, span * 0.015) or at + w >= span - max(3, span * 0.015)
            hit = (None if edge or (axis, at) not in partial_rules
                   else crosses_a_shape(at, w, axis))
            if hit is None:
                out.append((at, w))
            else:
                print("   (dropped %s rule at %d: it starts at %s, a %s, and does not"
                      " run on past it - a connector, not a divider)"
                      % (axis, at, hit["id"], hit["kind"]))
                uncertain.append(dict(kind="rule-through-shape",
                                      x=at if axis == "v" else 0,
                                      y=0 if axis == "v" else at, w=w, h=w,
                                      reason="a rule reaching one frame only, stopping at %s"
                                             % hit["id"],
                                      check="confirm there is no lane divider here"))
        return out

    vr, hr = keep_rules(vr, "v", W), keep_rules(hr, "h", H)
    inner_v = [r for r in vr if 6 < r[0] < W - 12]
    inner_h = [r for r in hr if 6 < r[0] < H - 12]
    vb = [0] + [x + w / 2 for x, w in inner_v] + [W]
    hb = [0] + [y + h / 2 for y, h in inner_h] + [H]
    strip = len(vb) > 2 and (vb[1] - vb[0]) < W * 0.04
    header = len(hb) > 2 and (hb[1] - hb[0]) < H * 0.04

    # the dashed box that encloses a whole CPFR phase: found before the connector
    # search, so its dashes are not mistaken for line-work or for words
    dboxes = dashed_boxes(ink, line_w or 4.0)
    for d in dboxes:
        print("   dashed enclosure x=%d y=%d %dx%d  r=%d  dash %.0f/%.0f over %d marks"
              % (d["x"], d["y"], d["w"], d["h"], d["rx"], d["dash"], d["gap"], d["dashes"]))

    mask = ink.copy()
    erased = np.zeros_like(ink)
    mask &= ~dash_pixels(ink, dboxes, line_w or 4.0)
    # the nodes as solid blocks, for measuring an arrowhead on the page itself
    # without a box's own outline joining in
    node_fill = np.zeros_like(ink)
    for n in nodes:
        node_fill[max(0, n["y"] - 2):n["y"] + n["h"] + 3,
                  max(0, n["x"] - 2):n["x"] + n["w"] + 3] = True
    for n in nodes:
        m = 14
        mask[max(0, n["y"] - m):n["y"] + n["h"] + m, max(0, n["x"] - m):n["x"] + n["w"] + m] = False
        erased[max(0, n["y"] - m):n["y"] + n["h"] + m, max(0, n["x"] - m):n["x"] + n["w"] + m] = True
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

    lbl, ncomp = ndi.label(mask, structure=np.ones((3, 3)))
    slices = ndi.find_objects(lbl)

    # A guard label is set ON its connector, breaking the connector into pieces
    # that each touch only one node, so the edge was dropped. Rejoin the pieces -
    # as components, not as pixels, so the label itself stays a separate component
    # and is still read as text.
    parent = list(range(ncomp + 1))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    spans, joined_px = {}, []              # the pixels of the spans themselves
    chain_dash = {}                        # each dashed chain's own dash/gap
    if font_px > 0:
        g = max(30, int(round(1.8 * font_px)))
        run = max(20, int(round(0.5 * font_px)))
        wide = max(8, int(round(0.3 * font_px)))
        joins = (bridge_runs(mask, erased, g, run, wide, 0)
                 + bridge_runs(mask, erased, g, run, wide, 1))
        made = 0
        for axis, c, a, b in joins:
            (r1, c1), (r2, c2) = (((a - 1, c), (b, c)) if axis == 0
                                  else ((c, a - 1), (c, b)))
            i, j = int(lbl[r1, c1]), int(lbl[r2, c2])
            if not (i and j):
                continue
            span = ((np.arange(a, b), np.full(b - a, c)) if axis == 0
                    else (np.full(b - a, c), np.arange(a, b)))
            if root(i) != root(j):
                made += 1
            parent[root(i)] = root(j)
            joined_px.append((j, span))
        for j, span in joined_px:          # after every union, so the root is final
            spans.setdefault(root(j), []).append(span)
        if made:
            print("   rejoined %d line break(s) of up to %dpx, where a label sits"
                  " on the line" % (made, g))

        # A dashed flow is not one component with gaps in it: it is a row of
        # separate marks, not one of which touches two nodes, so the whole line
        # was discarded and its dashes were read as text - the dashed diagonal on
        # FulfilmentDespatchAdvice came out as "\\\\\ Z aN --_ L\" drawn on the
        # page. Chain them instead. A dash is a short straight mark; the next dash
        # of the same line lies ahead of it along its own direction, parallel to
        # it, within a few dash lengths. Three in a row is a dashed line, two is a
        # coincidence.
        marks = {}
        for i in range(1, ncomp + 1):
            sl = slices[i - 1]
            if sl is None:
                continue
            hh, ww = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
            if not (0.2 * font_px <= max(hh, ww) <= 1.5 * font_px):
                continue
            yy, xx = np.where(lbl[sl] == i)
            if yy.size < 6:
                continue
            yy = yy + sl[0].start
            xx = xx + sl[1].start
            cx, cy = float(xx.mean()), float(yy.mean())
            cov = np.cov(np.vstack([xx - cx, yy - cy]))
            ev, evec = np.linalg.eigh(cov)
            # A dash only has to be elongated enough for its own direction to be
            # readable, because what identifies a dashed line is the chain test
            # below - three marks ahead of one another along that direction,
            # parallel, evenly spaced. 3:1 was a guess and it is wrong for the
            # oldest artwork: UBL-1.0-ProcurementProcess draws every object flow
            # in 17x7 dashes, 2.4:1, so not one of its ~30 dashed connectors was
            # ever considered and their dashes were read as text instead. The
            # variance ratio of a LxW rectangle is (L/W)^2, so this is 2:1 - the
            # point at which the principal axis of a rectangle is still determined
            # to within about 10 degrees.
            if ev[0] < 0.05 or ev[1] < 4.0 * ev[0]:      # not 2:1 or better
                continue
            marks[i] = (cx, cy, float(evec[0, 1]), float(evec[1, 1]),
                        3.5 * math.sqrt(max(float(ev[1]), 1e-6)))

        link = {}
        for i, (cx, cy, ux, uy, ln) in marks.items():
            # the nearest mark each way along its own direction, not just the
            # nearest of the two: linking one way only breaks a line of six
            # dashes into two chains of three
            best = {1: (None, 1e18), -1: (None, 1e18)}
            for j2, (px, py, vx2, vy2, ln2) in marks.items():
                if j2 == i:
                    continue
                dx, dy = px - cx, py - cy
                d = math.hypot(dx, dy)
                if d < 1 or d > 3.0 * max(ln, ln2):
                    continue
                along = dx * ux + dy * uy
                if abs(along) < 0.9 * d:                  # not ahead along its axis
                    continue
                if abs(ux * vx2 + uy * vy2) < 0.9:        # not parallel to it
                    continue
                side = 1 if along > 0 else -1
                if d < best[side][1]:
                    best[side] = (j2, d)
            for j2, _ in best.values():
                if j2 is not None:
                    link.setdefault(i, set()).add(j2)
                    link.setdefault(j2, set()).add(i)

        # A label set on a *diagonal* connector breaks it in two, and the rejoin
        # above only closes gaps that run straight up or across, so the flow into
        # the join bar on BillingwithDebitNote arrived as an arrowhead, a stub and
        # a tail, and none of them touched two nodes. Join collinear pieces at any
        # angle: same line, same slant, facing each other, with a gap no wider
        # than a label and no node standing in it.
        long_segs = {}
        for i in range(1, ncomp + 1):
            sl = slices[i - 1]
            if sl is None:
                continue
            yy, xx = np.where(lbl[sl] == i)
            if yy.size < 40:
                continue
            yy = yy + sl[0].start
            xx = xx + sl[1].start
            cx, cy = float(xx.mean()), float(yy.mean())
            cov = np.cov(np.vstack([xx - cx, yy - cy]))
            ev, evec = np.linalg.eigh(cov)
            if ev[0] < 0.05 or ev[1] < 5.0 * ev[0]:
                continue
            ux, uy = float(evec[0, 1]), float(evec[1, 1])
            t = (xx - cx) * ux + (yy - cy) * uy
            half = float(t.max() - t.min()) / 2.0
            if 2.0 * half < 0.4 * font_px:
                continue
            # a piece of a broken line, and whether it is unmistakably a line: the
            # arrowhead at the end of one is a wedge, not a line, but its axis
            # still points along the flow, so it may be joined *to* a line and
            # never to another wedge
            long_segs[i] = (cx, cy, ux, uy, half,
                            ev[1] >= 36.0 * ev[0] and 2.0 * half >= 0.8 * font_px)

        # ...and the erasure itself widens every gap next to a node by its margin
        # at each end, so a break the erasure made is up to 2m wider than the one
        # the artwork drew
        gapmax = 2.5 * font_px + 2 * 14
        for i, (cx, cy, ux, uy, ln, line_i) in long_segs.items():
            for j, (px2, py2, vx2, vy2, ln2, line_j) in long_segs.items():
                if j <= i or abs(ux * vx2 + uy * vy2) < 0.99:  # not the same slant
                    continue
                if not (line_i or line_j):
                    continue
                along = abs((px2 - cx) * ux + (py2 - cy) * uy)
                gap = along - ln - ln2
                if not (0 < gap <= gapmax):
                    continue
                sgn = 1.0 if ((px2 - cx) * ux + (py2 - cy) * uy) > 0 else -1.0
                a_end = (cx + sgn * ux * ln, cy + sgn * uy * ln)
                b_end = (px2 - sgn * ux * ln2, py2 - sgn * uy * ln2)
                # the same line, judged where it matters: the two ends that face
                # each other lie along both pieces' own direction. Comparing the
                # pieces' centres instead is too strict on a short piece, whose
                # centre is pulled sideways by the arrowhead that sits on it -
                # 8px out of true on BillingwithDebitNote, against a 5px bound.
                gx, gy2 = b_end[0] - a_end[0], b_end[1] - a_end[1]
                gL = math.hypot(gx, gy2) or 1.0
                if (abs(gx * ux + gy2 * uy) / gL < 0.985
                        or abs(gx * vx2 + gy2 * vy2) / gL < 0.985):
                    continue
                n2 = int(max(abs(b_end[0] - a_end[0]), abs(b_end[1] - a_end[1]))) + 1
                ry = np.rint(np.linspace(a_end[1], b_end[1], n2)).astype(int)
                rx = np.rint(np.linspace(a_end[0], b_end[0], n2)).astype(int)
                # A node stands in the gap only if the line would have to cross
                # its box. Against the erased mask - the box plus a 14px margin -
                # a line that merely clips a corner counted as blocked: the flow
                # from the decision node to "add detail" on UBL-1.0-Procurement-
                # Process passes 14px outside "accept order" and was cut in two,
                # each half then ending on that box, one of them backwards. It
                # crosses 5px of box; a flow that really runs through a node
                # crosses the whole of it.
                run = int(node_fill[np.clip(ry, 0, H - 1), np.clip(rx, 0, W - 1)].sum())
                if run > max(20.0, 0.5 * font_px):
                    continue                                   # a node stands in the gap
                if root(i) != root(j):
                    print("   rejoined a %.0fpx break in a line at %.0f degrees,"
                          " where a label sits on it"
                          % (gap, math.degrees(math.atan2(uy, ux)) % 180))
                parent[root(i)] = root(j)
                spans.setdefault(root(j), []).append((ry, rx))

        def build_chains():
            seen_m, out_c = set(), []
            for i in link:
                if i in seen_m:
                    continue
                stack, chain = [i], []
                while stack:
                    k = stack.pop()
                    if k in seen_m:
                        continue
                    seen_m.add(k)
                    chain.append(k)
                    stack += [m for m in link.get(k, ()) if m not in seen_m]
                if len(chain) >= 3:
                    out_c.append(chain)
                elif len(chain) == 2:
                    pairs2.append(chain)
            return out_c

        # Three marks in a row are a dashed line and two are a coincidence - but
        # not when the two of them, carried one pitch further at each end, arrive
        # at two different nodes. "advise receipt" writes ReceiptAdvice on
        # UBL-1.0-ProcurementProcess over a span so short that only two of its
        # dashes stand alone: the third is swallowed by the arrowhead on the box
        # corner. Both ends landing on a node is what a coincidence does not do.
        def reaches(px, py):
            best = None
            for nd in nodes:
                dx = max(nd["x"] - px, 0, px - (nd["x"] + nd["w"]))
                dy = max(nd["y"] - py, 0, py - (nd["y"] + nd["h"]))
                if math.hypot(dx, dy) <= 34:
                    if best is None or math.hypot(dx, dy) < best[1]:
                        best = (nd["id"], math.hypot(dx, dy))
            return best[0] if best else None

        pairs2 = []
        chains = build_chains()
        # One dashed line can come back as two chains, because where another line
        # crosses it the dash under the crossing belongs to that line's component
        # and is not a mark at all. The gap is then two pitches wide, past what a
        # mark is allowed to reach, and the flow out of ReceiptAdvice on
        # UBL-1.0-ProcurementProcess stopped dead in mid-lane. Close it between
        # *chains* rather than by letting every mark look further: a chain has
        # already been established as a dashed line and knows its own pitch, so
        # the reach is measured rather than guessed, and two stray marks can
        # never find each other this way. Letting marks reach further instead
        # cost two diagrams their line-work and ate the "r" of "Seller".
        def ends_of(chain):
            pts = [(marks[k][0], marks[k][1], k) for k in chain]
            i = max(range(len(pts)), key=lambda a: (pts[a][0], pts[a][1]))
            j = min(range(len(pts)), key=lambda a: (pts[a][0], pts[a][1]))
            steps = sorted(math.hypot(pts[a][0] - pts[b][0], pts[a][1] - pts[b][1])
                           for a in range(len(pts)) for b in range(a + 1, len(pts)))
            pitch = steps[0] if steps else 0.0
            return pts[i], pts[j], pitch

        merged = True
        while merged:
            merged = False
            info = [ends_of(ch) for ch in chains]
            for ci in range(len(chains)):
                for cj in range(ci + 1, len(chains)):
                    if merged:
                        break
                    for pa in info[ci][:2]:
                        for pb in info[cj][:2]:
                            gap = math.hypot(pb[0] - pa[0], pb[1] - pa[1])
                            lim = 2.6 * max(info[ci][2], info[cj][2])
                            if not (0 < gap <= lim):
                                continue
                            ua = (marks[pa[2]][2], marks[pa[2]][3])
                            ub = (marks[pb[2]][2], marks[pb[2]][3])
                            gx, gy2 = (pb[0] - pa[0]) / gap, (pb[1] - pa[1]) / gap
                            if (abs(ua[0] * ub[0] + ua[1] * ub[1]) < 0.97
                                    or abs(gx * ua[0] + gy2 * ua[1]) < 0.97):
                                continue
                            link.setdefault(pa[2], set()).add(pb[2])
                            link.setdefault(pb[2], set()).add(pa[2])
                            print("   closed a %.0fpx break between two runs of dashes"
                                  % gap)
                            merged = True
                            break
                        if merged:
                            break
            if merged:
                chains = build_chains()

        # ...and only now, with every run of dashes as long as it is going to get,
        # look at the runs of two.
        for pr in pairs2:
            if any(pr[0] in ch for ch in chains):
                continue
            (ax, ay), (bx2, by2) = marks[pr[0]][:2], marks[pr[1]][:2]
            d0 = math.hypot(bx2 - ax, by2 - ay)
            if d0 < 1:
                continue
            # ...and the two of them have to be the same mark twice, which is
            # what the dashes of one line are and what two letters are not. The
            # "[" and "]" of a "[no action]" guard on SelfBilling-with-CreditNote
            # sit between two nodes and pass every other test here; they measure
            # 39 and 26 long, against 16.6 and 16.0 for the pair that really is a
            # dashed flow.
            la, lb = marks[pr[0]][4], marks[pr[1]][4]
            if max(la, lb) > 1.25 * max(min(la, lb), 1e-6):
                continue
            ux, uy = (bx2 - ax) / d0, (by2 - ay) / d0
            na = reaches(ax - ux * d0, ay - uy * d0)
            nb = reaches(bx2 + ux * d0, by2 + uy * d0)
            if na and nb and na != nb:
                print("   two dashes between %s and %s, carried a dash further at"
                      " each end, reach both - taking them as a dashed flow"
                      % (na, nb))
                chains.append(pr)

        for chain in chains:
            pts = sorted((marks[k][0], marks[k][1]) for k in chain)
            for k in chain[1:]:
                parent[root(chain[0])] = root(k)
            rr = root(chain[0])
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                n2 = int(max(abs(x2 - x1), abs(y2 - y1))) + 1
                spans.setdefault(rr, []).append(
                    (np.rint(np.linspace(y1, y2, n2)).astype(int),
                     np.rint(np.linspace(x1, x2, n2)).astype(int)))
            # A dashed line stops a gap short of the node at each end, so the
            # chain of its dashes ends short too and the flow reads as running
            # between nothing: "place order" to "Order" on UBL-1.0-Procurement-
            # Process leaves 36px and 57px of white against a 34px reach, and the
            # five dashes between them were dropped and then read as text. The
            # line does reach; carry the chain one pitch further at each end,
            # which is its own measurement of how far the drawing skips.
            if len(pts) >= 2:
                steps = [math.hypot(x2 - x1, y2 - y1)
                         for (x1, y1), (x2, y2) in zip(pts, pts[1:])]
                pitch = float(np.median(steps))
                for (xa, ya), (xb, yb) in ((pts[1], pts[0]), (pts[-2], pts[-1])):
                    d = math.hypot(xb - xa, yb - ya) or 1.0
                    # ...only where it falls short. A chain that already ends on a
                    # node needs no help, and carrying it past the node moved the
                    # point the arrowhead is measured at: two dashed flows on
                    # Fulfilment-ReceiptAdvice came back pointing up the page.
                    #
                    # "Already reaches" has to mean the same thing here as it does
                    # where a connector's ends are matched to nodes, which is 34px
                    # from the node's own box. Measured against the erased mask
                    # instead - the box and a 14px margin - a chain 44px short of
                    # "place order" counted as arriving, was left where it was,
                    # and the flow from it to Order was lost.
                    r = 34
                    yy0, yy1 = int(max(0, yb - r)), int(min(H, yb + r + 1))
                    xx0, xx1 = int(max(0, xb - r)), int(min(W, xb + r + 1))
                    sub = node_fill[yy0:yy1, xx0:xx1]
                    gy, gx = np.ogrid[yy0:yy1, xx0:xx1]
                    if sub[(gy - yb) ** 2 + (gx - xb) ** 2 <= r * r].any():
                        continue
                    # one pitch, or two where the end dash itself is missing -
                    # the lane divider swallows it on the flow out of
                    # ReceiptAdvice, which then stopped 94px short of the box it
                    # points at. Step a pitch at a time and stop as soon as a node
                    # is within reach, so the line is never carried past one.
                    ux, uy = (xb - xa) / d, (yb - ya) / d
                    ex, ey = xb + ux * pitch, yb + uy * pitch
                    n2 = int(max(abs(ex - xb), abs(ey - yb))) + 1
                    yy0, yy1 = int(max(0, ey - r)), int(min(H, ey + r + 1))
                    xx0, xx1 = int(max(0, ex - r)), int(min(W, ex + r + 1))
                    sub = node_fill[yy0:yy1, xx0:xx1]
                    gy, gx = np.ogrid[yy0:yy1, xx0:xx1]
                    reached = sub[(gy - ey) ** 2 + (gx - ex) ** 2 <= r * r].any()
                    # a second pitch, but only where a partition rule lies in the
                    # way - that is a dash the drawing really has lost, and it is
                    # the reason the flow out of ReceiptAdvice stopped 94px short
                    # of the box it points at. Taking the second step everywhere
                    # carried nine other diagrams' dashed lines past their own ends.
                    if not reached:
                        x2, y2 = ex + ux * pitch, ey + uy * pitch
                        lo_x, hi_x = sorted((xb, x2)); lo_y, hi_y = sorted((yb, y2))
                        crossed = (any(lo_x <= x + w / 2.0 <= hi_x for x, w in vr)
                                   or any(lo_y <= y + h / 2.0 <= hi_y for y, h in hr))
                        if crossed:
                            ex, ey = x2, y2
                            n2 = int(max(abs(ex - xb), abs(ey - yb))) + 1
                    spans.setdefault(rr, []).append(
                        (np.rint(np.linspace(yb, ey, n2)).astype(int),
                         np.rint(np.linspace(xb, ex, n2)).astype(int)))
            # the chain knows its own pattern - it is made of the dashes. Reading
            # it back off the page later cannot always find it: a long dashed flow
            # is crossed by other lines that fill its gaps, and four flows on
            # UBL-1.0-ProcurementProcess were drawn solid into a document because
            # of it. The dash is the mark, the gap is what is left of the pitch.
            lens = sorted(marks[k][4] for k in chain)
            dl = float(lens[len(lens) // 2])
            if len(pts) >= 2:
                st2 = [math.hypot(x2 - x1, y2 - y1)
                       for (x1, y1), (x2, y2) in zip(pts, pts[1:])]
                pt = float(np.median(st2))
                if pt > dl > 0:
                    # ...and where along the line a dash actually begins. A dash
                    # pattern in the right proportions but the wrong phase puts
                    # every drawn dash over one of the original's gaps, which
                    # costs more ink than drawing the line solid did.
                    chain_dash[rr] = (round(dl, 1), round(pt - dl, 1),
                                      pts[0][0], pts[0][1])
            print("   chained %d dashes into one dashed flow" % len(chain))

    members = {}
    for i in range(1, ncomp + 1):
        if slices[i - 1] is not None:
            members.setdefault(root(i), []).append(i)

    edges, textbits, unexplained, open_ends = [], [], [], []
    cross_stubs = []

    def touching(xs, ys, T=34):
        """the nodes a piece of line-work runs to - notes excepted.

        A note is an annotation, never a step in the flow. IMFM sets three of them
        on lines that run the width of the page, and counting them as nodes turned
        one straight flow into two sloping ones meeting at the note's middle, each
        with an arrowhead of its own."""
        return [n for n in nodes
                if n["kind"] != "note"
                and (((xs >= n["x"] - T) & (xs <= n["x"] + n["w"] + T) &
                      (ys >= n["y"] - T) & (ys <= n["y"] + n["h"] + T)).sum() > 3)]

    def split_crossing(xs, ys, touch):
        """Two connectors that cross are one component, and one component is one
        connector - so the pair came out as a single edge and the other was simply
        gone. On BillingwithDebitNote that lost the flow from "Reconcile Charges"
        to "Raise Debit Note" entirely, because the flow out of the join bar
        crosses it.

        A crossing is not a junction, though, and the difference is visible: the
        straight line between two contacts of a real connector lies on ink for its
        whole length, and between two contacts that are merely both on this
        component it does not. Take every pair that does, drop any that runs
        through a third contact on its way, and give each its own share of the
        ink. Returns a list of pixel sets, or None to leave the component alone."""
        pts = []
        for nd in touch:
            cx, cy = nd["x"] + nd["w"] / 2.0, nd["y"] + nd["h"] / 2.0
            k = int(np.argmin((xs - cx) ** 2 + (ys - cy) ** 2))
            pts.append((int(xs[k]), int(ys[k])))
        # A node the line runs *past* is not one of its ends. The flow from the
        # decision node to "add detail" on UBL-1.0-ProcurementProcess clears the
        # corner of "accept order" by 14px, and counting that as a contact split
        # one arrow into two - one of them pointing backwards - and did the same
        # on the left with "change order" and again with the dashed flow from
        # "cancel order" to OrderCancellation. The difference is in the ink: at
        # the end of a line it runs away in one direction only, and where the line
        # merely passes it runs both ways.
        def runs_past(p):
            r = max(12.0, 0.6 * font_px)
            d2 = (xs - p[0]) ** 2 + (ys - p[1]) ** 2
            sel = np.flatnonzero((d2 > (0.35 * r) ** 2) & (d2 <= r * r))
            if sel.size < 6:
                return False
            if sel.size > 400:
                sel = sel[:: int(sel.size // 400) + 1]
            vx, vy = xs[sel] - p[0], ys[sel] - p[1]
            L = np.hypot(vx, vy)
            vx, vy = vx / L, vy / L
            return bool((np.outer(vx, vx) + np.outer(vy, vy)).min() < -0.9)

        keep = [k for k, p in enumerate(pts) if not runs_past(p)]
        if len(keep) >= 2:
            pts = [pts[k] for k in keep]
            touch = [touch[k] for k in keep]
        if len(pts) < 3:
            return None
        tol = max(6.0, 0.15 * font_px)
        x0, y0 = int(xs.min()), int(ys.min())
        w = int(xs.max()) - x0 + 1
        h = int(ys.max()) - y0 + 1
        m = np.zeros((h, w), bool)
        m[ys - y0, xs - x0] = True
        near = ndi.maximum_filter(m, size=int(2 * tol) + 1)

        def seg(p, q):
            n = int(max(abs(q[0] - p[0]), abs(q[1] - p[1])))
            xi = np.rint(np.linspace(p[0], q[0], max(n, 2))).astype(int) - x0
            yi = np.rint(np.linspace(p[1], q[1], max(n, 2))).astype(int) - y0
            return n, near[np.clip(yi, 0, h - 1), np.clip(xi, 0, w - 1)]

        def off(p, q, r):
            """how far r is off the segment p-q, and whether it is between them"""
            dx, dy = q[0] - p[0], q[1] - p[1]
            L = math.hypot(dx, dy) or 1.0
            t = ((r[0] - p[0]) * dx + (r[1] - p[1]) * dy) / L
            u = abs(-(r[0] - p[0]) * dy + (r[1] - p[1]) * dx) / L
            return u, (0.1 * L < t < 0.9 * L)

        pairs = []
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                n, ok = seg(pts[i], pts[j])
                if n < 10 or float(ok.mean()) < 0.92:
                    continue
                if any(off(pts[i], pts[j], pts[k])[0] <= tol
                       and off(pts[i], pts[j], pts[k])[1]
                       for k in range(len(pts)) if k not in (i, j)):
                    continue                       # a route through a third node
                pairs.append((i, j))
        if len(pairs) < 2 or len({k for pr in pairs for k in pr}) < 3:
            return None
        # every pixel goes to the connector it lies on, and anything left over
        # stays together so that it is still reported rather than quietly lost
        best = np.full(xs.size, -1)
        bestd = np.full(xs.size, 1e18)
        for idx, (i, j) in enumerate(pairs):
            p, q = pts[i], pts[j]
            dx, dy = q[0] - p[0], q[1] - p[1]
            L = math.hypot(dx, dy) or 1.0
            t = ((xs - p[0]) * dx + (ys - p[1]) * dy) / L
            u = np.abs(-(xs - p[0]) * dy + (ys - p[1]) * dx) / L
            take = (t >= -tol) & (t <= L + tol) & (u < bestd) & (u <= 3 * tol)
            bestd[take] = u[take]
            best[take] = idx
        out = []
        for idx in range(len(pairs)):
            sel = best == idx
            if sel.sum() >= text_floor(font_px):
                out.append((ys[sel], xs[sel]))
        rest = best < 0
        if rest.sum() >= text_floor(font_px):
            out.append((ys[rest], xs[rest]))
        return out if len(out) >= 2 else None

    groups = []
    for grp, ids in members.items():
        px = []
        for i in ids:
            sl = slices[i - 1]
            gy, gx = np.where(lbl[sl] == i)
            px.append((gy + sl[0].start, gx + sl[1].start))
        px.extend(spans.get(grp, []))
        gy = np.concatenate([p[0] for p in px])
        gx = np.concatenate([p[1] for p in px])
        t = touching(gx, gy)
        parts = split_crossing(gx, gy, t) if len(t) > 2 else None
        if parts:
            print("   one component crossing %d nodes split into %d connectors"
                  % (len(t), len(parts)))
            groups.extend((a, b, grp) for a, b in parts)
        else:
            groups.append((gy, gx, grp))

    print("\nEDGES")
    for ys, xs, grp in groups:
        n_px = int(ys.size)
        if n_px < text_floor(font_px):
            continue
        touch = touching(xs, ys)
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
            # A flow that leaves the diagram. The CPFR diagrams are phases of one
            # larger process, so several of their connectors run from a node,
            # across the phase boundary and off the page, to be picked up by the
            # next diagram - there is no second node to find, and the whole line
            # was being discarded as unexplained. It is still line-work, and the
            # node it leaves is still connected to something.
            # Length is only a stand-in for "this runs off the page": a flow that
            # reaches the border has left the diagram however short it is. The two
            # "No" flows into "Ordering" on CPFR-ExceptionMonitor are 135px against
            # a 137px floor, and both were thrown away by that margin - the diagram
            # lost the two arrows that say where its work comes from. Where the
            # component actually touches the border, ask only that it be longer
            # than a line of type.
            edge_margin = max(3.0, 0.015 * max(W, H))
            at_border = (bx0 <= edge_margin or by0 <= edge_margin
                         or bx1 >= W - 1 - edge_margin or by1 >= H - 1 - edge_margin)
            floor = max(font_px, 10) * (1.0 if at_border else 3.0)
            if (len(touch) == 1 and n_px >= EDGE_MIN_AREA
                    and max(bx1 - bx0, by1 - by0) >= floor):
                nd = touch[0]
                cx, cy = nd["x"] + nd["w"] / 2.0, nd["y"] + nd["h"] / 2.0
                near_i = int(np.argmin((xs - cx) ** 2 + (ys - cy) ** 2))
                far_i = int(np.argmax((xs - cx) ** 2 + (ys - cy) ** 2))
                at = (int(xs[near_i]), int(ys[near_i]))
                end = (int(xs[far_i]), int(ys[far_i]))
                # ...unless it stops just short of another node. A connector to a
                # document box stops a little further out than one to an activity,
                # and several were landing 34-40px away - one pixel outside the
                # reach that decides which nodes a component touches - so the flow
                # from "Send Product Activity" to the document beside it became a
                # line running off the page, arrowhead and all.
                reach2 = max(60, 1.2 * font_px)
                other = None
                for cand in nodes:
                    if cand is nd:
                        continue
                    dx = max(cand["x"] - end[0], 0, end[0] - (cand["x"] + cand["w"]))
                    dy = max(cand["y"] - end[1], 0, end[1] - (cand["y"] + cand["h"]))
                    if math.hypot(dx, dy) <= reach2:
                        other = cand
                        break
                if other is not None:
                    touch = [nd, other]          # a connector after all
                else:
                    turns = trace_corners(xs, ys, at, end,
                                          max(2, int(round(font_px * 0.1))))
                    st0 = max(2.0, line_w or 4.0)
                    mh = 0.35 * font_px
                    # which way it runs. A flow arriving from off the page points
                    # at its node - the line down into "Create Retail Event" does -
                    # and drawing every one of them outward left that arrowhead
                    # off. Whether the mark at an open end is a head at all is
                    # settled later, against the size of this diagram's own
                    # arrowhead - a line that simply stops is not one, which is how
                    # the right-hand flow out of "Forecast (sales - positive
                    # response)" gained an arrow the artwork does not draw.
                    out_head = arrow_size(xs, ys, end, (turns[-1] if turns else at),
                                          st0, min_len=mh)
                    in_head = arrow_size(xs, ys, at, (turns[0] if turns else end),
                                         st0, min_len=mh)
                    inward = bool(in_head) and (not out_head
                                                or in_head[1] > out_head[1])
                    if inward:
                        at, end = end, at
                        turns = turns[::-1]
                    head = in_head if inward else out_head
                    open_ends.append(dict(node=nd["id"], at=list(at), end=list(end),
                                          points=turns, arrow=bool(head), inward=inward,
                                          headPx=(list(head) if head else None),
                                          x=bx0, y=by0, w=bx1 - bx0 + 1, h=by1 - by0 + 1))
                    print("   %-4s -> (off the diagram) at %d,%d"
                          % (nd["id"], end[0], end[1]))
                    continue

        if len(touch) != 2 or n_px < EDGE_MIN_AREA:
            bx0, by0 = int(xs.min()), int(ys.min())
            bx1, by1 = int(xs.max()), int(ys.max())
            # Only bin this as text if it is the size and shape of text. A
            # rejected connector is neither, and letting one into the text bin
            # is not harmless: the blocks are merged by proximity in four
            # cascading passes, so a single long fragment chains unrelated
            # labels into one block. That is how a partition title came out 764
            # characters long, carrying half the diagram's words.
            # A short straight stroke drawn across a partition rule. UBL puts a
            # pair of them across the lane divider under the document box on
            # BusinessCard and DigitalCapability, and they belong to no node and
            # no connector, so they were binned with the text, failed to read as
            # text, and vanished off the page. What they mean is the
            # specification's to say; that they are ink is not in question, so
            # they are measured, drawn, and named for a person to confirm.
            m = cross_stub(xs, ys, vr, hr, font_px)
            if m:
                cross_stubs.append(m)
                continue
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
        vx, vy = pb[0] - pa[0], pb[1] - pa[1]

        # A connector within a few degrees of an axis is on that axis. Its two
        # contacts are where the trace met each node, and those can be a few
        # pixels apart across the line - 24px over 782 on CRP-InitialStocking's
        # flows into the join bar - which is enough to make the chord between them
        # a slope the ink never follows. Every reading below is taken against that
        # chord, so it is put right first: the line's own coordinate is the middle
        # of its ink, which is measured and not inferred.
        def reading(qa, qb):
            ux, uy = qb[0] - qa[0], qb[1] - qa[1]
            n = math.hypot(ux, uy) or 1
            d = ((xs - qa[0]) * uy - (ys - qa[1]) * ux) / n
            return n, np.abs(d), float(d.mean())

        def is_line(n, d, sg):
            return abs(sg) < 8.0 and float(np.median(d)) < 0.15 * n + 3.0

        # ...and it is on that axis if putting it there makes its ink lie along
        # it. No angle has to be guessed at: try the axis, keep it only if the
        # reading comes back straight. A connector that really runs at an angle
        # does not straighten when it is squared up, so it keeps its own chord.
        #
        # This is a repair, not a default. A connector whose own two contacts
        # already read as one line is left exactly where they put it: squaring
        # those up as well moved ten connectors a few pixels sideways, off the ink
        # they were drawn on, which is a displacement where there was none.
        if not is_line(*reading(pa, pb)):
            # ...and only by as much as a contact can be out. The two ends of a
            # trace land a few pixels apart on where they met their nodes - 24 and
            # 29 on CRP-InitialStocking, against 73px type. A leg of an L is not
            # that: ExportCustomsDeclaration routes a flow 90px out to the left of
            # its box and then down, against 26px type, and squaring that up
            # straightened a corner the artwork draws.
            slack = max(8.0, 0.5 * font_px)
            axis = None
            if abs(vy) > 8 and abs(vx) <= slack:
                c = int(round(float(np.median(xs))))
                axis = ((c, pa[1]), (c, pb[1]))
            elif abs(vx) > 8 and abs(vy) <= slack:
                c = int(round(float(np.median(ys))))
                axis = ((pa[0], c), (pb[0], c))
            if axis and is_line(*reading(*axis)):
                pa, pb = axis
        vx, vy = pb[0] - pa[0], pb[1] - pa[1]
        L = math.hypot(vx, vy) or 1
        dist = np.abs((xs - pa[0]) * vy - (ys - pa[1]) * vx) / L
        # Is it one line or an elbow? Not the average distance of its ink from
        # the chord between its ends: an arrowhead is 70px wide on the Tender
        # diagrams and every pixel of it is far off the connector's own line, so
        # on a short connector the head alone pushed the average past any
        # threshold and lines the artwork draws dead straight were filed as
        # orthogonal and redrawn with an elbow.
        #
        # A head is symmetric about the line it sits on, so it cancels when the
        # distance keeps its sign; an elbow does not, because all of its ink is on
        # one side of the chord. Measured across the 78, straight connectors come
        # out at 0-5 and elbows at 15-460, so the two do not overlap anywhere near
        # the middle. The second test is for the route that doubles back and
        # cancels: however symmetric, it does not stay near its own chord.
        sgn = float((((xs - pa[0]) * vy - (ys - pa[1]) * vx) / L).mean())
        straight = abs(sgn) < 8.0 and float(np.median(dist)) < 0.15 * L + 3.0
        routing = ("diagonal" if straight and abs(vx) > 8 and abs(vy) > 8
                   else "straight" if straight else "orthogonal")
        turns = trace_corners(xs, ys, pa, pb, max(2, int(round(font_px * 0.1)))) \
            if routing == "orthogonal" else []

        # Which end carries the arrowhead. Counting ink in a fixed 45px square
        # around each contact - which is what this did - is not a measurement of
        # anything on artwork that runs from 26px type to 84px: the square holds a
        # whole node on one diagram and a fraction of the head on another, and the
        # end that happens to touch a node's border wins. Measure the head itself
        # at each end instead, along the connector's own direction there, and fall
        # back to the ink count only when neither end shows one.
        st = max(2.0, line_w or 4.0)
        cxs, cys = corridor(ink, node_fill, pa, pb, int(max(40, 10 * st)))
        if cxs.size < 8:
            cxs, cys = xs, ys
        else:
            # this connector's own weight, read in the middle of it where there is
            # no head to widen it
            vx, vy = pb[0] - pa[0], pb[1] - pa[1]
            L = math.hypot(vx, vy) or 1.0
            tt = ((cxs - pa[0]) * vx + (cys - pa[1]) * vy) / L
            uu = np.abs(-(cxs - pa[0]) * vy + (cys - pa[1]) * vx) / L
            mid = (tt >= 0.4 * L) & (tt <= 0.6 * L) & (uu <= 6 * st)
            if mid.sum() >= 6:
                # ...but not wider than the component itself says it is. A line
                # crossing the middle - the lane divider the two Tender-Contract
                # diagrams run their dashed flow across - puts its own pixels in
                # this band, and they are all far from the connector's axis: the
                # 8px dashed line read as 64px wide, and at that weight nothing on
                # it is an arrowhead any more. The component's own reading cannot
                # see a crossing line, so it is the ceiling here.
                st = max(1.5, min(2.0 * float(np.percentile(uu[mid], 85)),
                                  2.0 * max(2.0, line_w or 4.0)))
        reach = math.hypot(pb[0] - pa[0], pb[1] - pa[1])

        def tip_of(end, back, by=16):
            """the arrow's point, not the connector component's last pixel.

            The component has the node boxes erased from around it with a margin,
            so its end stops short of where the arrow actually touches the node -
            inside the head, where the ink is already wide. Probing from there
            reads a head as flat, which is how the arrow into "Receive & Resolve
            Exception" came out pointing the other way."""
            dx, dy = end[0] - back[0], end[1] - back[1]
            L = math.hypot(dx, dy) or 1.0
            return (int(round(end[0] + dx / L * by)), int(round(end[1] + dy / L * by)))

        back_b = turns[-1] if turns else pa
        back_a = turns[0] if turns else pb
        st0 = max(2.0, line_w or 4.0)

        # First reading: the head as it appears on the connector component. This
        # is what has been deciding direction, and across the 78 diagrams it
        # disagrees with the original on two edges, so it is not replaced.
        min_head = 0.35 * font_px
        wide_a = arrow_size(xs, ys, pa, back_a, st0, min_len=min_head)
        wide_b = arrow_size(xs, ys, pb, back_b, st0, min_len=min_head)
        # A head is a mark of the diagram's own size across the line as well as
        # along it. Where the node erasure cut the point away from its own line -
        # which is what happens at a join bar - what is left of the component at
        # that end is the line itself, and it measured 9.6px across against
        # arrowheads of 79. Taken for a head it decided the direction, and the
        # flow into the bar on UpdateCatalogueItemSpecification came out of it.
        if wide_a and wide_a[1] < 0.3 * font_px:
            wide_a = None
        if wide_b and wide_b[1] < 0.3 * font_px:
            wide_b = None
        wa = wide_a[1] if wide_a else 0.0
        wb = wide_b[1] if wide_b else 0.0

        # It cannot settle a head that fills the whole gap it sits in, though - a
        # short connector between two elements set close together, like "Send
        # Exception Criteria" and the document beside it, 99px apart. A wedge is
        # as wide at one end as at the other, so width says nothing there; what
        # separates them is that the ink narrows to a point at the head's end and
        # not at the tail's. That reading needs the page rather than the component,
        # because the component has the boxes erased from around it and loses the
        # point with them - so it is used only where width has nothing to say.
        # ...and where the component shows no head at either end. That happens
        # when the head is not part of the component: the node erasure around a
        # join bar cuts the point away from its own line, and the direction then
        # fell back to counting ink in a square, which read the flow into the bar
        # on UpdateCatalogueItemSpecification as a flow out of it. The corridor
        # reads the page, so it still has the head the component lost.
        even = wa and wb and max(wa, wb) < 1.3 * min(wa, wb)
        point_a = point_b = None
        if even or not (wa or wb):
            point_a = arrow_size(cxs, cys, tip_of(pa, back_a), back_a, st, reach,
                                 need_point=True, min_len=min_head)
            point_b = arrow_size(cxs, cys, tip_of(pb, back_b), back_b, st, reach,
                                 need_point=True, min_len=min_head)
            # An arrowhead is about as long as it is wide - 0.6 to 1.2 across the
            # 78 - so ink half again wider than it is long is a box edge or a
            # crossing line caught in the probe, not a point. This is the reading
            # that settles the direction where neither end shows a head on the
            # component itself, which is what happens at the apex of a decision
            # diamond: three connectors converge there, so the apex reads as
            # nothing and the other end's box edge reads as a 43x80 "head". The
            # solid diagonal on FulfilmentDespatchAdvice then pointed away from
            # the diamond its point is drawn at.
            if point_a and point_a[1] > 1.6 * point_a[0]:
                point_a = None
            if point_b and point_b[1] > 1.6 * point_b[0]:
                point_b = None
        if os.environ.get("UBL_TRACE_DEBUG"):
            print("      head %s->%s: st=%.1f w=%.0f/%.0f point=%s/%s"
                  % (touch[0]["id"], touch[1]["id"], st, wa, wb, point_a, point_b))

        if point_a or point_b:
            ta = point_a[2] if point_a else 0.0
            tb = point_b[2] if point_b else 0.0
            b_is_head = tb >= ta
            ratio = max(ta, tb) / max(1e-6, min(ta, tb)) if ta and tb else 4.0
        elif wa or wb:
            b_is_head = wb >= wa
            ratio = max(wa, wb) / max(1e-6, min(wa, wb)) if wa and wb else 4.0
        else:
            b_is_head = db >= da
            ratio = max(da, db) / max(1, min(da, db))
        src, dst = (touch[0], touch[1]) if b_is_head else (touch[1], touch[0])
        p_from, p_to = (pa, pb) if b_is_head else (pb, pa)
        head = (wide_b or point_b) if b_is_head else (wide_a or point_a)
        if turns and not b_is_head:
            turns = turns[::-1]
        lo, hi = min(da, db), max(da, db)
        conf = "high" if ratio >= 2.5 else "medium" if ratio >= 1.6 else "LOW"
        if any(set((e["from"], e["to"])) == set((src["id"], dst["id"])) and
               abs(e["fromPoint"][0] - p_from[0]) + abs(e["fromPoint"][1] - p_from[1]) < 80
               for e in edges):
            continue                       # the same connector, found in two pieces
        rec = {"from": src["id"], "to": dst["id"], "routing": routing,
               "fromPoint": list(p_from), "toPoint": list(p_to),
               "arrowInk": [lo, hi], "directionConfidence": conf}
        # where it turns, so the rebuild can put the line back on its own route
        # instead of choosing an elbow of its own
        if turns:
            rec["points"] = turns
        # Dashed or solid, and one head or two. A flow with a point at both ends
        # is not a flow from one of them to the other - the "prior exchange of
        # public keys" the Tender-Contract diagrams draw across their lane divider
        # is a standing relationship between the two parties - and it is exactly
        # the case the direction test cannot settle, because both ends really do
        # look alike. Require a measured point at both ends, of the same size and
        # tapering the same way, so that "cannot tell" is not mistaken for it.
        pa_h = point_a or arrow_size(cxs, cys, tip_of(pa, back_a), back_a, st, reach,
                                     need_point=True, min_len=min_head)
        pb_h = point_b or arrow_size(cxs, cys, tip_of(pb, back_b), back_b, st, reach,
                                     need_point=True, min_len=min_head)
        if (pa_h and pb_h and pa_h[2] >= 1.3 and pb_h[2] >= 1.3
                and max(pa_h[2], pb_h[2]) < 1.4 * min(pa_h[2], pb_h[2])
                and max(pa_h[1], pb_h[1]) < 1.4 * min(pa_h[1], pb_h[1])):
            rec["arrowBoth"] = True
            rec["directionConfidence"] = "both-ends"
        dash = dash_run(ink, node_fill, p_from, p_to, st0,
                        trim=1.2 * (head[0] if head else 0.0))
        if dash:
            rec["dash"], rec["gap"] = dash
        elif grp in chain_dash:
            dl, gp, mx, my = chain_dash[grp]
            rec["dash"], rec["gap"] = dl, gp
            # the phase, for a line drawn as one straight run
            if not rec.get("points"):
                vx, vy = p_to[0] - p_from[0], p_to[1] - p_from[1]
                LL = math.hypot(vx, vy)
                if LL > 1:
                    t0 = ((mx - p_from[0]) * vx + (my - p_from[1]) * vy) / LL
                    rec["dashOffset"] = round((-(t0 - dl / 2.0)) % (dl + gp), 1)
        if head:
            # measured again, now that the direction is settled, with the walk
            # allowed to run forward to the head's actual point. The reading above
            # decided which end carries the head and must stay as it is; this one
            # only says how big to draw it.
            # on the page rather than on the component: the connector component
            # has the node boxes erased from around it with a margin, and the
            # head's point is inside that margin, so the walk forward finds
            # nothing there and the head measures short exactly where it matters.
            full = arrow_size(cxs, cys, p_to, (turns[-1] if turns else p_from), st,
                              reach, min_len=min_head, ahead=int(max(10, 8 * st)))
            if full and full[0] > head[0]:
                head = full
            rec["arrowPx"] = list(head[:3])
            # A walk that ran to the end of its own probe never found where the
            # head stops, and reports the probe's length instead: ProcurementProcess
            # draws its flows as long diagonals, and four of them read as 111px
            # heads - the probe - against real heads of about 40. The reading still
            # stands for deciding which end carries the head, because that compares
            # one end against the other; it is only useless as a size, so it is
            # marked here and left out of the diagram's own measurement below.
            if head[4]:
                rec["arrowSaturated"] = True
            # Solid triangle or open "V". The transport diagrams of UBL 2.3 fill
            # their arrowheads and the CPFR and billing diagrams leave them open,
            # and drawing every one of them open put a thin two-stroke mark where
            # the artwork has a solid wedge - visible on the page, and the largest
            # single class the difference could not name.
            #
            # Read it where the two drawings actually differ: inside the wedge,
            # between the shaft and the barb. A filled head has ink there and an
            # open one has white. Counting ink per unit of area around the tip -
            # which is what this did - measures the head's own proportions instead,
            # and read the same heads as filled or open depending only on how much
            # of their length had been measured.
            L, Wd = head[0], head[1]
            bp = (turns[-1] if turns else p_from)
            hL = math.hypot(p_to[0] - bp[0], p_to[1] - bp[1]) or 1.0
            hx, hy = (p_to[0] - bp[0]) / hL, (p_to[1] - bp[1]) / hL
            ap = (p_to[0] + hx * head[3], p_to[1] + hy * head[3])
            y0, y1 = int(max(0, ap[1] - L)), int(min(H, ap[1] + L))
            x0, x1 = int(max(0, ap[0] - L)), int(min(W, ap[0] + L))
            patch = ink[y0:y1, x0:x1] & ~node_fill[y0:y1, x0:x1]
            if patch.size:
                yy, xx = np.nonzero(np.ones_like(patch))
                tt = -((xx + x0 - ap[0]) * hx + (yy + y0 - ap[1]) * hy)
                uu = np.abs(-(xx + x0 - ap[0]) * hy + (yy + y0 - ap[1]) * hx)
                edge_u = (Wd / 2.0) * np.clip(tt / max(L, 1.0), 0, 1)
                shaft = max(st / 2.0, 1.0) + 1.0
                inside = ((tt >= 0.45 * L) & (tt <= 0.95 * L) &
                          (uu >= shaft) & (uu <= 0.6 * edge_u))
                if inside.sum() >= 6:
                    rec["arrowFill"] = round(
                        float(patch.reshape(-1)[inside].mean()), 3)
        edges.append(rec)
        print("   %-4s -> %-4s  %-11s arrowhead %5d vs %-5d  ratio %.1f  %s"
              % (src["id"], dst["id"], routing, hi, lo, ratio,
                 "<-- CHECK DIRECTION" if conf == "LOW" else conf))

    # Blocks are joined when they are close enough to be one label. The gap
    # across was a flat 70px, which at 36px type is two ems: on
    # IMFM-BasicTransportExecutionPlan that swallowed the "[yes]" beside a
    # connector into the question standing on the other side of it, and the two
    # were then read as one line - "\u201c|* Update Transport es) Execution Plan
    # Request?" - and drawn as one. A word gap is a third of an em, so measure
    # this in the diagram's own type too.
    def merge(bs, gx=max(24, int(font_px * 0.9)), gy=max(16, int(font_px * 0.9))):
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

    cross_marks = join_stubs(cross_stubs)
    for m in cross_marks:
        print("   mark across the %s rule at %d: %.0fpx at %.0f degrees%s"
              % ("column" if m["rule"] == "v" else "band", m["at"], m["length"],
                 m["angle"], "" if m["whole"] else " (one half only)"))
    if cross_marks:
        uncertain.append(dict(
            kind="mark-across-rule", x=min(m["x1"] for m in cross_marks),
            y=min(m["y1"] for m in cross_marks),
            w=max(m["x2"] for m in cross_marks) - min(m["x1"] for m in cross_marks),
            h=max(m["y2"] for m in cross_marks) - min(m["y1"] for m in cross_marks),
            reason="%d short stroke(s) drawn across a partition rule; they are"
                   " redrawn as measured, but what they denote is not read"
                   % len(cross_marks),
            check="name this notation - the SVG carries it as line-work only"))

    print("\nTEXT (titles, guards, notes)")
    texts = []
    strays = []          # line-work that read as text: nearly always an arrowhead
    for b in lines:
        w, h = b[2] - b[0] + 1, b[3] - b[1] + 1
        # ...and a block is too small to be text in this diagram's own type, not in
        # a flat number of pixels: 25x14 is a word at 40px type and a whole "No" at
        # 26px type, which is why four of the transport diagrams lost theirs.
        if w < max(16, 0.55 * font_px) or h < max(10, 0.35 * font_px):
            continue
        # The gutter down the side carries the band titles, set sideways, and the
        # partition pass reads them there by turning the crop. Read across, as
        # here, they come back as nonsense - "Planning" as "Cc co Qa." - and IMFM
        # drew both, the nonsense on top of the title. The header band along the
        # top is different: its titles read correctly either way, and the reading
        # here is the one that knows where they sit, so it stays.
        mx = b[0] + w / 2.0
        if strip and mx < vb[1]:
            print("   (dropped x=%-5d y=%-5d %4dx%-4d - in the band-title gutter,"
                  " where the text is set sideways and is read there)"
                  % (b[0], b[1], w, h))
            continue
        t = ocr(bg, b[0], b[1], w, h, -6)
        if not t:
            continue
        # ...unless it reads as an actual word. Line-work comes back as one or
        # two characters of punctuation - "\\V/", "TZ", "DN" - and a run of four
        # letters is not something an arrowhead produces.
        box_b = dict(x=b[0], y=b[1], w=w, h=h)
        if (not re.search(r"[A-Za-z]{4,}", t)
                and (line_like(ink, box_b, font_px)
                     or ocr_best_conf(bg, b[0], b[1], w, h, -6) < TEXT_CONF)):
            print("   (dropped x=%-5d y=%-5d %4dx%-4d  %r - line-work, not text)"
                  % (b[0], b[1], w, h, t))
            strays.append((b[0] + w / 2.0, b[1] + h / 2.0))
            continue
        item = dict(text=t, x=b[0], y=b[1], w=w, h=h)
        got = t.split("\n")
        boxes = label_lines(ink, dict(x=b[0], y=b[1], w=w, h=h), -4)
        # ...and line by line as well as block by block. The blocks are merged by
        # proximity, so an arrowhead lying beside a real label joins it and rides
        # in on the label's own good name: "[accept credit]" came back as
        # "[accept credit] \ Ne" on SelfBillingwithCreditNote and the "\ Ne" was
        # drawn on the page. A band that does not read as text is not text, even
        # when the band above it is.
        def reads_as_text(bx):
            if re.search(r"[A-Za-z]{4,}",
                         ocr(bg, bx["x"], bx["y"], bx["w"], bx["h"], -4)):
                return True
            if line_like(ink, bx, font_px):
                return False
            return (ocr_best_conf(bg, bx["x"], bx["y"], bx["w"], bx["h"], -4)
                    >= TEXT_CONF)

        trimmed = []
        for bx in boxes:
            # The ends of a band are where a stray mark attaches itself: the
            # blocks are merged by proximity, so an arrowhead beside a label joins
            # its band and rides in on the label's good name - "[accept credit]"
            # came back as "[accept credit] \ Ne". Judge a short run at either end
            # on its own; the middle of a band is words by construction.
            runs = word_groups(ink, bx, font_px)
            if len(runs) >= 2:
                short = 2.0 * font_px
                def stray(r):
                    # line-work, not merely a word tesseract read badly: trimming
                    # on a bad reading alone took "n Request]" off the end of a
                    # real label on IMFM-BasicTransportExecutionPlan
                    return (r["w"] <= short and line_like(ink, r, font_px)
                            and not reads_as_text(r))
                while len(runs) >= 2 and stray(runs[0]):
                    runs = runs[1:]
                while len(runs) >= 2 and stray(runs[-1]):
                    runs = runs[:-1]
                x_lo = min(g["x"] for g in runs)
                x_hi = max(g["x"] + g["w"] for g in runs)
                if x_hi - x_lo < bx["w"] - 4:
                    print("   (trimmed a line at x=%-5d y=%-5d from %dpx to %dpx -"
                          " line-work beside the words)"
                          % (bx["x"], bx["y"], bx["w"], x_hi - x_lo))
                    strays.append((bx["x"] + bx["w"] / 2.0, bx["y"] + bx["h"] / 2.0))
                    bx = dict(bx, x=x_lo, w=x_hi - x_lo)
            if reads_as_text(bx):
                trimmed.append(bx)
                continue
            keep_w = [g for g in word_groups(ink, bx, font_px) if reads_as_text(g)]
            if not keep_w:
                print("   (dropped a line at x=%-5d y=%-5d %4dx%-4d - line-work,"
                      " not text)" % (bx["x"], bx["y"], bx["w"], bx["h"]))
                strays.append((bx["x"] + bx["w"] / 2.0, bx["y"] + bx["h"] / 2.0))
                continue
            x_lo = min(g["x"] for g in keep_w)
            x_hi = max(g["x"] + g["w"] for g in keep_w)
            if x_hi - x_lo < bx["w"] - 4:
                print("   (trimmed a line at x=%-5d y=%-5d from %dpx to %dpx -"
                      " line-work beside the words)"
                      % (bx["x"], bx["y"], bx["w"], x_hi - x_lo))
                strays.append((bx["x"] + bx["w"] / 2.0, bx["y"] + bx["h"] / 2.0))
            trimmed.append(dict(bx, x=x_lo, w=x_hi - x_lo))
        if trimmed != boxes:
            boxes = trimmed
            got = []                      # force the per-line read below
        if boxes and len(boxes) == len(got):
            item["lines"] = [dict(bx, text=s2) for bx, s2 in zip(boxes, got)]
        elif boxes:
            # The block reader and the ink disagree on how many lines there are -
            # an arrowhead caught in the block adds a ">", two lines set close
            # together merge - and with no pairing the rebuild had nowhere to put
            # any of them: it centred the lot on the block and drew them at the
            # diagram's type size. Read each band on its own instead, so every
            # line has its own place and its own width, measured.
            per = [" ".join(ocr(bg, bx["x"], bx["y"], bx["w"], bx["h"], -4).split())
                   for bx in boxes]
            keep_l = [(bx, p) for bx, p in zip(boxes, per) if p]
            if keep_l:
                item["text"] = "\n".join(p for _, p in keep_l)
                item["lines"] = [dict(bx, text=p) for bx, p in keep_l]
            elif not got:
                continue                  # every band was line-work
        # A guard is a short label standing beside the branch it belongs to. Half
        # of this artwork brackets them - "[accept charges]" - and half does not:
        # the transport diagrams write a plain "Yes" and "No", and requiring the
        # brackets left every one of those unattached, so the model could not say
        # which way out of a decision was which.
        one_line = " ".join(t.split())
        in_title_strip = (header and b[1] < hb[1]) or (strip and b[0] < vb[1])
        if (not in_title_strip
                and (t.startswith("[") or t.endswith("]")
                     or (len(one_line) <= 14 and len(one_line.split()) <= 2
                         and len(re.sub(r"[^0-9A-Za-z]", "", one_line)) >= 2))):
            cx, cy = b[0] + w / 2, b[1] + h / 2
            kinds = {n["id"]: n["kind"] for n in nodes}
            bracketed = t.startswith("[") or t.endswith("]")
            best, bd = None, 1e18
            for e in edges:
                branch = kinds.get(e["from"]) in ("decision", "fork")
                # An unbracketed word is only a guard where a guard can be: on a
                # branch. Without that, "Producer" and "Importer Party" - lane
                # titles on the diagrams that set them without a header band -
                # attached themselves to the flow out of the start event, which is
                # not a thing an activity diagram has.
                if not branch and not bracketed:
                    continue
                bias = 1.0 if branch else 2.25
                for p in (e["fromPoint"], e["toPoint"]):
                    d = ((p[0] - cx) ** 2 + (p[1] - cy) ** 2) * bias
                    if d < bd:
                        bd, best = d, e
            if best is not None and bd < (W * 0.12) ** 2:
                best["guard"] = one_line
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
            # ...and where it sits, measured off its own ink rather than assumed
            # to be centred in the cell: the rebuild draws the title where the
            # artwork puts it, and the check that every word is in the right place
            # has nothing to go on otherwise.
            cx0, cx1 = int(vb[c]) + 6, int(vb[c + 1]) - 6
            cy0 = int(hr[0][0] + hr[0][1] + 4) if hr else 2      # below the frame
            cy1 = max(int(hb[r0]) - 4, cy0 + 1)
            cell = ink[cy0:cy1, cx0:cx1]
            if cell.any():
                yy, xx = np.nonzero(cell)
                box = dict(x=cx0 + int(xx.min()), y=cy0 + int(yy.min()),
                           w=int(xx.max() - xx.min()) + 1,
                           h=int(yy.max() - yy.min()) + 1)
        else:
            # no header band: the title is simply the topmost text in the column
            cand = [x for x in texts if vb[c] <= x["x"] + x["w"] / 2 <= vb[c + 1]
                    and x["y"] < H * 0.08]
            box = min(cand, key=lambda x: x["y"]) if cand else None
            t = box["text"] if box else ""
        # the rule beside the strip lands in the crop and reads as a bar
        t = re.sub(r"^[^0-9A-Za-z]+|[^0-9A-Za-z)\]]+$", "", t).strip()
        g = dict(axis="column", index=c - c0,
                 x0=round(vb[c]), x1=round(vb[c + 1]), title=t)
        if box:
            g["titleBox"] = [box["x"], box["y"], box["w"], box["h"]]
        grid.append(g)
    for r in range(r0, len(hb) - 1):
        t = ""
        if strip:
            x0, y0 = round(vb[c0 - 1]), round(hb[r])
            w0, h0 = round(vb[c0] - vb[c0 - 1]), round(hb[r + 1] - hb[r])
            t = ocr(bg.crop((x0 + 4, y0 + 4, x0 + w0 - 4, y0 + h0 - 4)).rotate(-90, expand=True),
                    0, 0, h0 - 8, w0 - 8)
        t = re.sub(r"^[^0-9A-Za-z]+|[^0-9A-Za-z)\]]+$", "", t).strip()
        grid.append(dict(axis="band", index=r - r0, y0=round(hb[r]), y1=round(hb[r + 1]), title=t))
    for n in nodes:
        cx, cy = n["x"] + n["w"] / 2, n["y"] + n["h"] / 2
        n["col"] = sum(1 for b in vb[1:-1] if cx > b) - c0
        n["row"] = sum(1 for b in hb[1:-1] if cy > b) - r0
    # An arrowhead the node erasure cut away from its own line is a mark on the
    # page that belongs to no component: it reads as text, fails to read as text,
    # and is dropped above. It still says where the head is, though, and that is
    # exactly what the edges it sits on could not work out for themselves - a join
    # bar takes the point of every flow arriving at it. So where one such mark
    # sits at one end of an edge and nothing sits at the other, and the edge is
    # one the direction probe could not settle, the head is at the mark.
    if strays:
        r2 = (1.5 * font_px) ** 2
        for e in edges:
            if e.get("directionConfidence") != "LOW":
                continue
            def near(p):
                return min(((p[0] - sx) ** 2 + (p[1] - sy) ** 2)
                           for sx, sy in strays) <= r2
            if near(e["fromPoint"]) and not near(e["toPoint"]):
                e["from"], e["to"] = e["to"], e["from"]
                e["fromPoint"], e["toPoint"] = e["toPoint"], e["fromPoint"]
                if e.get("points"):
                    e["points"] = e["points"][::-1]
                e["directionConfidence"] = "mark-at-head"
                print("   %-4s -> %-4s  turned round: the point it lost sits at the"
                      " other end" % (e["from"], e["to"]))

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
        # the diagram's own arrowhead, as the median of the heads measured on its
        # connectors: the lengths cluster tightly, the widths do not, because a
        # crossing line lands inside the probe
        # The size of this diagram's arrowhead, from the heads measured on its
        # connectors. A walk that ran to the end of its probe never found where the
        # head stops and reports the probe's length instead - ProcurementProcess
        # had four such, all at 111px, against real heads of about 38 - so the
        # median is taken over the shortest cluster rather than over everything.
        # Only the readings that found both ends of the head. The rest measured the
        # probe. Cut what remains against its own median rather than against the
        # shortest reading, because short readings happen too - a head whose point
        # is buried in a node's border measures only the part behind the contact -
        # and a floor set by the shortest threw away every head measured in full.
        # A head is also narrower than it is long - across all 78 diagrams the
        # measured aspect sits between 0.8 and 1.1 - so a reading half again wider
        # than it is long is a box's border caught in the probe, not a head.
        sized = [e for e in edges if e.get("arrowPx") and not e.get("arrowSaturated")
                 and e["arrowPx"][1] <= 1.6 * e["arrowPx"][0]]
        heads = sorted(e["arrowPx"][0] for e in sized)
        widths = sorted(e["arrowPx"][1] for e in sized)
        # Where too little of the diagram reads, say so rather than drawing to a
        # number taken from two readings. UBL-1.0-ProcurementProcess is the case:
        # its flows are long diagonals meeting boxes at an angle, every probe ends
        # on a border, and the three readings that survive are 61, 76 and 106px
        # against heads of about 40. The head is then set from the diagram's own
        # type size, which is the one measurement it does give up reliably and
        # which the other 77 diagrams' heads track at around 1.1 times.
        if len(heads) < max(2, 0.25 * len(edges)):
            heads, widths = [], []
            if edges:
                uncertain.append(dict(
                    kind="arrowhead-size-unreadable", x=0, y=0, w=W, h=H,
                    reason="only %d of %d connectors gave a usable arrowhead"
                           " measurement; the head is drawn at 1.1x the type size"
                           % (len(sized), len(edges))))
        if heads:
            keep = [h for h in heads if h <= 2 * float(np.median(heads))]
            arrow_px = round(float(np.median(keep or heads)), 1)
            # the width of the same cluster, not of everything: a head measured
            # across a crossing line is wide for the wrong reason
            tw = [e["arrowPx"][1] for e in sized if e["arrowPx"][0] <= 2 * arrow_px]
            arrow_w = float(np.median(tw or widths))
        else:
            arrow_px = round(1.1 * font_px, 1) if edges else 0.0
            arrow_w = round(0.9 * arrow_px, 1)
        fills = [e["arrowFill"] for e in edges if e.get("arrowFill") is not None]
        arrow_fill = "filled" if fills and float(np.median(fills)) >= 0.5 else "open"
        if arrow_px:
            print("\nARROWHEAD  %.0f x %.0fpx, %s, %s"
                  % (arrow_px, arrow_w, arrow_fill,
                     "measured on %d connector(s)" % len(heads) if heads
                     else "no connector read - set from the type size"))
        # A head at both ends is a real thing - the two Tender-Contract diagrams
        # draw their "prior exchange of public keys" that way - but it is also
        # what a connector reads as when its far end lands where several lines
        # and a box corner meet. The two real ones measure 1.01 and 1.04 times
        # their diagram's own arrowhead across; the flow from "change order" to
        # "receive advice" on UBL-1.0-ProcurementProcess measured 3.2 times, which
        # is not an arrowhead but the junction it ends in.
        if arrow_w:
            for e in edges:
                if not e.get("arrowBoth"):
                    continue
                wd = (e.get("arrowPx") or [0, 0, 0])[1]
                if not (0.6 * arrow_w <= wd <= 1.6 * arrow_w):
                    print("   (%s -> %s: the head at its far end is %.0fpx across"
                          " against a %.0fpx arrowhead - not a head at both ends)"
                          % (e["from"], e["to"], wd, arrow_w))
                    e.pop("arrowBoth", None)
                    if e.get("directionConfidence") == "both-ends":
                        e["directionConfidence"] = "medium"

        # An open end has no node to stop at, so a line that simply runs out can
        # read as a head. Against the diagram's own arrowhead it cannot: keep only
        # the ones that are the right size for this drawing.
        for o in open_ends:
            if o["arrow"] and arrow_px:
                L, Wd = (o.get("headPx") or [0, 0])[:2]
                if not (0.5 * arrow_px <= L <= 2.0 * arrow_px) or Wd < 0.5 * arrow_w:
                    print("   (%s: the mark at its open end is %.0fx%.0f against a"
                          " %.0fx%.0f arrowhead - not a head)"
                          % (o["node"], L, Wd, arrow_px, arrow_w))
                    o["arrow"] = False
        # Two directions an activity diagram fixes whatever the ink says: nothing
        # leaves an end event and nothing enters a start event. The arrowheads on
        # UBL-1.0-ProcurementProcess are 42px on a 3425px page and the one at its
        # end event read backwards, so the only end on the diagram was drawn
        # handing work to "reconcile invoice". This is notation, not a reading, so
        # it settles the direction rather than competing with it.
        kind_of = {n["id"]: n["kind"] for n in nodes}
        for e in edges:
            flip = (kind_of.get(e["from"]) == "final"
                    or kind_of.get(e["to"]) == "initial")
            if not flip:
                continue
            what = "an end event" if kind_of.get(e["from"]) == "final" else "a start event"
            print("   turned %s -> %s round: %s is at the wrong end of it"
                  % (e["from"], e["to"], what))
            e["from"], e["to"] = e["to"], e["from"]
            e["fromPoint"], e["toPoint"] = e.get("toPoint"), e.get("fromPoint")
            if isinstance(e.get("arrowInk"), list) and len(e["arrowInk"]) == 2:
                e["arrowInk"] = [e["arrowInk"][1], e["arrowInk"][0]]
            if e.get("points"):
                e["points"] = list(reversed(e["points"]))
            e["directionConfidence"] = "notation"

        # A document is written by something and read by something - that is what
        # a document *is* in an activity diagram, and UBL draws every one of them
        # that way. So a document whose flows all point the same way has one of
        # them backwards, and the arrowheads say which: the one whose two ends are
        # closest to carrying the same amount of ink was the least decided.
        #
        # This can only fire where the reading is impossible, which across the 78
        # is two flows, both on UBL-1.0-ProcurementProcess - the coin-flip at
        # Order (160 against 163) and the flow from "accept order" to the second
        # OrderResponseSimple. It is a repair, not a preference: where the flows
        # already go both ways it does nothing.
        def decided(e):
            ink2 = e.get("arrowInk") or [1, 1]
            lo, hi = sorted((max(ink2[0], 1), max(ink2[1], 1)))
            return hi / float(lo)

        for n in nodes:
            if n["kind"] != "object":
                continue
            ins = [e for e in edges if e["to"] == n["id"]]
            outs = [e for e in edges if e["from"] == n["id"]]
            side = ins if (ins and not outs) else (outs if (outs and not ins) else None)
            if side is None or len(side) < 2:
                continue
            e = min(side, key=decided)
            print("   turned %s -> %s round: %r is %s but nothing %s it, and this"
                  " flow's two ends carry the same ink to within %.0f%%"
                  % (e["from"], e["to"], " ".join((n.get("label") or "").split()),
                     "read by all of them" if side is outs else "written by all of them",
                     "writes" if side is outs else "reads", 100 * (decided(e) - 1)))
            e["from"], e["to"] = e["to"], e["from"]
            e["fromPoint"], e["toPoint"] = e.get("toPoint"), e.get("fromPoint")
            if isinstance(e.get("arrowInk"), list) and len(e["arrowInk"]) == 2:
                e["arrowInk"] = [e["arrowInk"][1], e["arrowInk"][0]]
            if e.get("points"):
                e["points"] = list(reversed(e["points"]))
            e["directionConfidence"] = "notation"

        # An unlabelled diamond is a plain branch: one flow in and the rest out.
        # Measured across the 78 rather than assumed - of the 31 diamonds that
        # carry no label, 28 already read that way, and the exceptions are three
        # on UBL-1.0-ProcurementProcess, whose diamonds are 29px across with as
        # many as five flows meeting at them. A *labelled* diamond is a different
        # thing and is left alone: UML allows a merge and a decision to share one
        # symbol, and the Billing family draws exactly that - "Reconcile Charges"
        # takes two flows in and sends two out, guards on all four, which I
        # checked against the artwork before writing this.
        #
        # Which flow is the incoming one cannot be had from the arrowheads there:
        # where five lines converge on a shape smaller than the type, the ink at
        # that end belongs to all of them. The page says it instead - these
        # diagrams run top to bottom, and the step a branch follows is drawn above
        # it. That reading is right for 19 of the 22 one-in diamonds where exactly
        # one flow comes from above, which is not good enough to be a rule on its
        # own; it only has to settle the three places where the shape is
        # impossible, and there is no other evidence left to prefer.
        for n in nodes:
            if n["kind"] != "decision" or " ".join((n.get("label") or "").split()):
                continue
            ins_ = [e for e in edges if e["to"] == n["id"]]
            if len(ins_) < 2:
                continue
            outs_ = [e for e in edges if e["from"] == n["id"]]
            cy = n["y"] + n["h"] / 2.0

            def far_y(e):
                oid = e["from"] if e["to"] == n["id"] else e["to"]
                o = next((m for m in nodes if m["id"] == oid), None)
                return (o["y"] + o["h"] / 2.0) if o else cy

            keep = min(ins_ + outs_, key=far_y)
            if keep not in ins_:
                keep = min(ins_, key=far_y)
            for e in ins_:
                if e is keep:
                    continue
                print("   turned %s -> %s round: an unlabelled diamond takes one"
                      " flow in and sends the rest out, and this one comes from"
                      " below it" % (e["from"], e["to"]))
                e["from"], e["to"] = e["to"], e["from"]
                e["fromPoint"], e["toPoint"] = e.get("toPoint"), e.get("fromPoint")
                if isinstance(e.get("arrowInk"), list) and len(e["arrowInk"]) == 2:
                    e["arrowInk"] = [e["arrowInk"][1], e["arrowInk"][0]]
                if e.get("points"):
                    e["points"] = list(reversed(e["points"]))
                e["directionConfidence"] = "notation"

        json.dump(dict(source=path, size=[W, H], fontPx=font_px, arrowPx=arrow_px,
                       arrowWidthPx=round(arrow_w, 1), arrowStyle=arrow_fill,
                       rules=dict(v=vr, h=hr), greyRules=greys, dashed=dboxes,
                       openEnds=open_ends, crossMarks=cross_marks,
                       partitions=grid, nodes=nodes, edges=edges, text=texts,
                       uncertain=uncertain),
                  open(out_json, "w"), indent=1)
        print("\nwrote %s   (%d nodes, %d edges, %d flagged for a human)"
              % (out_json, len(nodes), len(edges), len(uncertain)))


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    oj = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    main(a[0], oj)
