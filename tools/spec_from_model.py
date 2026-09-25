#!/usr/bin/env python3
"""Turn a diagram's model and layout into a build_diagram.py spec - no hand editing.

    python3 spec_from_model.py <NAME-diagram.json> <spec.json> [modelWidth]

reads NAME-diagram.json and, beside it, NAME-layout.json (both written by
model_io.py from the extractor's graph). Nothing is read from the extraction
report: what is drawn comes from the model and its layout alone.

Everything here is derived from the measurements: the model scale, stroke weights,
font size, node rectangles (interior expanded by half a stroke), corner radii, the
partition rules and titles, and the edges - including where each connector actually
meets its nodes, so nothing about the routing is guessed.
"""
import json, os, sys
from statistics import median

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_io

ASCENDER = 0.73          # Helvetica ascender as a fraction of em
INNER_RATIO = 0.425      # activity-final inner disc / outer ring (measured)


def main(src, out, model_w=1480.0):
    model, lay = model_io.load(src)
    W, H = lay["size"]
    s = model_w / W
    M = lambda v: round(v * s, 1)
    rules = {ax: [(r["at"], r["width"]) for r in lay["rules"][k]]
             for ax, k in (("v", "vertical"), ("h", "horizontal"))}

    # A rule belongs to the border if it sits at the canvas edge - within a small
    # margin, because not every diagram draws its frame flush. UBL-2.3-Tender-
    # Contract-Pre insets its frame to x=6, and testing for exactly 0 filed both
    # of its frame rules as inner dividers, so the renderer drew divider lines
    # along the border on top of the frame rect. The doubled border was the single
    # largest invented component in the whole set.
    mv, mh = max(3, W * 0.015), max(3, H * 0.015)
    inner_v = [(x, w) for x, w in rules["v"] if mv < x and x + w < W - mv]
    inner_h = [(y, t) for y, t in rules["h"] if mh < y and y + t < H - mh]
    # The frame is the border rules only. Taking the widest of *all* rules made a
    # partition divider heavier than the border set the border's weight - UBL
    # draws some dividers at 22px against a 10px frame - and the extra width then
    # ran the whole way round the canvas as invented line-work.
    outer_v = [(x, w) for x, w in rules["v"] if (x, w) not in inner_v]
    outer_h = [(y, t) for y, t in rules["h"] if (y, t) not in inner_h]
    outer = [w for _, w in outer_v] + [t for _, t in outer_h]
    frame = median(outer) if outer else max(w for _, w in rules["h"] + rules["v"])
    divider = median([w for _, w in inner_v + inner_h]) if (inner_v or inner_h) else frame

    # How far each rule runs, read off its own ink rather than assumed to be edge
    # to edge: eleven of the inner rules in the 78 stop short, seven of them
    # covering less than three quarters of the page.
    def span(key):
        axis, at, wd = key
        for r in lay["rules"]["vertical" if axis == "v" else "horizontal"]:
            if (r["at"], r["width"]) == (at, wd):
                s = r["span"]
                return [M(s[0]), M(s[1])] if s else []
        return []

    # each node as the extractor measured it: what it is from the model, where
    # and how it is drawn from the layout
    nodes_in = [dict(lay["nodes"][n["id"]], **n) for n in model["nodes"]]
    acts = [n for n in nodes_in if n["kind"] == "action"]
    objs = [n for n in nodes_in if n["kind"] == "object"]
    s_act = int(median([n["stroke"] for n in acts])) if acts else 6
    s_obj = int(median([n["stroke"] for n in objs])) if objs else s_act * 2
    style = lay["style"]
    font_px = style.get("fontPx") or 78

    nodes = []
    for n in nodes_in:
        k = n["kind"]
        st = s_obj if k == "object" else (n.get("stroke") or s_act) if k == "final" else s_act
        if k in ("initial", "fork"):
            nodes.append({"id": n["id"], "kind": k, "label": "",
                          "x": M(n["x"]), "y": M(n["y"]), "w": M(n["w"]), "h": M(n["h"])})
            continue
        d = {"id": n["id"], "kind": k, "label": n.get("label", ""),
             "x": M(n["x"] - st / 2), "y": M(n["y"] - st / 2),
             "w": M(n["w"] + st), "h": M(n["h"] + st)}
        if k in ("action", "note") and n.get("rx"):
            # the box above is the outer edge - interior inflated by the stroke -
            # so the corner radius has to be inflated with it. Carrying the
            # interior radius onto the outer box draws a corner tighter than the
            # original's, which is what leaves ink uncovered at all four corners.
            d["rx"], d["ry"] = M(n["rx"] + st / 2), M(n["ry"] + st / 2)
        if k == "note" and n.get("fold"):
            d["fold"] = M(n["fold"])
        if k == "final":
            # per-node measurement where the extractor made one; the constant is
            # only a fallback for graphs written before it measured this
            d["innerRatio"] = n.get("innerRatio") or INNER_RATIO
        # each label line keeps the position it was measured at, so a label the
        # artwork put near the top of a tall box does not drift to the middle
        if n.get("labelLines"):
            # each line's measured width travels with it, so the rebuild can set
            # the line to exactly the width the artwork gives it rather than to
            # whatever Helvetica happens to make of the same string
            d["labelLines"] = [{"text": l["text"], "cx": M(l["x"] + l["w"] / 2),
                                "cy": M(l["y"] + l["h"] / 2), "w": M(l["w"])}
                               for l in n["labelLines"]]
        if n.get("bold") is not None:
            d["bold"] = bool(n["bold"])
        nodes.append(d)
    byid = {n["id"]: n for n in nodes}

    # where the connector really meets each node, as a fraction of that node's box
    def frac(node, pt):
        fx = (M(pt[0]) - node["x"]) / max(node["w"], 1e-6)
        fy = (M(pt[1]) - node["y"]) / max(node["h"], 1e-6)
        return [round(min(max(fx, 0.0), 1.0), 4), round(min(max(fy, 0.0), 1.0), 4)]

    texts = {t["id"]: t for t in model["texts"]}
    lanes_by_id = {l["id"]: l for l in model["lanes"]}
    edges = []
    for f in model["flows"]:
        ed = dict(lay["flows"][f["id"]], **f)
        a, b = byid.get(ed["from"]), byid.get(ed["to"])
        if not a or not b:
            continue
        d = {"id": f["id"], "from": ed["from"], "to": ed["to"],
             "exitXY": frac(a, ed["fromPoint"]), "entryXY": frac(b, ed["toPoint"]),
             "straight": ed["routing"] in ("straight", "diagonal"),
             "confidence": (f.get("direction") or {}).get("confidence", "")}
        # the corners the connector actually turns at, so an orthogonal route is
        # put back where the artwork draws it rather than wherever a router elbows
        if ed.get("points"):
            d["points"] = [[M(p[0]), M(p[1])] for p in ed["points"]]
        # the guard's words, from the text block that is the guard (or, where the
        # reading attached a lane title to the flow, from that lane's title)
        if f.get("guard"):
            g = f["guard"]
            label = (model_io.guard_text(texts[g]) if g in texts
                     else model_io.norm(lanes_by_id[g]["title"]))
            if label:
                d["label"] = label
        # the artwork's own dash pattern, where the flow is drawn dashed
        if ed.get("dash"):
            d["dash"], d["gap"] = M(ed["dash"]), M(ed["gap"])
            if ed.get("dashOffset") is not None:
                d["dashOffset"] = M(ed["dashOffset"])
        # a point at both ends: a standing relationship between two parties, not
        # a flow from one to the other
        if f.get("bothEnds"):
            d["arrowBoth"] = True
        edges.append(d)

    parts = [dict(lay["lanes"][l["id"]], **l) for l in model["lanes"]]
    cols = [p for p in parts if p["axis"] == "column"]
    bands = [p for p in parts if p["axis"] == "band"]
    lanes = []
    for c in cols:
        b = c.get("titleBox")
        # A lane whose name the artwork does not draw (given by a correction) is
        # drawn as it always was, with no words; the name goes to the draw.io
        # model, where a lane is a lane, as "name".
        shown = c.get("titleShown", True)
        lane = {"id": c["id"], "title": c["title"] if shown else "",
                "x": M(c["x0"]), "w": M(c["x1"] - c["x0"]),
                "cx": M(b[0] + b[2] / 2) if b else M((c["x0"] + c["x1"]) / 2),
                "cy": M(b[1] + b[3] / 2) if b else M(font_px)}
        if not shown:
            lane["name"] = c["title"]
        lanes.append(lane)

    # Words drawn where the reading had put a lane title, which a correction has
    # found to be something else - a phase's title, or a guard. They are set as
    # a lane title is set, in the same box, so the drawing does not move.
    def caption(i, role, words, b):
        return {"id": i, "role": role, "text": words,
                "cx": M(b[0] + b[2] / 2), "cy": M(b[1] + b[3] / 2)}
    captions = [caption(p["id"], "phase-title", p["title"], lay["phases"][p["id"]]["title"]["box"])
                for p in model["phases"]
                if lay["phases"][p["id"]].get("title", {}).get("as") == "lane-title"]
    captions += [caption(t["id"], "guard", t["text"], lay["texts"][t["id"]]["box"])
                 for t in model["texts"] if lay["texts"][t["id"]].get("as") == "lane-title"]

    # a narrow first column is the gutter the band titles run up
    gutter = rules["v"][1][0] if len(rules["v"]) > 2 and \
        rules["v"][1][0] < W * 0.04 else 0
    bandLabels = [{"id": b["id"], "title": b["title"], "cx": M(gutter / 2),
                   "cy": M((b["y0"] + b["y1"]) / 2)} for b in bands if gutter and b["title"]]

    # Free text keeps the position it was measured at.
    #
    # This used to carry only text the extractor had managed to attach to an edge,
    # which silently dropped 323 of the 386 blocks read off the 78 UML diagrams -
    # every "Yes"/"No" whose edge was not matched, and every free label such as
    # "Publish Official Journal". The artwork has that ink, so the SVG needs it
    # whether or not the attachment succeeded; an unattached label is still
    # content, it just carries less meaning in the graph. A lane title is not
    # among them: the model holds it once, as the lane's, and model_io.py moves
    # the extractor's second reading of it to the extraction report.
    # A phase title the reading placed as text is set as the text it was.
    placed = [(tm["id"], tm["text"], lay["texts"][tm["id"]], None) for tm in model["texts"]
              if lay["texts"][tm["id"]].get("as") != "lane-title"]
    placed += [(p["id"], p["title"], lay["phases"][p["id"]]["title"], "phase-title")
               for p in model["phases"]
               if lay["phases"][p["id"]].get("title", {}).get("as") == "text"]
    guards = []
    for i, words, t, role in placed:
        g = {"id": i, "text": words, "x": M(t["x"]), "y": M(t["y"]),
             "w": M(t["w"]), "h": M(t["h"])}
        if role:
            g["role"] = role
        if t.get("lines"):
            g["labelLines"] = [{"text": l["text"], "cx": M(l["x"] + l["w"] / 2),
                                "cy": M(l["y"] + l["h"] / 2), "w": M(l["w"])}
                               for l in t["lines"]]
        guards.append(g)

    spec = {
        "canvas": {"w": model_w, "h": round(H * s, 3)},
        "stroke": {"frame": M(frame), "divider": M(divider), "action": M(s_act),
                   "object": M(s_obj), "edge": M(s_act)},
        "font": {"family": "Helvetica, Arial, sans-serif",
                 "node": M(font_px), "lane": M(font_px), "guard": M(font_px)},
        # the arrowhead the diagram itself draws, measured off its connectors.
        # The marker's V occupies 0.8 of the marker box, so the box is the
        # measured length divided by that. 56px - the effective size of the
        # constant that used to be used everywhere - is the fallback, and it was
        # twice too big for the 26px-type diagrams and half the size of
        # ProcurementProcess's.
        "arrow": M((style.get("arrowPx") or 56) / 0.8),
        # across the line as well as along it: the artwork's heads are blunter
        # than a triangle as wide as it is long, and drawing them square lost a
        # third of their ink
        "arrowWidth": M((style.get("arrowWidthPx") or (style.get("arrowPx") or 56)) / 0.8),
        "arrowStyle": style.get("arrowStyle") or "open",
        # the dashed rounded box a CPFR phase is drawn inside, with the artwork's
        # own dash and gap so the rebuild repeats the pattern rather than inventing
        # one
        "dashed": [{"id": p["id"], "x": M(d["x"]), "y": M(d["y"]), "w": M(d["w"]), "h": M(d["h"]),
                    "rx": M(d["rx"]), "dash": M(d["dash"]), "gap": M(d["gap"]),
                    "weight": M(d.get("weight") or 0)}
                   for p in model["phases"] for d in [lay["phases"][p["id"]]]],
        # dividers the artwork draws in grey rather than black, in their own tone
        "greyRules": [{"axis": r["axis"], "at": M(r["at"]), "w": M(r["w"]),
                       "colour": "#%02x%02x%02x" % ((r["level"],) * 3)}
                      for r in lay["greyRules"]],
        # a short stroke drawn across a partition rule: line-work the diagram
        # carries whose meaning the specification has not been read for, so it is
        # reproduced exactly as measured and classified as what it plainly is
        "crossMarks": [{"id": c["id"], "x1": M(m["x1"]), "y1": M(m["y1"]),
                        "x2": M(m["x2"]), "y2": M(m["y2"]),
                        "weight": M(m.get("weight") or 0)}
                       for c in model["marks"] for m in [lay["marks"][c["id"]]]],
        # a flow that leaves the diagram: drawn along its measured route, from
        # where it meets its node to where it runs off
        "openEnds": [{"id": om["id"], "points": [[M(p[0]), M(p[1])] for p in
                                 [o["at"]] + (o.get("points") or []) + [o["end"]]],
                      "arrow": bool(om.get("arrow"))}
                     for om in model["offPage"] for o in [lay["offPage"][om["id"]]]],
        # where the border rules actually are, rather than assuming the frame is
        # flush with the canvas: some diagrams inset it (Tender-Contract-Pre puts
        # it at x=6) and a flush frame then misses the original's by its own width
        "frameBox": [M(min((x + w / 2 for x, w in outer_v), default=frame / 2)),
                     M(min((y + t / 2 for y, t in outer_h), default=frame / 2)),
                     M(max((x + w / 2 for x, w in outer_v), default=W - frame / 2)),
                     M(max((y + t / 2 for y, t in outer_h), default=H - frame / 2))],
        # position, weight and the span the artwork draws it over
        "dividers": [[M(x + w / 2), M(w)] + span(("v", x, w)) for x, w in inner_v],
        "bands": [[M(y + t / 2), M(t)] + span(("h", y, t)) for y, t in inner_h],
        "lanes": lanes, "bandLabels": bandLabels, "captions": captions,
        "nodes": nodes, "edges": edges, "guards": guards,
    }
    json.dump(spec, open(out, "w"), indent=1)
    print("  scale %.5f   frame %dpx  divider %dpx  action %dpx  object %dpx"
          % (s, frame, divider, s_act, s_obj))
    print("  font %.0fpx (%.1f model)   %d lanes, %d bands, %d nodes, %d edges -> %s"
          % (font_px, M(font_px), len(lanes), len(bands), len(nodes), len(edges), out))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 1480.0)
