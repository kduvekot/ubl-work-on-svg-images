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

    frame = max(w for _, w in e["rules"]["h"] + e["rules"]["v"])
    inner_v = [(x, w) for x, w in e["rules"]["v"] if 0 < x < W - w - 1]
    inner_h = [(y, t) for y, t in e["rules"]["h"] if 0 < y < H - t - 1]
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
            d["rx"], d["ry"] = M(n["rx"]), M(n["ry"])
        if k == "final":
            d["innerRatio"] = INNER_RATIO
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

    # guard labels keep the position they were measured at
    guards = []
    for t in e.get("text", []):
        if t.get("attachedTo") or t["text"].startswith("["):
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
        "arrow": M(70),
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
