#!/usr/bin/env python3
"""A figure's spec in a house style: one look for the same element everywhere.

    python3 house_style.py <spec.json> <out-spec.json> [--avoid] [--no-grid] [--no-space]
                           [--right-angles | --drawio-routing]

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
    grid                       boxes joined across in rows, boxes one above
                               the other in a lane in columns, a lane's
                               columns evenly spaced (grid; --no-grid for
                               the smaller step of align_boxes)
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



def _ink(o):
    """the box of a node, or of a text's words"""
    if "w" in o and "h" in o and "x" in o and not o.get("labelLines") or o.get("kind"):
        return o["x"], o["y"], o["x"] + o["w"], o["y"] + o["h"]
    ll = o["labelLines"]
    return (min(l["cx"] - l["w"] / 2 for l in ll), min(l["cy"] for l in ll) - 0.6 * EM,
            max(l["cx"] + l["w"] / 2 for l in ll), max(l["cy"] for l in ll) + 0.6 * EM)


def phase_contents(s):
    """what each phase box holds, by id: so that it goes on holding it"""
    out = []
    for p in s.get("dashed", []):
        inn = [o["id"] for o in s["nodes"] + [g for g in s.get("guards", []) if g.get("labelLines")]
               if p["x"] <= _ink(o)[0] and _ink(o)[2] <= p["x"] + p["w"]
               and p["y"] <= _ink(o)[1] and _ink(o)[3] <= p["y"] + p["h"]]
        out.append(inn)
    return out


def hold_phases(s, held):
    """each phase box grown round what it held, a label size clear"""
    every = {o["id"]: o for o in s["nodes"] + s.get("guards", [])}
    for p, inn in zip(s.get("dashed", []), held):
        for i in inn:
            if i not in every:
                continue
            x0, y0, x1, y1 = _ink(every[i])
            if x0 - EM < p["x"]:
                p["w"] += p["x"] - (x0 - EM)
                p["x"] = x0 - EM
            if y0 - EM < p["y"]:
                p["h"] += p["y"] - (y0 - EM)
                p["y"] = y0 - EM
            p["w"] = max(p["w"], x1 + EM - p["x"])
            p["h"] = max(p["h"], y1 + EM - p["y"])


def _monotone(pairs):
    """a map from old to new positions, through the (old, new) pairs of the
    boxes, made monotone: for what is not a box - the frame, dividers, phase
    boxes, captions - so that it keeps its place among the boxes"""
    pairs = sorted(pairs)
    xs, ys, top = [], [], None
    for o, n in pairs:
        top = n if top is None else max(top, n - 0.0)
        if xs and o - xs[-1] < 0.5:
            ys[-1] = max(ys[-1], top)
            continue
        xs.append(o)
        ys.append(top)

    def f(v):
        if not xs:
            return v
        if v <= xs[0]:
            return v + ys[0] - xs[0]
        if v >= xs[-1]:
            return v + ys[-1] - xs[-1]
        for i in range(1, len(xs)):
            if v <= xs[i]:
                t = (v - xs[i - 1]) / (xs[i] - xs[i - 1])
                return ys[i - 1] + t * (ys[i] - ys[i - 1])
        return v
    return f


def _shift_rest(s, axis, old):
    """after boxes have moved along one axis (old: id -> old centre), move
    what hangs on them: flows' bends (kept where both ends moved alike, else
    dropped for the router), guards with their flow, off-page flows with their
    box; and map the rest (frame, dividers, phase boxes, captions) through the
    boxes' monotone map"""
    X = axis == "x"
    k, kw = ("x", "w") if X else ("y", "h")
    byid = {n["id"]: n for n in s["nodes"]}
    d = {i: byid[i][k] + byid[i][kw] / 2 - c for i, c in old.items()}
    f = _monotone([(c, byid[i][k] + byid[i][kw] / 2) for i, c in old.items()])
    for e in s["edges"]:
        a, b = d.get(e["from"], 0), d.get(e["to"], 0)
        if e.get("points"):
            if abs(a - b) < 0.5:
                for p in e["points"]:
                    p[0 if X else 1] += a
            else:
                e["points"] = []
    eby = {e.get("id"): e for e in s["edges"]}
    for g in s.get("guards", []):
        e = eby.get(g.get("onFlow"))
        if e is not None:
            m = (d.get(e["from"], 0) + d.get(e["to"], 0)) / 2
        elif g.get("near") in d:
            m = d[g["near"]]                     # a question beside its decision
        else:
            continue
        for l in g.get("labelLines", []):
            l["cx" if X else "cy"] += m
            if not X and l.get("baseline") is not None:
                l["baseline"] += m
        for key in ("x", "cx") if X else ("y", "cy", "baseline"):
            if g.get(key) is not None and isinstance(g[key], (int, float)):
                g[key] += m
    fb = s.get("frameBox")
    for o in s.get("openEnds", []):
        # an off-page flow goes with the box it starts or ends at; its other
        # end stays at the frame's edge, where it was
        m = d.get(o.get("near"), 0)
        if not m:
            continue
        free = o["points"][-1 if o.get("nearEnd", 0) == 0 else 0]
        at_edge = fb and any(abs(free[i] - fb[j]) < 3 for i, j in ((0, 0), (0, 2), (1, 1), (1, 3)) if i == (0 if X else 1))
        keep = list(free)
        o["points"] = [[p[0] + m, p[1]] if X else [p[0], p[1] + m] for p in o["points"]]
        if at_edge:
            j = -1 if o.get("nearEnd", 0) == 0 else 0
            o["points"][j][0 if X else 1] = keep[0 if X else 1]
    if X:
        return
    for p in s.get("dashed", []):
        a, b = p[k], p[k] + p[kw]
        p[k], p[kw] = f(a), f(b) - f(a)
    for c in s.get("captions", []) + s.get("bandLabels", []):
        kk = "cx" if X else "cy"
        m = f(c[kk]) - c[kk]
        c[kk] += m
        if not X and c.get("baseline") is not None:
            c["baseline"] += m
    for b in s.get("bands", []):
        b[0] = f(b[0])
    for m in s.get("crossMarks", []):
        m["y1"], m["y2"] = f(m["y1"]), f(m["y2"])


def grid(s):
    """Boxes on a grid: rows and columns, the columns of a lane evenly spaced.

    Columns: in each lane, boxes one above the other - joined by a flow down,
    or overlapping across - are stacked in one column, as long as none of
    them overlaps another up and down (Procurement's reject order, change
    order and cancel order, in the Seller's lane). The columns of a lane are
    then spaced evenly, with the same gap between them and at the lane's
    edges, clear of the documents on its dividers; the lane is widened where
    they would not fit with at least 3 label sizes between.

    Rows: boxes joined by a flow across - a document, the action that sends
    it and the action that receives it - are put level with each other, as
    long as none of them overlaps another across (the decision if item(s)
    rejected, level with the ReceiptAdvice it receives). Each row keeps the
    order of the boxes above and below it, at least a flow's length apart:
    the figure grows down where a row needs room.

    Returns (columns, rows) of more than one box."""
    byid = {n["id"]: n for n in s["nodes"]}
    # a text that is on no flow (a decision's question) goes with the box
    # nearest to it
    for g in s.get("guards", []):
        if not g.get("onFlow") and g.get("labelLines"):
            p = (sum(l["cx"] for l in g["labelLines"]) / len(g["labelLines"]),
                 sum(l["cy"] for l in g["labelLines"]) / len(g["labelLines"]))
            dist = lambda n: max(n["x"] - p[0], p[0] - n["x"] - n["w"], 0) + max(n["y"] - p[1], p[1] - n["y"] - n["h"], 0)  # noqa: E731
            near = min(s["nodes"], key=dist)
            # a question goes with its decision, when one is close by
            dec = [n for n in s["nodes"] if n["kind"] == "decision"]
            if dec:
                d = min(dec, key=dist)
                if dist(d) <= dist(near) + 6 * EM:
                    near = d
            g["near"] = near["id"]
    for o in s.get("openEnds", []):
        # the box an off-page flow starts or ends at: the one nearest its ends
        dist = lambda n, p: max(n["x"] - p[0], p[0] - n["x"] - n["w"], 0) + max(n["y"] - p[1], p[1] - n["y"] - n["h"], 0)  # noqa: E731
        best = min(((dist(n, p), k, n["id"]) for n in s["nodes"] for k, p in ((0, o["points"][0]), (1, o["points"][-1]))))
        o["near"], o["nearEnd"] = best[2], best[1]
    if not s.get("frameBox"):
        s["frameBox"] = [0, 0, s["canvas"]["w"], s["canvas"]["h"]]
    fb = s["frameBox"]
    need = 1.5 * s["arrow"] + 0.5 * EM
    need_at = lambda a, b: need_decision(s) if "decision" in (a["kind"], b["kind"]) else need   # noqa: E731
    gap_min = 3 * EM                             # between columns, at the least
    gap_row = 1.5 * EM                           # between boxes one above the other, not joined
    pad = 0.5 * EM
    cx = lambda n: n["x"] + n["w"] / 2           # noqa: E731
    cy = lambda n: n["y"] + n["h"] / 2           # noqa: E731
    wide_bar = lambda n: n["kind"] == "fork" and n["w"] > n["h"] and n["w"] > 4 * EM   # noqa: E731
    flat_bar = lambda n: n["kind"] == "fork" and n["w"] > n["h"]                       # noqa: E731

    def rules():
        return sorted(d[0] if isinstance(d, list) else d for d in s.get("dividers", []))

    def on_rule():
        return {n["id"] for n in s["nodes"] if n["kind"] == "object"
                and any(n["x"] < r < n["x"] + n["w"] for r in rules())}

    def spans(n, other, axis, p=pad):
        k, kw = ("x", "w") if axis == "x" else ("y", "h")
        return n[k] - p < other[k] + other[kw] and other[k] - p < n[k] + n[kw]

    # flows by the way they leave and meet their boxes, as drawn: from a side
    # to a side runs across, from a top or bottom to a top or bottom runs down,
    # and one that turns a corner is neither (it keeps its boxes in order)
    sp = dict(s, byid=byid)

    def side(n, p, q):
        """'h' where p lies on a left or right side (or corner) of n, else 'v';
        at a box's corner, the way the flow goes on to q"""
        if n["kind"] == "decision":
            return "h" if abs(p[1] - cy(n)) < abs(p[0] - cx(n)) * n["h"] / n["w"] else "v"
        dx = min(abs(p[0] - n["x"]), abs(p[0] - n["x"] - n["w"]))
        dy = min(abs(p[1] - n["y"]), abs(p[1] - n["y"] - n["h"]))
        if dx < 1.5 and dy < 1.5:
            return "h" if abs(q[0] - p[0]) >= abs(q[1] - p[1]) else "v"
        return "h" if dx < dy else "v"
    ways = {}
    for e in s["edges"]:
        A, B = byid[e["from"]], byid[e["to"]]
        pts = bd.polyline(sp, e)
        a, b = side(A, pts[0], pts[1]), side(B, pts[-1], pts[-2])
        if flat_bar(A) or flat_bar(B):
            ways[id(e)] = "down"
        elif a == b == "h":
            ways[id(e)] = "across"
        elif a == b == "v":
            ways[id(e)] = "down"
        else:
            ways[id(e)] = "corner"
    way = lambda e: ways[id(e)]                  # noqa: E731
    flows = [e for e in s["edges"] if e["from"] != e["to"]]

    def union(items, pairs, ok, check_all=None):
        grp = {i: [i] for i in items}
        for _, a, b in sorted(pairs):
            if grp[a] is grp[b]:
                continue
            if not ok(grp[a], grp[b]):
                continue
            if check_all is not None:
                gs = []
                for g in grp.values():
                    if not any(g is o for o in gs) and g is not grp[a] and g is not grp[b]:
                        gs.append(g)
                if not check_all(gs + [grp[a] + grp[b]]):
                    continue
            m = grp[a] + grp[b]
            for i in m:
                grp[i] = m
        out = []
        for g in grp.values():
            if not any(g is o for o in out):
                out.append(g)
        return out

    # ---- columns, lane by lane
    ncols = 0
    lanes_done = 0
    while True:
        rs = rules()
        edges = [fb[0]] + rs + [fb[2]]
        if lanes_done >= len(edges) - 1:
            break
        L0, R0 = edges[lanes_done], edges[lanes_done + 1]
        onr = on_rule()
        mem = [n["id"] for n in s["nodes"] if n["id"] not in onr and L0 < cx(n) < R0 and not wide_bar(n)
               and not any(n["x"] < r < n["x"] + n["w"] for r in rs)]
        if not mem:
            lanes_done += 1
            continue
        pairs = []
        mset = set(mem)
        for e in flows:
            a, b = e["from"], e["to"]
            if a in mset and b in mset and way(e) == "down":
                pairs.append(((0, abs(cx(byid[a]) - cx(byid[b]))), a, b))
        for i, a in enumerate(mem):
            for b in mem[i + 1:]:
                if spans(byid[a], byid[b], "x", 0):
                    pairs.append(((1, abs(cx(byid[a]) - cx(byid[b]))), a, b))

        # every flow between two boxes of a column (not only one down it):
        # a box between them sends it round
        down = [(e["from"], e["to"]) for e in flows]
        # an off-page flow leaving a box up or down: nothing stacked in its way
        off = []
        for o in s.get("openEnds", []):
            pts = o["points"] if o.get("nearEnd", 0) == 0 else o["points"][::-1]
            if o.get("near") in mset and len(pts) >= 2 and abs(pts[1][0] - pts[0][0]) < 1:
                off.append((o["near"], pts[1][1]))

        def col_ok(g1, g2):
            if any(spans(byid[a], byid[b], "y") for a in g1 for b in g2):
                return False
            # nothing in the column between two boxes joined down it
            m = set(g1) | set(g2)
            for a, b in down:
                if a in m and b in m:
                    lo, hi = sorted((cy(byid[a]), cy(byid[b])))
                    if any(lo < cy(byid[c]) < hi for c in m if c not in (a, b)):
                        return False
            for a, y in off:
                if a in m:
                    lo, hi = sorted((cy(byid[a]), y))
                    if any(lo < cy(byid[c]) < hi for c in m if c != a):
                        return False
            return True
        # a decision (or fork) with two branches down its column: the branch
        # that goes further down continues the column, and the nearer one,
        # which would stand in its way, steps aside - to the side its own
        # flows go (GoodsItemPassportApproval: Valid? above Apply Stamps,
        # Send Reject beside, towards its document)
        apart, evicted = set(), {}
        plain_ok = col_ok

        def col_ok(g1, g2):
            if any(frozenset((a, b)) in apart for a in g1 for b in g2):
                return False
            return plain_ok(g1, g2)
        for _ in range(4):
            cols = union(mem, pairs, col_ok)
            gc = {i: k for k, g in enumerate(cols) for i in g}
            new = False
            for a in mem:
                if byid[a]["kind"] not in ("decision", "fork"):
                    continue
                outs = [e["to"] for e in flows if e["from"] == a and e["to"] in mset]
                for b in outs:
                    for c in outs:
                        if b == c or gc[b] != gc[a] or gc[c] == gc[a] or b in evicted:
                            continue
                        if cy(byid[a]) < cy(byid[b]) < cy(byid[c]) and spans(byid[c], byid[a], "x", 0):
                            apart.add(frozenset((a, b)))
                            evicted[b] = a
                            new = True
            if not new:
                break
        cols.sort(key=lambda g: sum(cx(byid[i]) for i in g) / len(g))
        for b, a in evicted.items():
            cb = next(g for g in cols if b in g)
            ca = next(g for g in cols if a in g)
            if cb is ca:
                continue
            others = [cx(byid[e["to"] if e["from"] in cb else e["from"]]) for e in s["edges"]
                      if (e["from"] in cb) != (e["to"] in cb) and a not in (e["from"], e["to"])]
            if not others:
                continue
            side = sum(others) / len(others) - cx(byid[a])
            cols.remove(cb)
            k = cols.index(ca)
            cols.insert(k + 1 if side > 0 else k, cb)
        ncols += sum(1 for g in cols if len(g) > 1)
        # the lane's room for its columns: clear of the documents on its dividers
        half = lambda r: max([byid[i]["w"] / 2 for i in onr if byid[i]["x"] < r < byid[i]["x"] + byid[i]["w"]] + [0])  # noqa: E731
        L = L0 + (half(L0) if L0 in rs else 0)
        R = R0 - (half(R0) if R0 in rs else 0)
        widths = [max(byid[i]["w"] for i in g) for g in cols]
        want = sum(widths) + (len(cols) + 1) * gap_min
        if R - L < want - 0.5:
            _stretch(s, "x", R0 - 0.01, want - (R - L))
            continue                                   # this lane again, now wide enough
        g = (R - L - sum(widths)) / (len(cols) + 1)
        old = {i: cx(byid[i]) for i in mem}
        at = L + g
        for grp, w in zip(cols, widths):
            c = at + w / 2
            for i in grp:
                n = byid[i]
                dx = c - cx(n)
                n["x"] += dx
                for l in n.get("labelLines", []):
                    l["cx"] += dx
            at += w + g
        _shift_rest(s, "x", old)
        lanes_done += 1
    # flows down a column meet both boxes in the middle
    for e in flows:
        A, B = byid[e["from"]], byid[e["to"]]
        if way(e) == "down" and abs(cx(A) - cx(B)) < 0.5 and not e.get("points"):
            e["exitXY"] = [0.5, (e.get("exitXY") or [0.5, 1])[1]]
            e["entryXY"] = [0.5, (e.get("entryXY") or [0.5, 0])[1]]
    # ---- rows, over the whole figure
    old = {n["id"]: cy(n) for n in s["nodes"]}
    band_rules = sorted(b[0] for b in s.get("bands", []))
    band_old = {id(b): b[0] for b in s.get("bands", [])}
    band_label_old = {id(c): c["cy"] for c in s.get("bandLabels", [])}
    band = lambda n: sum(1 for r in band_rules if r < cy(n))     # noqa: E731
    # a box the artwork draws across a band's rule belongs to neither band
    astride = {n["id"] for n in s["nodes"] if any(n["y"] < r < n["y"] + n["h"] for r in band_rules)}
    # a box much taller than the one it is joined to across (IMFM's actions,
    # with a document beside them at every flow) is not lined up with it by
    # the middle: the flow meets it level, where along its side it can
    tall = lambda a, b: "decision" not in (a["kind"], b["kind"]) and max(a["h"], b["h"]) > 3 * EM and max(a["h"], b["h"]) > 1.8 * min(a["h"], b["h"])  # noqa: E731
    pairs = [(abs(cy(byid[e["to"]]) - cy(byid[e["from"]])), e["from"], e["to"]) for e in flows
             if way(e) == "across" and not wide_bar(byid[e["from"]]) and not wide_bar(byid[e["to"]])
             and not tall(byid[e["from"]], byid[e["to"]])]

    across = [(e["from"], e["to"]) for e in flows if way(e) == "across"]
    joined_any = [(e["from"], e["to"]) for e in flows]

    # what must stay above what, box by box (as below, for the rows): a merge
    # of two rows that would put a row both above and below another is refused
    kinds = {}
    for e in flows:
        kinds[frozenset((e["from"], e["to"]))] = way(e)
    order = []
    nl = s["nodes"]
    for i, a in enumerate(nl):
        for b in nl[i + 1:]:
            j = kinds.get(frozenset((a["id"], b["id"])))
            if (spans(a, b, "x") or j == "down" or (band(a) != band(b) and a["id"] not in astride
                                                    and b["id"] not in astride)) and abs(cy(a) - cy(b)) >= 0.5:
                order.append((a["id"], b["id"]) if cy(a) < cy(b) else (b["id"], a["id"]))

    def acyclic(groups):
        rep = {i: k for k, g in enumerate(groups) for i in g}
        nxt = {}
        for a, b in order:
            if rep[a] == rep[b]:
                return False                    # two boxes that must be one above the other, in one row
            nxt.setdefault(rep[a], set()).add(rep[b])
        state = {}

        def visit(k):
            state[k] = 1
            for m in nxt.get(k, ()):
                if state.get(m) == 1 or (m not in state and not visit(m)):
                    return False
            state[k] = 2
            return True
        return all(visit(k) for k in list(nxt) if k not in state)

    def row_ok(g1, g2):
        if band(byid[g1[0]]) != band(byid[g2[0]]):
            return False
        if any(spans(byid[a], byid[b], "x") for a in g1 for b in g2):
            return False
        # nothing in the row between two boxes joined across: the flow
        # between them would have to go round it
        m = set(g1) | set(g2)
        for a, b in joined_any:
            if a in m and b in m:
                lo, hi = sorted((cx(byid[a]), cx(byid[b])))
                if any(lo < cx(byid[c]) < hi for c in m if c not in (a, b)):
                    return False
        return True
    rows = union([n["id"] for n in s["nodes"]], pairs, row_ok, acyclic)
    gid = {i: k for k, g in enumerate(rows) for i in g}
    desired = [sum(old[i] for i in g) / len(g) for g in rows]
    # what must stay above what, and how far apart (centre to centre)
    joined = {}
    for e in flows:
        joined[frozenset((e["from"], e["to"]))] = way(e)
    above = {}
    nodes = list(s["nodes"])
    # a flow across a row keeps clear of the boxes of other rows, as a box
    # would: the stretch between its two boxes, as a box of no height
    for a, b in across:
        if gid[a] == gid[b]:
            l, r = sorted((byid[a], byid[b]), key=cx)
            i = "flow %s %s" % (a, b)
            byid[i] = dict(id=i, x=l["x"] + l["w"], y=cy(l), w=max(0, r["x"] - l["x"] - l["w"]), h=0, kind="flow")
            gid[i] = gid[a]
            old[i] = old[a]
            nodes.append(byid[i])
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            ga, gb = gid[a["id"]], gid[b["id"]]
            if ga == gb:
                continue
            j = joined.get(frozenset((a["id"], b["id"])))
            other_band = a["kind"] != "flow" and b["kind"] != "flow" and band(a) != band(b) \
                and a["id"] not in astride and b["id"] not in astride
            if not (spans(a, b, "x") or j == "down" or other_band):
                continue
            if abs(old[a["id"]] - old[b["id"]]) < 0.5:
                continue
            t, u = (a, b) if old[a["id"]] < old[b["id"]] else (b, a)
            d = t["h"] / 2 + u["h"] / 2 + ((need_at(t, u)) if j else gap_row)
            if other_band:
                d = max(d, t["h"] / 2 + u["h"] / 2 + 2 * EM)     # room for the band's rule between
            key = (gid[t["id"]], gid[u["id"]])
            above[key] = max(above.get(key, 0), d)
    # the lane titles stay at the top: nothing moves up into them
    tb = max([t["cy"] + 0.7 * EM + pad for t in s["lanes"] if t.get("title")] + [fb[1] + pad])
    floor = [max(byid[i]["h"] / 2 + min(tb, byid[i]["y"]) for i in g) for g in rows]
    # rows placed top-down, in order of what must be above what (ties: where
    # they want to be); a cycle is broken at the row that wants to be highest
    preds = {k: [] for k in range(len(rows))}
    for (a, b), d in above.items():
        preds[b].append((a, d))
    y = {}
    todo = set(range(len(rows)))
    while todo:
        ready = [k for k in todo if all(a in y or a == k for a, _ in preds[k])]
        k = min(ready or todo, key=lambda k: desired[k])
        y[k] = max([desired[k], floor[k]] + [y[a] + d for a, d in preds[k] if a in y])
        todo.discard(k)
    for i in [i for i in byid if i.startswith("flow ")]:
        del byid[i], old[i]
    nodes = s["nodes"]
    for k, g in enumerate(rows):
        for i in g:
            n = byid[i]
            dy = y[k] - cy(n)
            n["y"] += dy
            for l in n.get("labelLines", []):
                l["cy"] += dy
                if l.get("baseline") is not None:
                    l["baseline"] += dy
    for e in flows:
        A, B = byid[e["from"]], byid[e["to"]]
        if way(e) == "across" and gid[A["id"]] == gid[B["id"]] and not e.get("points"):
            e["exitXY"] = [(e.get("exitXY") or [1, 0.5])[0], 0.5]
            e["entryXY"] = [(e.get("entryXY") or [0, 0.5])[0], 0.5]
    # the frame, dividers and canvas grow with the lowest box
    low = max(n["y"] + n["h"] for n in nodes) + pad
    if low > fb[3]:
        grow = low - fb[3]
        s["canvas"]["h"] += grow
        fb[3] = low
        for dv in s.get("dividers", []):
            dv[3] += grow
    _shift_rest(s, "y", old)
    # a band's rule between the rows above and below it, its title in the
    # middle of the band
    for b in s.get("bands", []):
        r = band_old[id(b)]
        up = [n["y"] + n["h"] for n in nodes if old[n["id"]] < r and n["id"] not in astride]
        dn = [n["y"] for n in nodes if old[n["id"]] > r and n["id"] not in astride]
        if up and dn and max(up) < min(dn):
            b[0] = (max(up) + min(dn)) / 2
    rs = sorted([fb[1]] + [b[0] for b in s.get("bands", [])] + [fb[3]])
    for c in s.get("bandLabels", []):
        k = sum(1 for r in sorted(band_old.values()) if r < band_label_old[id(c)])
        c["cy"] = (rs[k] + rs[k + 1]) / 2
    # a flow across between boxes not lined up by their middles (a tall box
    # and a document beside it) meets the taller level with the other's middle
    for e in flows:
        A, B = byid[e["from"]], byid[e["to"]]
        if way(e) != "across" or gid[A["id"]] == gid[B["id"]] or e.get("points"):
            continue
        big, small, key = (A, B, "exitXY") if A["h"] > B["h"] else (B, A, "entryXY")
        if big["y"] + 0.5 * EM <= cy(small) <= big["y"] + big["h"] - 0.5 * EM:
            f = e.get(key) or [0.5, 0.5]
            e[key] = [f[0], (cy(small) - big["y"]) / big["h"]]
            k2 = "entryXY" if key == "exitXY" else "exitXY"
            e[k2] = [(e.get(k2) or [0.5, 0.5])[0], 0.5]
    return ncols, sum(1 for g in rows if len(g) > 1)


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
        ll = o.get("labelLines")
        if "kind" not in o and ll:
            # a text: where its words are (its stored box may be stale)
            c = sum(l["cx" if X else "cy"] for l in ll) / len(ll)
            if c > cut:
                for l in ll:
                    l["cx" if X else "cy"] += d
                    if not X and l.get("baseline") is not None:
                        l["baseline"] += d
                if isinstance(o.get(kx), (int, float)):
                    o[kx] += d
                return True
            return False
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
    moved = {n["id"]: (n["x"] + n["w"] / 2 if X else n["y"] + n["h"] / 2) > cut for n in s["nodes"]}
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
        pts = [list(p) for p in o["points"]]
        o["points"] = [[mv(p[0]), p[1]] if X else [p[0], mv(p[1])] for p in pts]
        # the end at a box goes with the box, and the stretch leading up to
        # it with that end, as long as it keeps the same line
        if o.get("near") in moved and moved[o["near"]]:
            seq = range(len(pts)) if o.get("nearEnd", 0) == 0 else range(len(pts) - 1, -1, -1)
            i0 = 0 if X else 1
            first = None
            for i in seq:
                if first is None:
                    first = pts[i][i0]
                elif abs(pts[i][i0] - first) > 0.5:
                    break
                if pts[i][i0] <= cut:
                    o["points"][i][i0] = pts[i][i0] + d
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
                            h=max(l["cy"] for l in ll) + EM * 0.6 - y0, kind="guard", flow=g.get("onFlow"),
                            near=None if g.get("onFlow") else g.get("near")))
    for t in s["lanes"]:
        if t.get("title"):
            out.append(dict(id=t.get("id"), x=t["cx"] - t["textWidth"] / 2, y=t["cy"] - EM * 0.7,
                            w=t["textWidth"], h=EM * 1.4, kind="title"))
    return out


def need_decision(s):
    """the room a flow at a diamond needs: the straight lead it leaves or
    meets the diamond by (router.route_libavoid: an arrowhead and a label size
    more), and the margin the router keeps round the next box"""
    return s["arrow"] + EM + 0.75 * EM + 0.5 * EM


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
            if (a.get("near") and a["near"] == b["id"]) or (b.get("near") and b["near"] == a["id"]):
                if ov_x <= 0 or ov_y <= 0:
                    continue                      # a decision's question, beside it as it should be
            need = (need_decision(s) if e and "decision" in (a["kind"], b["kind"]) else need_flow) if e else max(gap.get(a["kind"], 0.5 * EM), gap.get(b["kind"], 0.5 * EM))
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
    mg = 2.5 * EM if s.get("dashed") else m          # room for a phase box's edge between
    for g in (i for i in it if i["kind"] == "guard"):
        if g["x"] < fb[0] + mg:
            out.append(("x", (fb[0] + g["x"] + g["w"] / 2) / 2, fb[0] + mg - g["x"], g["id"], "frame"))
        if g["x"] + g["w"] > fb[2] - mg:
            out.append(("x", (g["x"] + g["w"] / 2 + fb[2]) / 2, g["x"] + g["w"] - (fb[2] - mg), g["id"], "frame"))
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
    # a text whose middle lies past the frame's edge cannot be brought in by
    # widening the figure (every cut beyond it moves it too): moved in first
    fb = s.get("frameBox") or [0, 0, s["canvas"]["w"], s["canvas"]["h"]]
    for g in s.get("guards", []):
        ll = g.get("labelLines") or []
        if not ll:
            continue
        x0 = min(l["cx"] - l["w"] / 2 for l in ll)
        x1 = max(l["cx"] + l["w"] / 2 for l in ll)
        c = (x0 + x1) / 2
        d = (fb[0] + EM - x0) if c < fb[0] else (fb[2] - EM - x1) if c > fb[2] else 0
        for l in ll:
            l["cx"] += d
        if d and isinstance(g.get("x"), (int, float)):
            g["x"] += d
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
        # a cut that parted nothing the last time (what moves with the cut is
        # not what the conflict measures): left be
        if made and made[-1][0] == ax and made[-1][3:] == (a, b) and abs(made[-1][2] - round(d, 1)) < 0.2:
            stuck.add((ax, a, b))
            continue
        _stretch(s, ax, cut, d)
        made.append((ax, round(cut), round(d, 1), a, b))
    return made


def main(src, out, *opts):
    spec = bd.load(src)
    bd.clear_guards(spec)
    s = house(spec)
    held = phase_contents(s)
    if "--no-grid" in opts:
        aligned = align_boxes(s) if "--no-align" not in opts else 0
    else:
        cols, rows = grid(s)
        aligned = 0
        print("  grid: %d columns, %d rows of more than one box" % (cols, rows))
    straight = straighten(s)
    routed = route_right_angles(s) if "--right-angles" in opts else \
        route_by_drawio(s) if "--drawio-routing" in opts else 0
    before = (s["canvas"]["w"], s["canvas"]["h"])
    made = make_space(s) if "--no-space" not in opts else []
    hold_phases(s, held)
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
