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
import sys, os, json, math
import numpy as np
import scipy.ndimage as ndi
from PIL import Image
import pytesseract

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ocr_cache

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


def enclosed_regions(ink, min_area=MIN_NODE_AREA):
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
        if area < min_area:
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


def arrow_size(xs, ys, tip, back, stroke, limit=None, need_point=False, min_len=0.0):
    """How big the arrowhead at `tip` is, in the original's own pixels.

    The rebuild drew every arrowhead at one hard-coded size, so the same head
    appeared on artwork drawn at 26px type and at 84px type: on the small
    diagrams it swamped the node it pointed at. The head is in the pixels like
    everything else - it is the stretch just behind the tip where the connector is
    wider than its own stroke.

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
    # An arrowhead is a mark of the diagram's own size. Ten pixels of ink where a
    # connector meets a box is a join or a corner, not a head - and taken for one
    # it pointed "Send Trade Item Location Profile" at the wrong element.
    if length < min_len:
        return None
    # Which end is the point. An arrowhead is a wedge, so its ink is narrow at the
    # tip and wide away from it; probed from the *other* end the same ink is wide
    # at the near end and narrow further along. Width alone therefore reads the
    # same at both ends of a head - which is how "Send Exception Criteria" came
    # out pointing at the wrong element, its head being nearly as long as the
    # 99px gap it sits in. The taper is what tells them apart.
    lo = half[1:max(2, length // 3) + 1]
    hi = half[max(1, 2 * length // 3):length + 1]
    taper = (float(hi.mean()) / max(float(lo.mean()), 0.5)) if lo.size and hi.size else 1.0
    return round(length, 1), round(width, 1), round(taper, 2)


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
                 # and it has to be big enough to be a node in its own right. The
                 # floor on a region's area now scales with the type, so that a
                 # small activity final's ring is not missed; letting those
                 # smaller regions veto a parent as well cost IMFM three object
                 # nodes, each vetoed by a 34x30 counter in its own bold label.
                 b["area"] >= MIN_NODE_AREA and
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
        if fill > 0.70 and ar < 1.35 and 6 < w < W * 0.06:
            discs.append(dict(d, kind="initial"))
        elif (ar > 3 and min(w, h) <= 60
                and max(w, h) > max(W * 0.012, 2.5 * glyph_h)):
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
                if hi - lo + 1 >= 2:
                    # the erosion took 3px off each side; the long axis keeps the
                    # component's own extent, the short axis is the measured band
                    if w >= h:
                        d = dict(d, y=int(y0) + int(lo) - 3, h=int(hi - lo + 1) + 6)
                    else:
                        d = dict(d, x=int(x0) + int(lo) - 3, w=int(hi - lo + 1) + 6)
                    bars.append(dict(d, kind="fork"))
            elif fill > 0.70:
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

        out = []
        for g in groups:
            line = (ink[:, g[0]:g[-1] + 1].any(axis=1) if axis == "v"
                    else ink[g[0]:g[-1] + 1, :].any(axis=0))
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
                out.append((int(g[0]), int(g[-1] - g[0] + 1)))
                if partial is not None and not all(ends):
                    partial.add((axis, int(g[0])))
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
    regs = drop_phantoms(ink, enclosed_regions(ink, min_area), cells, flags=uncertain,
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
    # A fork bar is drawn much heavier than a line - across the 78 diagrams every
    # real one is at least four times the diagram's own stroke, 18px and up
    # against strokes of 3 to 6. What is merely as thick as a stroke is a stroke:
    # the top edge of a rounded box drawn at 8px survives the erosion that is
    # meant to make line-work vanish, and 27 such "bars" were found, every one of
    # them with no connector attached because there was no node there to connect.
    line_w = float(np.median(box_strokes)) if box_strokes else 0.0
    if line_w:
        real = [b for b in bars if min(b["w"], b["h"]) >= 2 * line_w]
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

    members = {}
    for i in range(1, ncomp + 1):
        if slices[i - 1] is not None:
            members.setdefault(root(i), []).append(i)

    edges, textbits, unexplained, open_ends = [], [], [], []
    print("\nEDGES")
    for grp, ids in members.items():
        px = []
        for i in ids:
            sl = slices[i - 1]
            ys, xs = np.where(lbl[sl] == i)
            px.append((ys + sl[0].start, xs + sl[1].start))
        px.extend(spans.get(grp, []))
        ys = np.concatenate([p[0] for p in px])
        xs = np.concatenate([p[1] for p in px])
        n_px = int(ys.size)
        if n_px < TEXT_MIN_AREA:
            continue
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
            # A flow that leaves the diagram. The CPFR diagrams are phases of one
            # larger process, so several of their connectors run from a node,
            # across the phase boundary and off the page, to be picked up by the
            # next diagram - there is no second node to find, and the whole line
            # was being discarded as unexplained. It is still line-work, and the
            # node it leaves is still connected to something.
            if (len(touch) == 1 and n_px >= EDGE_MIN_AREA
                    and max(bx1 - bx0, by1 - by0) >= 3 * max(font_px, 10)):
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
        L = math.hypot(vx, vy) or 1
        dist = np.abs((xs - pa[0]) * vy - (ys - pa[1]) * vx) / L
        straight = float(dist.mean()) < 6.0
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
                st = max(1.5, 2.0 * float(np.percentile(uu[mid], 85)))
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
        even = wa and wb and max(wa, wb) < 1.3 * min(wa, wb)
        point_a = point_b = None
        if even:
            point_a = arrow_size(cxs, cys, tip_of(pa, back_a), back_a, st, reach,
                                 need_point=True, min_len=min_head)
            point_b = arrow_size(cxs, cys, tip_of(pb, back_b), back_b, st, reach,
                                 need_point=True, min_len=min_head)
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
        if head:
            rec["arrowPx"] = list(head)
        edges.append(rec)
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
        # the diagram's own arrowhead, as the median of the heads measured on its
        # connectors: the lengths cluster tightly, the widths do not, because a
        # crossing line lands inside the probe
        # The size of this diagram's arrowhead, from the heads measured on its
        # connectors. A walk that ran to the end of its probe never found where the
        # head stops and reports the probe's length instead - ProcurementProcess
        # had four such, all at 111px, against real heads of about 38 - so the
        # median is taken over the shortest cluster rather than over everything.
        heads = sorted(e["arrowPx"][0] for e in edges if e.get("arrowPx"))
        widths = sorted(e["arrowPx"][1] for e in edges if e.get("arrowPx"))
        if heads:
            tight = [h for h in heads if h <= 2 * heads[0]]
            arrow_px = round(float(np.median(tight)), 1)
            arrow_w = float(np.median(widths))
        else:
            arrow_px, arrow_w = 0.0, 0.0
        if arrow_px:
            print("\nARROWHEAD  %.0fpx long over %d connector(s)" % (arrow_px, len(heads)))
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
        json.dump(dict(source=path, size=[W, H], fontPx=font_px, arrowPx=arrow_px,
                       rules=dict(v=vr, h=hr), greyRules=greys, dashed=dboxes,
                       openEnds=open_ends,
                       partitions=grid, nodes=nodes, edges=edges, text=texts,
                       uncertain=uncertain),
                  open(out_json, "w"), indent=1)
        print("\nwrote %s   (%d nodes, %d edges, %d flagged for a human)"
              % (out_json, len(nodes), len(edges), len(uncertain)))


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    oj = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    main(a[0], oj)
