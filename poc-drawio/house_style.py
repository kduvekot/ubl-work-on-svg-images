#!/usr/bin/env python3
"""A figure's spec in a house style: one look for the same element everywhere.

    python3 house_style.py <spec.json> <out-spec.json>

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


def main(src, out):
    spec = bd.load(src)
    bd.clear_guards(spec)
    s = house(spec)
    json.dump(s, open(out, "w", encoding="utf-8"), indent=1)
    ov = overlaps(s)
    print("  %s: scale %.2f, %.0f x %.0f px, %d overlapping pairs%s"
          % (os.path.basename(out), EM / label_em(spec), s["canvas"]["w"], s["canvas"]["h"], len(ov),
             "".join("\n    %s / %s" % p for p in ov)))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
