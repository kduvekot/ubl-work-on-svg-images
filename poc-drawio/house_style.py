#!/usr/bin/env python3
"""A figure's spec in a house style: one look for the same element everywhere.

    python3 house_style.py <spec.json> <out-spec.json> [--no-space] [--right-angles | --drawio-routing]

A proposal, for the TC to see what a uniform set looks like; nothing of it is
decided. The figure keeps its layout: it is scaled so its labels come out at
the house label size, and every element keeps its measured centre. A box
keeps its measured size too - a figure that draws its actions as tall
columns, with many flows along their sides (IMFM), keeps them so - and only
grows where its words would not fit. What the house style sets is what makes
the same element look the same: weights, type, corners, heads, discs, bars,
lane titles. The values are the medians of the census over all 78 figures
(census.md), taken relative to the label size:

    label                      12 px Helvetica (draw.io's own default)
    lines, action outline      0.10 of the label size
    document outline           0.16
    lane divider               0.11
    frame                      0.18
    arrowhead                  1.35 long, 0.81 as wide as long, open
    action, document           its measured size, at least its words + 1
                               label size each side and 0.8 (action) or 1.2
                               (document) above and below
    action corners             one radius, 1.3 label sizes, in every action
                               (at most half its height)
    document on a divider      centred on it, when it is less than 1.5 label
                               sizes off
    decision with a question   its measured size, at least around its words
    decision without           2 across
    lane titles                centred 1.3 label sizes below the frame's
                               top, plain, no rule under them
    flows                      within 0.75 label sizes of level or upright:
                               made exactly so; at an angle: kept (or, with
                               --right-angles / --drawio-routing, routed
                               across and down, as a trial)
    room                       where boxes come too close, or out of their
                               lane, the figure is opened up at a line
                               between them (make_space; --no-space to skip)
    start, end                 1.8 across (draw.io's UML start and end states)
    fork bar                   0.5 thick, its measured length
    grey rules                 none: one line per divider
    phase title                bold, on a white ground where a divider runs
                               through it
    type                       actions bold, documents bold italic, lane
                               titles, decisions and guards plain; all at
                               the label size

The result is a spec like the ones spec_from_model.py writes, drawn by
drawio_from_spec.py as any other.
"""
import copy, json, os, sys
from PIL import ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import build_diagram as bd          # noqa: E402

EM = 12.0
HOUSE = dict(line=0.10, document=0.16, divider=0.11, frame=0.18, arrow=1.35, arrow_ratio=0.81,
             pad_action=(0.5, 0.4), pad_document=(0.5, 0.6), pad_decision=(1.0, 0.8),
             decision_bare=2.0, disc=1.8, fork=0.5, line_height=1.2, corner=1.3, snap=1.5,
             title=1.3)
BOLD = {"action": True, "object": True, "decision": False, "note": False}
ITALIC = {"object": True}
FONTS = "/usr/share/fonts/truetype/liberation/LiberationSans-%s.ttf"
_font = {}


def text_width(t, bold=False, italic=False, size=EM):
    """the width draw.io's Helvetica sets t in (Liberation Sans in Chromium,
    metric-compatible with Arial and close to Helvetica)"""
    k = ("Bold" if bold else "Regular") if not italic else ("BoldItalic" if bold else "Italic")
    f = _font.setdefault(k, ImageFont.truetype(FONTS % k, 100))
    return f.getlength(t) * size / 100


def label_em(spec):
    """the figure's label size: the median of its actions' and documents' lines"""
    sizes = sorted(l["size"] for n in spec["nodes"] if n["kind"] in ("action", "object")
                   for l in n.get("labelLines", []) if l.get("size"))
    return sizes[len(sizes) // 2] if sizes else spec["font"]["node"]


def scale(spec, k):
    """every coordinate and length of the spec, times k"""
    s = copy.deepcopy(spec)
    s.pop("byid", None)
    S = lambda v: v * k                                    # noqa: E731
    s["canvas"] = {"w": S(s["canvas"]["w"]), "h": S(s["canvas"]["h"])}
    if s.get("frameBox"):
        s["frameBox"] = [S(v) for v in s["frameBox"]]
    s["dividers"] = [[S(d[0]), d[1], S(d[2]), S(d[3])] if isinstance(d, list) else S(d)
                     for d in s.get("dividers", [])]
    s["bands"] = [[S(d[0]), d[1], S(d[2]), S(d[3])] if isinstance(d, list) else S(d)
                  for d in s.get("bands", [])]
    for g in s.get("greyRules", []):
        g["at"], g["w"] = S(g["at"]), S(g["w"])
    for d in s.get("dashed", []):
        for key in ("x", "y", "w", "h", "rx", "dash", "gap"):
            d[key] = S(d[key])
    for group in ("lanes", "captions", "bandLabels"):
        for t in s.get(group, []):
            for key in ("x", "w", "cx", "cy", "baseline", "textWidth", "size"):
                if t.get(key) is not None:
                    t[key] = S(t[key])
    for n in s["nodes"] + s.get("guards", []):
        for key in ("x", "y", "w", "h", "rx", "ry", "fold"):
            if n.get(key) is not None:
                n[key] = S(n[key])
        for l in n.get("labelLines", []):
            for key in ("cx", "cy", "w", "size"):
                if l.get(key) is not None:
                    l[key] = S(l[key])
    for e in s["edges"]:
        e["points"] = [[S(p[0]), S(p[1])] for p in e.get("points", [])]
        for key in ("dash", "gap", "dashOffset"):
            if e.get(key) is not None:
                e[key] = S(e[key])
    for o in s.get("openEnds", []):
        o["points"] = [[S(p[0]), S(p[1])] for p in o["points"]]
    for m in s.get("crossMarks", []):
        for key in ("x1", "y1", "x2", "y2"):
            m[key] = S(m[key])
    return s


def lines(n):
    return [l["text"] for l in n.get("labelLines", [])] or \
        [t for t in (n.get("label") or "").split("\n") if t.strip()]


def boxed(n, words, pad, bold, italic):
    """the house size of a box around its words, about the measured centre"""
    w = max((text_width(t, bold, italic) for t in words), default=0) + 2 * pad[0] * EM
    h = len(words) * HOUSE["line_height"] * EM + 2 * pad[1] * EM
    return w, h


def centred_lines(words, cx, cy, bold, italic):
    lh = HOUSE["line_height"] * EM
    top = cy - (len(words) - 1) * lh / 2
    return [{"text": t, "cx": cx, "cy": top + i * lh, "w": text_width(t, bold, italic), "size": EM}
            for i, t in enumerate(words)]


def refit(old, new, f):
    """a contact point's fraction on the old box, moved to the new one so a
    line that ran straight across or down still does: the side it lies on is
    kept, and its place along that side stays where it was on the page"""
    x = old["x"] + old["w"] * f[0]
    y = old["y"] + old["h"] * f[1]
    side = min((f[0], "l"), (1 - f[0], "r"), (f[1], "t"), (1 - f[1], "b"))[1]
    fx = min(1.0, max(0.0, (x - new["x"]) / new["w"]))
    fy = min(1.0, max(0.0, (y - new["y"]) / new["h"]))
    return {"l": (0.0, fy), "r": (1.0, fy), "t": (fx, 0.0), "b": (fx, 1.0)}[side]


def house(spec):
    k = EM / label_em(spec)
    s = scale(spec, k)
    s["stroke"] = {"frame": HOUSE["frame"] * EM, "divider": HOUSE["divider"] * EM,
                   "action": HOUSE["line"] * EM, "object": HOUSE["document"] * EM,
                   "edge": HOUSE["line"] * EM}
    s["font"] = dict(s["font"], node=EM, lane=EM, guard=EM)
    s["arrow"] = HOUSE["arrow"] * EM
    s["arrowWidth"] = HOUSE["arrow"] * HOUSE["arrow_ratio"] * EM
    s["arrowStyle"] = "open"
    s["dividers"] = [[d[0], s["stroke"]["divider"], d[2], d[3]] if isinstance(d, list) else d
                     for d in s["dividers"]]
    s["bands"] = [[d[0], s["stroke"]["divider"], d[2], d[3]] if isinstance(d, list) else d
                  for d in s["bands"]]
    # the grey rules beside a divider are one artwork's quirk (C.1); the
    # house style has one line per divider
    s["greyRules"] = []
    s["house"] = True
    for d in s.get("dashed", []):
        d["weight"] = s["stroke"]["divider"]
    top = (s.get("frameBox") or [0, 0])[1]
    for t in s["lanes"]:
        # every lane title at the same place: centred a fixed distance below
        # the frame's top, plain, at the label size
        t["cy"] = top + HOUSE["title"] * EM
        t["baseline"] = t["cy"] + 0.35 * EM
        t["size"], t["bold"] = EM, False
        t["textWidth"] = text_width(t.get("title") or "")
    # a rule under the lane titles is drawn by 7 figures (IMFM, the 2.3
    # customs figures) and not by the other 71: the house style has none. A
    # band that divides the figure further down (IMFM's planning, execution,
    # completion) stays.
    first = min(n["y"] for n in s["nodes"])
    s["bands"] = [b for b in s["bands"]
                  if not ((b[0] if isinstance(b, list) else b) < min(first, top + 4 * EM))]
    for t in s.get("captions", []):
        bold = t.get("role") == "phase-title"
        t["baseline"] = t["cy"] + 0.35 * EM
        t["size"], t["bold"] = EM, bold
        t["textWidth"] = text_width(t["text"], bold)
    old = {n["id"]: dict(n) for n in s["nodes"]}
    for n in s["nodes"]:
        k_ = n["kind"]
        cx, cy = n["x"] + n["w"] / 2, n["y"] + n["h"] / 2
        words = lines(n)
        bold, italic = BOLD.get(k_, False), ITALIC.get(k_, False)
        if k_ in ("action", "object") or (k_ == "decision" and words):
            pad = {"action": HOUSE["pad_action"], "object": HOUSE["pad_document"]}.get(k_, HOUSE["pad_decision"])
            w, h = boxed(n, words, pad, bold, italic)
            if k_ == "decision":
                w, h = w * 1.4, h * 1.4        # the words must fit inside the diamond
            # the measured size, grown only where the words would not fit
            w, h = max(w, n["w"]), max(h, n["h"])
        elif k_ == "decision":
            w = h = HOUSE["decision_bare"] * EM
        elif k_ in ("initial", "final"):
            w = h = HOUSE["disc"] * EM
            n.pop("innerRatio", None)
        elif k_ == "fork":
            t = HOUSE["fork"] * EM
            w, h = (n["w"], t) if n["w"] >= n["h"] else (t, n["h"])
        else:                                   # a note keeps its measured size
            w, h = n["w"], n["h"]
        if k_ == "object":
            # a document on a divider sits centred on it
            for d in s["dividers"]:
                at = d[0] if isinstance(d, list) else d
                if cx - w / 2 < at < cx + w / 2 and abs(cx - at) <= HOUSE["snap"] * EM:
                    cx = at
                    break
        n["x"], n["y"], n["w"], n["h"] = cx - w / 2, cy - h / 2, w, h
        if k_ == "action":
            n["rx"] = n["ry"] = min(HOUSE["corner"] * EM, h / 2)
        if words and k_ != "fork":
            n["labelLines"] = centred_lines(words, cx, cy, bold, italic)
            n["bold"], n["italic"] = bold, italic
    # a flow leaving the page keeps meeting its node: the end that lay on the
    # node's old outline moves to the same place on the new one
    new = {n["id"]: n for n in s["nodes"]}
    tol = s["arrow"]
    for o in s.get("openEnds", []):
        for k in (0, -1):
            p = o["points"][k]
            for nid, b in old.items():
                if b["x"] - tol <= p[0] <= b["x"] + b["w"] + tol and b["y"] - tol <= p[1] <= b["y"] + b["h"] + tol:
                    f = (min(1, max(0, (p[0] - b["x"]) / b["w"])), min(1, max(0, (p[1] - b["y"]) / b["h"])))
                    q = refit(b, new[nid], f)
                    nb = new[nid]
                    o["points"][k] = [nb["x"] + nb["w"] * q[0], nb["y"] + nb["h"] * q[1]]
                    # the next point along keeps the line straight across or down
                    nxt = o["points"][1 if k == 0 else -2]
                    if abs(nxt[0] - p[0]) < abs(nxt[1] - p[1]):
                        nxt[0] = o["points"][k][0]
                    else:
                        nxt[1] = o["points"][k][1]
                    break
    for e in s["edges"]:
        a, b = old[e["from"]], old[e["to"]]
        na = next(n for n in s["nodes"] if n["id"] == e["from"])
        nb = next(n for n in s["nodes"] if n["id"] == e["to"])
        e["exitXY"] = list(refit(a, na, e.get("exitXY") or bd.SIDE[e["exit"]]))
        e["entryXY"] = list(refit(b, nb, e.get("entryXY") or bd.SIDE[e["entry"]]))
        e.pop("dashOffset", None)
    for g in s.get("guards", []):
        for l in g.get("labelLines", []):
            left = l["cx"] - l["w"] / 2
            l["w"] = text_width(l["text"])
            l["size"] = EM
            l["cx"] = left + l["w"] / 2        # the words keep their left edge
        g.pop("moved", None)
    return s


def overlaps(s):
    """pairs of boxes, and guards and boxes, that now overlap: where the house
    sizes need the layout to give way"""
    boxes = [n for n in s["nodes"] if n["kind"] in ("action", "object", "decision", "note")]
    hit = lambda a, b: a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and \
        a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]          # noqa: E731
    out = [(a["id"], b["id"]) for i, a in enumerate(boxes) for b in boxes[i + 1:] if hit(a, b)]
    for g in s.get("guards", []):
        ll = g.get("labelLines") or []
        if not ll:
            continue
        box = dict(x=min(l["cx"] - l["w"] / 2 for l in ll), y=min(l["cy"] for l in ll) - EM * 0.5,
                   w=max(l["w"] for l in ll), h=(max(l["cy"] for l in ll) - min(l["cy"] for l in ll)) + EM)
        out += [(g["id"], b["id"]) for b in boxes if hit(box, b)]
    for t in s["lanes"]:
        if t.get("title"):
            box = dict(x=t["cx"] - t["textWidth"] / 2, y=t["cy"] - EM * 0.6, w=t["textWidth"], h=EM * 1.2)
            out += [(t.get("id"), b["id"]) for b in s["nodes"] if hit(box, b)]
    # a flow too short to show its arrowhead: two boxes grown up against
    # each other
    sp = dict(s, byid={n["id"]: n for n in s["nodes"]})
    for e in s["edges"]:
        pts = bd.polyline(sp, e)
        if sum(((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 for a, b in zip(pts, pts[1:])) < 1.5 * s["arrow"]:
            out.append((e["from"], e["to"]))
    return out


def align_boxes(s, tol=1.5):
    """Line boxes up with the boxes their flows connect them to, so the flows
    run straight and meet each box in the middle of its side: a document level
    with the action that sends it, an action straight under the one before it.

    For every flow almost level (the two boxes' middles within tol label sizes
    of each other, one above the other's side) or almost upright, the box with
    fewer flows moves - at most tol label sizes, only if it stays in its lane
    and clear of every other box, and only once along each axis, so the moves
    cannot undo each other. A document on a divider moves only up and down.
    Returns the number of moves."""
    byid = {n["id"]: n for n in s["nodes"]}
    deg = {}
    for e in s["edges"]:
        deg[e["from"]] = deg.get(e["from"], 0) + 1
        deg[e["to"]] = deg.get(e["to"], 0) + 1
    rules = [d[0] if isinstance(d, list) else d for d in s.get("dividers", [])]
    fb = s.get("frameBox") or [0, 0, s["canvas"]["w"], s["canvas"]["h"]]
    on_rule = {n["id"] for n in s["nodes"] if n["kind"] == "object"
               and any(n["x"] < r < n["x"] + n["w"] for r in rules)}
    locked = {"x": set(), "y": set()}
    pad = 0.5 * EM

    def clear(n, dx, dy):
        x0, y0, x1, y1 = n["x"] + dx, n["y"] + dy, n["x"] + n["w"] + dx, n["y"] + n["h"] + dy
        for o in s["nodes"]:
            if o is n:
                continue
            if x0 < o["x"] + o["w"] + pad and o["x"] < x1 + pad and y0 < o["y"] + o["h"] + pad and o["y"] < y1 + pad:
                return False
        if n["id"] not in on_rule:
            cx = (x0 + x1) / 2
            left = max([r for r in rules if r <= n["x"] + n["w"] / 2] + [fb[0]])
            right = min([r for r in rules if r > n["x"] + n["w"] / 2] + [fb[2]])
            if x0 < left + pad or x1 > right - pad or not (left < cx < right):
                return False
        return fb[1] + pad <= y0 and y1 <= fb[3] - pad

    def inside(n, dx, dy):
        """the box, moved, still in the frame and on no other box (it may come
        close: making room will then open the figure there)"""
        x0, y0, x1, y1 = n["x"] + dx, n["y"] + dy, n["x"] + n["w"] + dx, n["y"] + n["h"] + dy
        if any(o is not n and x0 < o["x"] + o["w"] and o["x"] < x1 and y0 < o["y"] + o["h"] and o["y"] < y1
               for o in s["nodes"]):
            return False
        return fb[1] + pad <= y0 and y1 <= fb[3] - pad

    def move(n, dx, dy):
        n["x"] += dx
        n["y"] += dy
        for l in n.get("labelLines", []):
            l["cx"] += dx
            l["cy"] += dy
    moves = 0
    # first, a document level with the action that sends it - the reading
    # order: action, document, next action - as far as 8 label sizes, where
    # the space there is free (Procurement's ReceiptAdvice, level with
    # "advise receipt")
    for n in s["nodes"]:
        if n["kind"] != "object":
            continue
        senders = [byid[e["from"]] for e in s["edges"] if e["to"] == n["id"] and not e.get("points")
                   and byid[e["from"]]["kind"] == "action"]
        if len(senders) != 1:
            continue
        a = senders[0]
        if abs((a["x"] + a["w"] / 2) - (n["x"] + n["w"] / 2)) < abs((a["y"] + a["h"] / 2) - (n["y"] + n["h"] / 2)):
            continue                            # sent from above or below: nothing to line up across
        dy = (a["y"] + a["h"] / 2) - (n["y"] + n["h"] / 2)
        # a box in the way here is no reason not to: making room opens the
        # figure where the move brings two things too close
        if 0.05 < abs(dy) <= 8 * EM and inside(n, 0, dy):
            move(n, 0, dy)
            locked["y"] |= {n["id"], a["id"]}
            moves += 1
            for e in s["edges"]:
                if e["to"] == n["id"] and e["from"] == a["id"]:
                    e["exitXY"] = [(e.get("exitXY") or [1, 0.5])[0], 0.5]
                    e["entryXY"] = [(e.get("entryXY") or [0, 0.5])[0], 0.5]
    for _ in range(2):
        for e in s["edges"]:
            if e.get("points"):
                continue
            A, B = byid[e["from"]], byid[e["to"]]
            ax, ay = A["x"] + A["w"] / 2, A["y"] + A["h"] / 2
            bx, by = B["x"] + B["w"] / 2, B["y"] + B["h"] / 2
            dx, dy = bx - ax, by - ay
            if abs(dx) >= abs(dy):              # a flow across: line up the middles' heights
                axis, off = "y", dy
            else:                               # a flow down: line up the middles' x
                axis, off = "x", dx
            if abs(off) < 0.05 or abs(off) > tol * EM:
                continue
            # the box with fewer flows moves; a document on a divider only up and down
            cand = sorted([(deg.get(B["id"], 0), 0, B, -off), (deg.get(A["id"], 0), 1, A, off)], key=lambda t: t[:2])
            if A["id"] in locked[axis] and B["id"] in locked[axis]:
                continue
            for _, _, n, d in cand:
                if n["id"] in locked[axis] or (axis == "x" and n["id"] in on_rule) or n["kind"] == "fork":
                    continue
                mx, my = (d, 0) if axis == "x" else (0, d)
                if clear(n, mx, my):
                    move(n, mx, my)
                    # both ends of a flow lined up stay so: a later move may
                    # line others up with them, not pull them apart
                    locked[axis] |= {A["id"], B["id"]}
                    moves += 1
                    # the flow now meets both boxes in the middle of their sides
                    fx, fy = e.get("exitXY") or [0.5, 0.5]
                    tx, ty = e.get("entryXY") or [0.5, 0.5]
                    if axis == "y":
                        e["exitXY"], e["entryXY"] = [fx, 0.5], [tx, 0.5]
                    else:
                        e["exitXY"], e["entryXY"] = [0.5, fy], [0.5, ty]
                    break
    return moves


def straighten(s, tol=0.75):
    """A flow that runs almost level or almost upright - its ends within tol
    label sizes of each other - made exactly so: 432 flows in 71 figures are
    off by a few pixels in the artwork and print slightly slanted. One end
    slides along the side of its box it meets (the target's first, else the
    source's), as far as that side reaches."""
    sp = dict(s, byid={n["id"]: n for n in s["nodes"]})
    done = 0
    for e in s["edges"]:
        if not e.get("straight") or e.get("points"):
            continue
        A, B = sp["byid"][e["from"]], sp["byid"][e["to"]]
        (x0, y0), (x1, y1) = bd.polyline(sp, e)[0], bd.polyline(sp, e)[-1]
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        if min(dx, dy) < 0.05 or min(dx, dy) > tol * EM:
            continue
        level = dx > dy                          # align y (level) or x (upright)
        fe, fx = list(e["entryXY"]), list(e["exitXY"])
        def slide(n, f, want):
            """f moved along n's side to `want`, if the side reaches it"""
            if level and f[0] in (0.0, 1.0) and n["y"] + 1 <= want <= n["y"] + n["h"] - 1:
                return [f[0], (want - n["y"]) / n["h"]]
            if not level and f[1] in (0.0, 1.0) and n["x"] + 1 <= want <= n["x"] + n["w"] - 1:
                return [(want - n["x"]) / n["w"], f[1]]
            return None
        g = slide(B, fe, y0 if level else x0)
        if g:
            e["entryXY"] = g
        else:
            g = slide(A, fx, y1 if level else x1)
            if not g:
                continue
            e["exitXY"] = g
        done += 1
    return done


def route_by_drawio(s):
    """Every flow at an angle handed to draw.io's own router, across and down,
    from the sides draw.io finds best (no fixed contact points)."""
    sp = dict(s, byid={n["id"]: n for n in s["nodes"]})
    n = 0
    for e in s["edges"]:
        pts = bd.polyline(sp, e)
        if e.get("straight") and not all(abs(a[0] - b[0]) < 2 or abs(a[1] - b[1]) < 2
                                          for a, b in zip(pts, pts[1:])):
            e["autoRoute"] = True
            n += 1
    return n


def route_right_angles(s):
    """Every flow at an angle re-routed across and down: an L or a Z between
    the same contact points, on the same sides (build_diagram.polyline routes
    a flow that is not 'straight' so). A flow already straight across or
    down stays as it is; a flow already bent keeps its bends."""
    sp = dict(s, byid={n["id"]: n for n in s["nodes"]})
    n = 0
    for e in s["edges"]:
        if not e.get("straight"):
            continue
        pts = bd.polyline(sp, e)
        if all(abs(a[0] - b[0]) < 2 or abs(a[1] - b[1]) < 2 for a, b in zip(pts, pts[1:])):
            continue
        e["straight"] = False
        e["points"] = []
        n += 1
    return n


# ---- making space -------------------------------------------------------

def _stretch(s, axis, cut, d):
    """Open the figure by d at `cut` along one axis: everything beyond the cut
    moves on by d. A box moves whole (by its centre); a lane, a band, the
    frame, a phase box widens where it spans the cut; lines and points move
    point by point. So rows and columns stay aligned, and lanes grow."""
    X = axis == "x"
    i0 = 0 if X else 1
    mv = lambda v: v + d if v > cut else v                      # noqa: E731
    def box(o, kx, kw):
        c = o[kx] + o[kw] / 2
        if c > cut:
            o[kx] += d
            for l in o.get("labelLines", []):
                l["cx" if X else "cy"] += d
            return True
        return False
    def span(o, kx, kw):
        a, b = o[kx], o[kx] + o[kw]
        o[kx], o[kw] = mv(a), mv(b) - mv(a)
    s["canvas"]["w" if X else "h"] += d
    if s.get("frameBox"):
        fb = s["frameBox"]
        fb[2 if X else 3] = mv(fb[2 if X else 3])
    for n in s["nodes"] + s.get("guards", []):
        box(n, "x" if X else "y", "w" if X else "h")
    for l in s["lanes"]:
        if X:
            span(l, "x", "w")
            l["cx"] = l["x"] + l["w"] / 2
        else:
            pass                                # titles stay under the top
    for dv in s.get("dividers", []):            # vertical rules: at x, from y to y
        if X:
            dv[0] = mv(dv[0])
        else:
            dv[2], dv[3] = mv(dv[2]), mv(dv[3])
    for b in s.get("bands", []):                # horizontal rules: at y, from x to x
        if X:
            b[2], b[3] = mv(b[2]), mv(b[3])
        else:
            b[0] = mv(b[0])
    for p in s.get("dashed", []):
        span(p, "x" if X else "y", "w" if X else "h")
    for c in s.get("captions", []) + s.get("bandLabels", []):
        k = "cx" if X else "cy"
        c[k] = mv(c[k])
        if not X and c.get("baseline") is not None:
            c["baseline"] = mv(c["baseline"])
    for e in s["edges"]:
        e["points"] = [[mv(p[0]), p[1]] if X else [p[0], mv(p[1])] for p in e.get("points", [])]
    for o in s.get("openEnds", []):
        o["points"] = [[mv(p[0]), p[1]] if X else [p[0], mv(p[1])] for p in o["points"]]
    for m in s.get("crossMarks", []):
        for k in (("x1", "x2") if X else ("y1", "y2")):
            m[k] = mv(m[k])


def _items(s):
    """what must keep its distance: boxes, discs, bars and notes; guards (as
    the box of their words); lane titles, which stay at the top"""
    out = [dict(id=n["id"], x=n["x"], y=n["y"], w=n["w"], h=n["h"], kind=n["kind"]) for n in s["nodes"]]
    for g in s.get("guards", []):
        ll = g.get("labelLines") or []
        if ll:
            x0 = min(l["cx"] - l["w"] / 2 for l in ll)
            y0 = min(l["cy"] for l in ll) - EM * 0.6
            out.append(dict(id=g["id"], x=x0, y=y0, w=max(l["cx"] + l["w"] / 2 for l in ll) - x0,
                            h=max(l["cy"] for l in ll) + EM * 0.6 - y0, kind="guard", flow=g.get("onFlow")))
    for t in s["lanes"]:
        if t.get("title"):
            out.append(dict(id=t.get("id"), x=t["cx"] - t["textWidth"] / 2, y=t["cy"] - EM * 0.7,
                            w=t["textWidth"], h=EM * 1.4, kind="title"))
    return out


def conflicts(s):
    """Where two things are too close, as (axis, cut, how much more room, what):
    a flow too short for its arrowhead, boxes, guards or titles touching."""
    it = _items(s)
    sp = dict(s, byid={n["id"]: n for n in s["nodes"]})
    flows = {}
    for e in s["edges"]:
        flows.setdefault(frozenset((e["from"], e["to"])), e)
    need_flow = 1.5 * s["arrow"] + 0.5 * EM
    gap = {"guard": 0.3 * EM, "title": 0.5 * EM}
    out = []
    for i, a in enumerate(it):
        for b in it[i + 1:]:
            if a["kind"] == "title" and b["kind"] == "title":
                continue
            if "guard" in (a["kind"], b["kind"]) and a["kind"] == b["kind"]:
                continue
            ov_x = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
            ov_y = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
            e = flows.get(frozenset((a["id"], b["id"])))
            need = need_flow if e else max(gap.get(a["kind"], 0.5 * EM), gap.get(b["kind"], 0.5 * EM))
            if not e and (ov_x <= 0 and ov_y <= 0):
                continue                          # side by side at a slant: nothing between them
            # the axis along which they face each other, or along which the
            # flow between them mostly runs
            if e:
                # the way the flow between them runs, end to end
                p0, p1 = bd.polyline(sp, e)[0], bd.polyline(sp, e)[-1]
                ax = "x" if abs(p1[0] - p0[0]) >= abs(p1[1] - p0[1]) else "y"
            elif ov_x > 0 and ov_y > 0:
                ax = "x" if ov_x < ov_y else "y"
            else:
                ax = "x" if ov_y > 0 else "y"
            if "title" in (a["kind"], b["kind"]):
                ax = "y"                          # titles stay where they are; things below move down
            if ax == "x":
                l, r = (a, b) if a["x"] + a["w"] / 2 <= b["x"] + b["w"] / 2 else (b, a)
                g = r["x"] - (l["x"] + l["w"])
                if g < need - 0.5:
                    cut = (l["x"] + l["w"] / 2 + r["x"] + r["w"] / 2) / 2 if g < 0 else l["x"] + l["w"] + g / 2
                    out.append(("x", cut, need - g, a["id"], b["id"]))
            else:
                t, u = (a, b) if (a["kind"] == "title" or a["y"] + a["h"] / 2 <= b["y"] + b["h"] / 2) \
                    and b["kind"] != "title" else (b, a)
                g = u["y"] - (t["y"] + t["h"])
                if g < need - 0.5:
                    cut = (t["y"] + t["h"] / 2 + u["y"] + u["h"] / 2) / 2 if g < 0 else t["y"] + t["h"] + g / 2
                    if t["kind"] == "title":
                        cut = t["y"] + t["h"] / 2
                    out.append(("y", cut, need - g, a["id"], b["id"]))
    # every box inside its lane and the frame: a box grown past a divider or
    # the frame pushes it outward (a document on a divider belongs to both
    # lanes and is left alone)
    fb = s.get("frameBox") or [0, 0, s["canvas"]["w"], s["canvas"]["h"]]
    rules = [d[0] if isinstance(d, list) else d for d in s.get("dividers", [])]
    m = 0.5 * EM
    for n in s["nodes"]:
        x0, x1, cx = n["x"], n["x"] + n["w"], n["x"] + n["w"] / 2
        if n["kind"] == "object" and any(x0 < r < x1 for r in rules):
            continue
        left = max([r for r in rules if r <= cx] + [fb[0]])
        right = min([r for r in rules if r > cx] + [fb[2]])
        if x0 < left + m:
            out.append(("x", (left + cx) / 2, left + m - x0, n["id"], "lane edge"))
        if x1 > right - m:
            out.append(("x", (cx + right) / 2, x1 - (right - m), n["id"], "lane edge"))
        if n["y"] + n["h"] > fb[3] - m:
            out.append(("y", (n["y"] + n["h"] / 2 + fb[3]) / 2, n["y"] + n["h"] - (fb[3] - m), n["id"], "frame"))
    return out


def make_space(s, limit=300):
    """Open the figure where things are too close, one cut at a time, the
    largest first, until nothing is: each cut only moves things apart, so it
    ends. Returns the cuts made."""
    made = []
    stuck = set()
    for _ in range(limit):
        c = [t for t in conflicts(s) if (t[0], t[3], t[4]) not in stuck]
        if not c:
            break
        ax, cut, d, a, b = max(c, key=lambda t: t[2])
        # an opening that moves only one of the two apart: two things whose
        # middles coincide cannot be parted by a line between them; left be
        pos = {n["id"]: n for n in s["nodes"]}
        k, kw = ("x", "w") if ax == "x" else ("y", "h")
        ends = [pos[i][k] + pos[i][kw] / 2 for i in (a, b) if i in pos]
        if len(ends) == 2 and (ends[0] > cut) == (ends[1] > cut):
            stuck.add((ax, a, b))
            continue
        _stretch(s, ax, cut, d)
        made.append((ax, round(cut), round(d, 1), a, b))
    return made


def main(src, out, *opts):
    spec = bd.load(src)
    bd.clear_guards(spec)
    s = house(spec)
    aligned = align_boxes(s) if "--no-align" not in opts else 0
    straight = straighten(s)
    routed = route_right_angles(s) if "--right-angles" in opts else \
        route_by_drawio(s) if "--drawio-routing" in opts else 0
    before = (s["canvas"]["w"], s["canvas"]["h"])
    made = make_space(s) if "--no-space" not in opts else []
    # opening a row or a column can put two lined-up boxes a little out of
    # line again; straighten once more
    straight += straighten(s)
    if "--avoid" in opts:
        import router
        routed, placed = router.route_libavoid(s, EM)
        print("  routed with libavoid: %d flows anew; %d guards placed anew" % (routed, placed))
    if "--route" in opts:
        import router
        routed, asked, placed = router.route_figure(s, EM, "all" if "--route-all" in opts else "angled")
        print("  routed %d of %d flows across and down; %d guards placed anew" % (routed, asked, placed))
    json.dump(s, open(out, "w", encoding="utf-8"), indent=1)
    left = conflicts(s)
    print("  %s: scale %.2f, %.0f x %.0f px%s; %d flows re-routed; %d cuts made (+%.0f x +%.0f px); %d conflicts left%s"
          % (os.path.basename(out), EM / label_em(spec), s["canvas"]["w"], s["canvas"]["h"], ", %d boxes aligned, %d flows straightened" % (aligned, straight),
             routed, len(made), s["canvas"]["w"] - before[0], s["canvas"]["h"] - before[1], len(left),
             "".join("\n    %s %s / %s" % (c[0], c[3], c[4]) for c in left)))


if __name__ == "__main__":
    main(*sys.argv[1:])
