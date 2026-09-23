#!/usr/bin/env python3
"""Turn extract_graph.py output into a build_diagram.py spec - no hand editing.

    python3 spec_from_extract.py <extracted.json> <spec.json> [modelWidth]

Everything here is derived from the measurements: the model scale, stroke weights,
font size, node rectangles (interior expanded by half a stroke), corner radii, the
partition rules and titles, and the edges - including where each connector actually
meets its nodes, so nothing about the routing is guessed.
"""
import json, sys
from statistics import median

ASCENDER = 0.73          # Helvetica ascender as a fraction of em
INNER_RATIO = 0.425      # activity-final inner disc / outer ring (measured)


def main(src, out, model_w=1480.0):
    e = json.load(open(src))
    W, H = e["size"]
    s = model_w / W
    M = lambda v: round(v * s, 1)

    # A rule belongs to the border if it sits at the canvas edge - within a small
    # margin, because not every diagram draws its frame flush. UBL-2.3-Tender-
    # Contract-Pre insets its frame to x=6, and testing for exactly 0 filed both
    # of its frame rules as inner dividers, so the renderer drew divider lines
    # along the border on top of the frame rect. The doubled border was the single
    # largest invented component in the whole set.
    mv, mh = max(3, W * 0.015), max(3, H * 0.015)
    inner_v = [(x, w) for x, w in e["rules"]["v"] if mv < x and x + w < W - mv]
    inner_h = [(y, t) for y, t in e["rules"]["h"] if mh < y and y + t < H - mh]
    # The frame is the border rules only. Taking the widest of *all* rules made a
    # partition divider heavier than the border set the border's weight - UBL
    # draws some dividers at 22px against a 10px frame - and the extra width then
    # ran the whole way round the canvas as invented line-work.
    outer_v = [(x, w) for x, w in e["rules"]["v"] if (x, w) not in inner_v]
    outer_h = [(y, t) for y, t in e["rules"]["h"] if (y, t) not in inner_h]
    outer = [w for _, w in outer_v] + [t for _, t in outer_h]
    frame = median(outer) if outer else max(w for _, w in e["rules"]["h"] + e["rules"]["v"])
    divider = median([w for _, w in inner_v + inner_h]) if (inner_v or inner_h) else frame

    nodes_in = e["nodes"]
    acts = [n for n in nodes_in if n["kind"] == "action"]
    objs = [n for n in nodes_in if n["kind"] == "object"]
    s_act = int(median([n["stroke"] for n in acts])) if acts else 6
    s_obj = int(median([n["stroke"] for n in objs])) if objs else s_act * 2
    font_px = e.get("fontPx") or 78

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
        if k == "final":
            # per-node measurement where the extractor made one; the constant is
            # only a fallback for graphs written before it measured this
            d["innerRatio"] = n.get("innerRatio") or INNER_RATIO
        # each label line keeps the position it was measured at, so a label the
        # artwork put near the top of a tall box does not drift to the middle
        if n.get("labelLines"):
            d["labelLines"] = [{"text": l["text"], "cx": M(l["x"] + l["w"] / 2),
                                "cy": M(l["y"] + l["h"] / 2)} for l in n["labelLines"]]
        nodes.append(d)
    byid = {n["id"]: n for n in nodes}

    # where the connector really meets each node, as a fraction of that node's box
    def frac(node, pt):
        fx = (M(pt[0]) - node["x"]) / max(node["w"], 1e-6)
        fy = (M(pt[1]) - node["y"]) / max(node["h"], 1e-6)
        return [round(min(max(fx, 0.0), 1.0), 4), round(min(max(fy, 0.0), 1.0), 4)]

    edges = []
    for ed in e["edges"]:
        a, b = byid.get(ed["from"]), byid.get(ed["to"])
        if not a or not b:
            continue
        d = {"from": ed["from"], "to": ed["to"],
             "exitXY": frac(a, ed["fromPoint"]), "entryXY": frac(b, ed["toPoint"]),
             "straight": ed["routing"] in ("straight", "diagonal"),
             "confidence": ed.get("directionConfidence", "")}
        # the corners the connector actually turns at, so an orthogonal route is
        # put back where the artwork draws it rather than wherever a router elbows
        if ed.get("points"):
            d["points"] = [[M(p[0]), M(p[1])] for p in ed["points"]]
        if ed.get("guard"):
            d["label"] = ed["guard"]
        edges.append(d)

    cols = [p for p in e.get("partitions", []) if p["axis"] == "column"]
    bands = [p for p in e.get("partitions", []) if p["axis"] == "band"]
    lanes = []
    for c in cols:
        b = c.get("titleBox")
        lanes.append({"title": c["title"], "x": M(c["x0"]), "w": M(c["x1"] - c["x0"]),
                      "cx": M(b[0] + b[2] / 2) if b else M((c["x0"] + c["x1"]) / 2),
                      "cy": M(b[1] + b[3] / 2) if b else M(font_px)})

    # a narrow first column is the gutter the band titles run up
    gutter = e["rules"]["v"][1][0] if len(e["rules"]["v"]) > 2 and \
        e["rules"]["v"][1][0] < W * 0.04 else 0
    bandLabels = [{"title": b["title"], "cx": M(gutter / 2),
                   "cy": M((b["y0"] + b["y1"]) / 2)} for b in bands if gutter and b["title"]]

    # Free text keeps the position it was measured at.
    #
    # This used to carry only text the extractor had managed to attach to an edge,
    # which silently dropped 323 of the 386 blocks read off the 78 UML diagrams -
    # every "Yes"/"No" whose edge was not matched, and every free label such as
    # "Publish Official Journal". The artwork has that ink, so the SVG needs it
    # whether or not the attachment succeeded; an unattached label is still
    # content, it just carries less meaning in the graph. Anything already drawn
    # as a partition title is skipped so it is not drawn twice.
    titles = [tuple(p["titleBox"]) for p in e.get("partitions", []) if p.get("titleBox")]
    title_text = {" ".join((p.get("title") or "").split()).lower()
                  for p in e.get("partitions", []) if p.get("title")}

    def drawn_as_title(t):
        if " ".join(t["text"].split()).lower() in title_text:
            return True
        return any(abs(t["x"] - b[0]) <= 2 and abs(t["y"] - b[1]) <= 2 and
                   abs(t["w"] - b[2]) <= 2 and abs(t["h"] - b[3]) <= 2 for b in titles)

    guards = []
    for t in e.get("text", []):
        if drawn_as_title(t):
            continue
        g = {"text": t["text"], "x": M(t["x"]), "y": M(t["y"]),
             "w": M(t["w"]), "h": M(t["h"])}
        if t.get("lines"):
            g["labelLines"] = [{"text": l["text"], "cx": M(l["x"] + l["w"] / 2),
                                "cy": M(l["y"] + l["h"] / 2)} for l in t["lines"]]
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
        "arrow": M((e.get("arrowPx") or 56) / 0.8),
        # the dashed rounded box a CPFR phase is drawn inside, with the artwork's
        # own dash and gap so the rebuild repeats the pattern rather than inventing
        # one
        "dashed": [{"x": M(d["x"]), "y": M(d["y"]), "w": M(d["w"]), "h": M(d["h"]),
                    "rx": M(d["rx"]), "dash": M(d["dash"]), "gap": M(d["gap"])}
                   for d in e.get("dashed", [])],
        # a flow that leaves the diagram: drawn along its measured route, from
        # where it meets its node to where it runs off
        "openEnds": [{"points": [[M(p[0]), M(p[1])] for p in
                                 [o["at"]] + (o.get("points") or []) + [o["end"]]],
                      "arrow": bool(o.get("arrow"))}
                     for o in e.get("openEnds", [])],
        # where the border rules actually are, rather than assuming the frame is
        # flush with the canvas: some diagrams inset it (Tender-Contract-Pre puts
        # it at x=6) and a flush frame then misses the original's by its own width
        "frameBox": [M(min((x + w / 2 for x, w in outer_v), default=frame / 2)),
                     M(min((y + t / 2 for y, t in outer_h), default=frame / 2)),
                     M(max((x + w / 2 for x, w in outer_v), default=W - frame / 2)),
                     M(max((y + t / 2 for y, t in outer_h), default=H - frame / 2))],
        "dividers": [M(x + w / 2) for x, w in inner_v],
        "bands": [M(y + t / 2) for y, t in inner_h],
        "lanes": lanes, "bandLabels": bandLabels,
        "nodes": nodes, "edges": edges, "guards": guards,
    }
    json.dump(spec, open(out, "w"), indent=1)
    print("  scale %.5f   frame %dpx  divider %dpx  action %dpx  object %dpx"
          % (s, frame, divider, s_act, s_obj))
    print("  font %.0fpx (%.1f model)   %d lanes, %d bands, %d nodes, %d edges -> %s"
          % (font_px, M(font_px), len(lanes), len(bands), len(nodes), len(edges), out))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 1480.0)
