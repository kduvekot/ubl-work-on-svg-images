#!/usr/bin/env python3
"""Build a draw.io-editable SVG (and matching .drawio) from a measured spec.

    python3 build_diagram.py <spec.json> <out-basename>

The spec carries geometry MEASURED from the original PNG (see DetectShapes.java and
the Runs/Cols scanners), not eyeballed. One model produces both the published SVG and
the editable draw.io file; the SVG embeds the model in its `content` attribute.

Shapes follow UML 2.5.1 notation and the TC's own draw.io style vocabulary:
action = rounded rect, object node = plain rect (heavier stroke), initial = filled
disc, activity final = ring + disc, decision = rhombus, edges = open "V" arrowhead.
"""
import html, json, sys, xml.sax.saxutils as su

SIDE = {"l": (0, .5), "r": (1, .5), "t": (.5, 0), "b": (.5, 1)}
# what each kind is called in the drawing, for the <title> a reader sees
KIND_NAME = {"action": "action", "object": "object node (document)",
             "initial": "initial node (start)", "final": "activity final (end)",
             "decision": "decision", "fork": "fork/join bar", "note": "note"}
STRAIGHT_TOLERANCE = 4.0     # below this, draw one straight segment, not an elbow


def load(path):
    s = json.load(open(path, encoding="utf-8"))
    s["byid"] = {n["id"]: n for n in s["nodes"]}
    return s


def anchor(n, e, which):
    """Where the connector meets the node. A measured pair of fractions is used
    when the extractor found one - it is the actual contact point in the original
    - and the named side is only the fallback."""
    f = e.get("exitXY" if which == "exit" else "entryXY")
    if f is None:
        f = SIDE[e[which]]
    return (n["x"] + n["w"] * f[0], n["y"] + n["h"] * f[1])


def side_of(e, which):
    """which side the measured contact point sits on, for the elbow logic"""
    f = e.get("exitXY" if which == "exit" else "entryXY")
    if f is None:
        return e[which]
    fx, fy = f
    return ("l" if fx < 0.5 else "r") if min(fx, 1 - fx) < min(fy, 1 - fy) \
        else ("t" if fy < 0.5 else "b")


def polyline(spec, e):
    a, b = spec["byid"][e["from"]], spec["byid"][e["to"]]
    p0, p1 = anchor(a, e, "exit"), anchor(b, e, "entry")
    if e.get("straight"):
        return [p0] + [tuple(p) for p in e.get("points", [])] + [p1]
    pts = [p0] + [tuple(p) for p in e.get("points", [])] + [p1]
    out = [pts[0]]
    for i, nxt in enumerate(pts[1:], 1):
        cur, last = out[-1], i == len(pts) - 1
        dx, dy = abs(cur[0] - nxt[0]), abs(cur[1] - nxt[1])
        # a near-aligned pair is drawn straight - the original artwork does the same,
        # and an elbow here would also swing the arrowhead onto the wrong axis
        if dx > STRAIGHT_TOLERANCE and dy > STRAIGHT_TOLERANCE:
            ex_h, en_h = side_of(e, "exit") in "lr", side_of(e, "entry") in "lr"
            if last:
                if ex_h and en_h:
                    mx = (cur[0] + nxt[0]) / 2
                    out += [(mx, cur[1]), (mx, nxt[1])]
                elif not ex_h and not en_h:
                    my = (cur[1] + nxt[1]) / 2
                    out += [(cur[0], my), (nxt[0], my)]
                elif en_h:
                    out.append((cur[0], nxt[1]))
                else:
                    out.append((nxt[0], cur[1]))
            else:
                out.append((nxt[0], cur[1]) if ex_h else (cur[0], nxt[1]))
        out.append(nxt)
    return out


def lines_of(n, cx, cy, size, font, weight="", style=""):
    """measured line positions when the extractor found them, centred otherwise"""
    ll = n.get("labelLines")
    if not ll:
        return text(n.get("label", ""), cx, cy, size, font, weight, style)
    return "".join(text(l["text"], l["cx"], l["cy"], size, font, weight, style) for l in ll)


def text(label, cx, cy, size, font, weight="", style=""):
    lines = label.split("\n")
    lh = size * 1.25
    y0 = cy - (len(lines) - 1) * lh / 2
    extra = (' font-weight="%s"' % weight if weight else "") + (' font-style="%s"' % style if style else "")
    return "".join(
        '<text x="%.1f" y="%.1f" text-anchor="middle" font-family="%s" font-size="%.1f"%s>%s</text>'
        % (cx, y0 + i * lh + size * 0.35, font, size, extra, su.escape(t))
        for i, t in enumerate(lines))


def group(kind, ident=None, title=None, **data):
    """Open a <g> that says what this element is.

    The classification is the durable part of this work, and it was living only in
    the graph and in the draw.io model embedded in the SVG's `content` attribute -
    the drawn shapes themselves were anonymous geometry, so anyone opening the SVG
    saw a rounded rectangle and had to infer that it is an action. Each element now
    carries its own kind, its id, and the ids it connects, which is also what makes
    the file queryable and restylable by type."""
    at = ' id="%s"' % ident if ident else ""
    at += ' class="ubl-%s"' % kind + ' data-kind="%s"' % kind
    for k, v in sorted(data.items()):
        if v not in (None, ""):
            at += ' data-%s="%s"' % (k.replace("_", "-"), su.escape(str(v), {'"': "&quot;"}))
    head = "<g%s>" % at
    return head + ("<title>%s</title>" % su.escape(title) if title else "")


def svg_body(spec):
    S, F = spec["stroke"], spec["font"]
    W, H = spec["canvas"]["w"], spec["canvas"]["h"]
    o = ['<rect x="0" y="0" width="%.1f" height="%.1f" fill="#fff"/>' % (W, H)]
    fb = spec.get("frameBox") or [S["frame"] / 2, S["frame"] / 2,
                                  W - S["frame"] / 2, H - S["frame"] / 2]
    o.append(group("frame", title="diagram frame"))
    o.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="none" stroke="#000" stroke-width="%.2f"/>'
             % (fb[0], fb[1], fb[2] - fb[0], fb[3] - fb[1], S["frame"]))
    o.append("</g>")
    for i, d in enumerate(spec.get("dividers", [])):
        o.append(group("lane-divider", "divider%d" % i, "lane divider", axis="v"))
        o.append('<line x1="%.1f" y1="0" x2="%.1f" y2="%.1f" stroke="#000" stroke-width="%.2f"/>'
                 % (d, d, H, S["divider"]))
        o.append("</g>")
    for i, d in enumerate(spec.get("bands", [])):
        o.append(group("band-divider", "band%d" % i, "band divider", axis="h"))
        o.append('<line x1="0" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#000" stroke-width="%.2f"/>'
                 % (d, W, d, S["divider"]))
        o.append("</g>")
    for i, gr in enumerate(spec.get("greyRules", [])):
        # a divider the artwork draws in grey; promoting it to black would be a
        # louder line than the drawing has
        o.append(group("lane-divider", "greyrule%d" % i, "lane divider (drawn in grey)",
                       axis=gr["axis"], tone=gr["colour"]))
        if gr["axis"] == "v":
            o.append('<line x1="%.1f" y1="0" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.2f"/>'
                     % (gr["at"] + gr["w"] / 2, gr["at"] + gr["w"] / 2, H, gr["colour"], gr["w"]))
        else:
            o.append('<line x1="0" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.2f"/>'
                     % (gr["at"] + gr["w"] / 2, W, gr["at"] + gr["w"] / 2, gr["colour"], gr["w"]))
        o.append("</g>")
    for i, d in enumerate(spec.get("dashed", [])):
        # the dashed rounded box a CPFR phase is drawn inside, at the artwork's own
        # dash and gap
        o.append(group("phase-boundary", "phase%d" % i,
                       "phase boundary (this diagram is one phase of a larger process)"))
        o.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="%.2f" ry="%.2f" '
                 'fill="none" stroke="#000" stroke-width="%.2f" stroke-dasharray="%.1f %.1f"/>'
                 % (d["x"], d["y"], d["w"], d["h"], d["rx"], d["rx"],
                    d.get("weight") or S["divider"],
                    max(d["dash"], 0.5), max(d["gap"], 0.5)))
        o.append("</g>")
    for i, l in enumerate(spec["lanes"]):
        o.append(group("lane-title", "lane%d" % i, l["title"]))
        o.append(text(l["title"], l["cx"], l["cy"], F["lane"], F["family"]))
        o.append("</g>")
    for i, b in enumerate(spec.get("bandLabels", [])):   # band titles run up the gutter
        o.append(group("band-title", "bandtitle%d" % i, b["title"]))
        o.append('<g transform="rotate(-90 %.1f %.1f)">%s</g>'
                 % (b["cx"], b["cy"], text(b["title"], b["cx"], b["cy"], F["lane"], F["family"])))
        o.append("</g>")
    for n in spec["nodes"]:
        x, y, w, h = n["x"], n["y"], n["w"], n["h"]
        cx, cy, k = x + w / 2, y + h / 2, n["kind"]
        o.append(group(k, n["id"],
                       "%s%s" % (KIND_NAME.get(k, k),
                                 ": " + " ".join(n["label"].split())
                                 if n.get("label") else "")))
        if k == "action":
            rx = n.get("rx", n.get("r", h / 2))
            ry = n.get("ry", rx)          # the originals have ELLIPTICAL corners
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" ry="%.1f" '
                     'fill="#fff" stroke="#000" stroke-width="%.2f"/>'
                     % (x, y, w, h, rx, ry, S["action"]))
            o.append(lines_of(n, cx, cy, F["node"], F["family"], weight="bold"))
        elif k == "object":
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#fff" stroke="#000" stroke-width="%.2f"/>'
                     % (x, y, w, h, S["object"]))
            o.append(lines_of(n, cx, cy, F["node"], F["family"], weight="bold", style="italic"))
        elif k == "initial":
            o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#000"/>' % (cx, cy, w / 2))
        elif k == "final":
            o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#fff" stroke="#000" stroke-width="%.2f"/>'
                     % (cx, cy, w / 2, S["action"]))
            o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#000"/>' % (cx, cy, w / 2 * n.get("innerRatio", .45)))
        elif k == "decision":
            o.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="#fff" stroke="#000" stroke-width="%.2f"/>'
                     % (cx, y, x + w, cy, cx, y + h, x, cy, S["action"]))
            o.append(lines_of(n, cx, cy, F["node"], F["family"]))
        elif k == "fork":
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#000"/>' % (x, y, w, h))
        elif k == "note":
            f = min(w, h) * 0.30                      # the folded corner
            o.append('<path d="M %.1f %.1f H %.1f L %.1f %.1f V %.1f H %.1f Z" '
                     'fill="#fff" stroke="#000" stroke-width="%.2f"/>'
                     % (x, y, x + w - f, x + w, y + f, y + h, x, S["action"]))
            o.append('<path d="M %.1f %.1f V %.1f H %.1f" fill="none" stroke="#000" stroke-width="%.2f"/>'
                     % (x + w - f, y, y + f, x + w, S["action"]))
            o.append(lines_of(n, cx, cy, F["node"], F["family"]))
        o.append("</g>")
    for i, e in enumerate(spec["edges"]):
        pts = polyline(spec, e)
        o.append(group("edge", "e%d" % i, "%s to %s" % (e["from"], e["to"]),
                       source=e["from"], target=e["to"],
                       routing="straight" if e.get("straight") else "orthogonal",
                       confidence=e.get("confidence")))
        o.append('<polyline points="%s" fill="none" stroke="#000" stroke-width="%.2f" marker-end="url(#arrow)"/>'
                 % (" ".join("%.1f,%.1f" % p for p in pts), S["edge"]))
        o.append("</g>")
    for i, oe in enumerate(spec.get("openEnds", [])):
        # a flow that leaves the diagram, drawn along the route it actually takes
        o.append(group("off-page-flow", "open%d" % i,
                       "flow continuing outside this diagram",
                       node=oe.get("node"),
                       direction="into the diagram" if oe.get("inward") else "out of the diagram"))
        o.append('<polyline points="%s" fill="none" stroke="#000" stroke-width="%.2f"%s/>'
                 % (" ".join("%.1f,%.1f" % (p[0], p[1]) for p in oe["points"]),
                    S["edge"], ' marker-end="url(#arrow)"' if oe.get("arrow") else ""))
        o.append("</g>")
    for i, g in enumerate(spec.get("guards", [])):
        o.append(group("guard", "text%d" % i, " ".join(g.get("text", "").split())))
        o.append(lines_of(g, g["x"] + g["w"] / 2, g["y"] + g["h"] / 2, F["guard"], F["family"]))
        o.append("</g>")
    return "".join(o)


MXSTYLE = {
    "action":  "rounded=1;arcSize=40;whiteSpace=wrap;html=1;fontStyle=1;",
    "object":  "rounded=0;whiteSpace=wrap;html=1;fontStyle=3;strokeWidth=2;",
    "initial": "ellipse;html=1;shape=startState;fillColor=#000000;strokeColor=#000000;",
    "final":   "ellipse;html=1;shape=endState;fillColor=#000000;strokeColor=#000000;",
    "decision": "rhombus;whiteSpace=wrap;html=1;",
    "fork":    "html=1;shape=line;direction=north;strokeWidth=12;",
    "note":    "shape=note;whiteSpace=wrap;html=1;backgroundOutline=1;darkOpacity=0.05;",
    "lane":    "swimlane;whiteSpace=wrap;html=1;startSize=%d;",
    "edge":    "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=open;endFill=0;endSize=14;",
}


def mxfile(spec):
    F = spec["font"]
    c = ['<mxGraphModel dx="1400" dy="800" grid="0" page="1" pageScale="1" '
         'pageWidth="%d" pageHeight="%d"><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
         % (round(spec["canvas"]["w"]), round(spec["canvas"]["h"]))]
    for i, l in enumerate(spec["lanes"]):
        c.append('<mxCell id="lane%d" value="%s" style="%s" vertex="1" parent="1">'
                 '<mxGeometry x="%.1f" y="0" width="%.1f" height="%.1f" as="geometry"/></mxCell>'
                 % (i, su.escape(l["title"]), MXSTYLE["lane"] % round(F["lane"] * 2),
                    l["x"], l["w"], spec["canvas"]["h"]))
    for n in spec["nodes"]:
        c.append('<mxCell id="%s" value="%s" style="%sfontFamily=Helvetica;fontSize=%d;" vertex="1" parent="1">'
                 '<mxGeometry x="%.1f" y="%.1f" width="%.1f" height="%.1f" as="geometry"/></mxCell>'
                 % (n["id"], su.escape(n.get("label", "").replace("\n", " ")),
                    MXSTYLE[n["kind"]], round(F["node"]), n["x"], n["y"], n["w"], n["h"]))
    for i, e in enumerate(spec["edges"]):
        fx, fy = e.get("exitXY") or SIDE[e["exit"]]
        tx, ty = e.get("entryXY") or SIDE[e["entry"]]
        st = MXSTYLE["edge"] + "exitX=%s;exitY=%s;entryX=%s;entryY=%s;" % (fx, fy, tx, ty)
        if e.get("straight"):
            st = st.replace("edgeStyle=orthogonalEdgeStyle;", "edgeStyle=none;")
        pts = "".join('<mxPoint x="%.1f" y="%.1f"/>' % tuple(p) for p in e.get("points", []))
        c.append('<mxCell id="e%d" value="%s" style="%s" edge="1" parent="1" source="%s" target="%s">'
                 '<mxGeometry relative="1" as="geometry">%s</mxGeometry></mxCell>'
                 % (i, su.escape(e.get("label", "")), st, e["from"], e["to"],
                    ('<Array as="points">%s</Array>' % pts) if pts else ""))
    c.append("</root></mxGraphModel>")
    return ('<mxfile host="UBL-TC" agent="UBL artwork pipeline" type="device">'
            '<diagram id="d1" name="Page-1">' + "".join(c) + "</diagram></mxfile>")


# A review copy of the drawing, coloured by what each element was classified as,
# so that a reader can check the classification by eye rather than by reading JSON.
#
# Six hues, not one per kind. The published palette's eight clear the colour-blind
# and normal-vision floors only for *adjacent* pairs; here any element can sit
# beside any other, and on that all-pairs test the largest set that passes is six
# (validated with the palette checker: worst normal-vision dE 15.6, worst CVD 6.9,
# which the rules allow because shape carries the distinction as well as colour).
# So notes share the decision hue - a folded box and a diamond are never mistaken
# for each other - and connectors and structure stay in neutrals, which do not
# compete with the six.
CLASS_COLOUR = {
    "action":         "#2a78d6",     # blue
    "object":         "#e34948",     # red
    "initial":        "#1baf7a",     # aqua
    "final":          "#eda100",     # yellow
    "decision":       "#4a3aa7",     # violet
    "note":           "#4a3aa7",     # violet, shared: the shapes cannot be confused
    "fork":           "#008300",     # green
    "edge":           "#111111",     # connectors stay near-black
    "off-page-flow":  "#111111",
    "frame":          "#8a8a85",
    "lane-divider":   "#8a8a85",
    "band-divider":   "#8a8a85",
    "phase-boundary": "#8a8a85",
}
LEGEND = [("action", "action"), ("object", "object node (document)"),
          ("initial", "initial (start)"), ("final", "activity final (end)"),
          ("decision", "decision / note"), ("fork", "fork or join bar"),
          ("edge", "connector"), ("frame", "frame, lane divider, phase boundary")]


def classified(spec, defs, model):
    W, H = spec["canvas"]["w"], spec["canvas"]["h"]
    fs = max(9.0, spec["font"]["lane"] * 0.8)
    band = fs * 2.6
    css = []
    for kind, colour in CLASS_COLOUR.items():
        css.append(".ubl-%s rect, .ubl-%s circle, .ubl-%s polygon, .ubl-%s path,"
                   " .ubl-%s line, .ubl-%s polyline"
                   " { stroke: %s !important; }" % ((kind,) * 6 + (colour,)))
    # the shapes the artwork fills solid keep a fill, in their own hue
    css.append(".ubl-initial circle { fill: %s !important; }" % CLASS_COLOUR["initial"])
    css.append(".ubl-fork rect { fill: %s !important; }" % CLASS_COLOUR["fork"])
    css.append(".ubl-final circle + circle { fill: %s !important; }" % CLASS_COLOUR["final"])
    css.append("text { fill: #111 !important; }")     # labels stay ink, never a hue

    leg = ['<g class="ubl-legend"><rect x="0" y="%.1f" width="%.1f" height="%.1f" fill="#fff"/>'
           % (H, W, band)]
    x = fs
    for kind, name in LEGEND:
        leg.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                   % (x, H + band / 2 - fs * 0.45, fs * 0.9, fs * 0.9, CLASS_COLOUR[kind]))
        leg.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="%.1f" fill="#111">%s</text>'
                   % (x + fs * 1.25, H + band / 2 + fs * 0.33, spec["font"]["family"], fs,
                      su.escape(name)))
        x += fs * 1.25 + fs * 0.55 * len(name) + fs * 1.2
    leg.append("</g>")

    return ('<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" '
            'version="1.1" width="%.0f" height="%.0f" viewBox="0 0 %.1f %.1f" content="%s">'
            % (W, H + band, W, H + band, html.escape(model, quote=True))
            + "<style>" + "".join(css) + "</style>"
            + defs + svg_body(spec) + "".join(leg) + "</svg>")


def main(spec_path, out):
    spec = load(spec_path)
    S = spec["stroke"]
    defs = ('<defs><marker id="arrow" markerUnits="userSpaceOnUse" viewBox="0 0 20 20" '
            'refX="18" refY="10" markerWidth="%.0f" markerHeight="%.0f" orient="auto">'
            '<path d="M 2 2 L 18 10 L 2 18" fill="none" stroke="#000" stroke-width="%.2f" '
            'stroke-linecap="round" stroke-linejoin="round"/></marker></defs>'
            % (spec.get("arrow", 20), spec.get("arrow", 20), S["edge"] * 0.9))
    model = mxfile(spec)
    W, H = spec["canvas"]["w"], spec["canvas"]["h"]
    svg = ('<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" '
           'version="1.1" width="%.0f" height="%.0f" viewBox="0 0 %.1f %.1f" content="%s">'
           % (W, H, W, H, html.escape(model, quote=True)) + defs + svg_body(spec) + "</svg>")
    open(out + ".svg", "w", encoding="utf-8").write(svg)
    open(out + ".drawio", "w", encoding="utf-8").write(model)
    open(out + "-classified.svg", "w", encoding="utf-8").write(classified(spec, defs, model))
    print("  %s.svg + .drawio + -classified.svg   (%d nodes, %d edges)"
          % (out, len(spec["nodes"]), len(spec["edges"])))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
