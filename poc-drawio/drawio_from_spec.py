#!/usr/bin/env python3
"""A native draw.io model of a figure, as close to its SVG as draw.io allows.

    python3 drawio_from_spec.py <spec.json> <out.drawio>

Proof of concept, kept apart from the pipeline: it reads the same spec as
tools/build_diagram.py (made by tools/spec_from_model.py from the JSONs) and
reuses its geometry - the guards moved off their lines, the hops, the routed
lines - without changing it. Where draw.io has a native way to say something
(a swimlane, a fork bar, an edge label, a line jump) that is used, set to the
measured sizes; where draw.io cannot say what the SVG says, the nearest native
setting is taken and the difference is written up in poc-drawio/README.md.
"""
import math, os, statistics, sys, xml.sax.saxutils as su

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import build_diagram as bd          # noqa: E402  (read only: geometry helpers)


def num(v, places=2):
    """a style or geometry number, without trailing noise"""
    return ("%.*f" % (places, v)).rstrip("0").rstrip(".")


def style(**kv):
    # a contact point is a fraction of the node's box: four places keep it
    # within a hundredth of a pixel
    return "".join("%s=%s;" % (k, num(v, 4 if k[:4] in ("exit", "entr") else 2)
                               if isinstance(v, float) else v) for k, v in kv.items())


def esc(s):
    return su.escape(s, {'"': "&quot;"})


def html_lines(lines):
    """label text for an html=1 label: one line each, as measured"""
    return "<br>".join(su.escape(t) for t in lines)


def text_block(item, fallback_size):
    """The measured lines of a label: their words, size, alignment and centre.

    draw.io sets a label as one block at one size and one alignment, where the
    SVG places every line on its own measured centre. The alignment is read off
    the measurements: the edge (left, centre or right) the lines agree on best.
    The block is then placed so its left edge (align=left), centre or right
    edge lies where the measured lines have theirs, and its middle on the
    middle of the lines."""
    ll = item.get("labelLines")
    if not ll:
        words = (item.get("label") or item.get("text") or "").split("\n")
        return dict(lines=words, size=fallback_size, align="center",
                    x=item["x"] + item["w"] / 2, cy=item["y"] + item["h"] / 2)
    size = statistics.median(l.get("size", fallback_size) for l in ll)
    lefts = [l["cx"] - l["w"] / 2 for l in ll]
    rights = [l["cx"] + l["w"] / 2 for l in ll]
    centres = [l["cx"] for l in ll]
    align = "center"
    if len(ll) > 1:
        spread = {"left": max(lefts) - min(lefts), "center": max(centres) - min(centres),
                  "right": max(rights) - min(rights)}
        align = min(spread, key=spread.get)
    x = {"left": statistics.mean(lefts), "center": statistics.mean(centres),
         "right": statistics.mean(rights)}[align]
    return dict(lines=[l["text"] for l in ll], size=size, align=align, x=x,
                cy=statistics.mean(l["cy"] for l in ll))


def placed_label(n, tb):
    """spacing that puts a vertex label's block where the measurements put it"""
    x0, x1 = n["x"], n["x"] + n["w"]
    sp = dict(spacing=0)
    if tb["align"] == "left":
        sp["spacingLeft"] = tb["x"] - x0
    elif tb["align"] == "right":
        sp["spacingRight"] = x1 - tb["x"]
    else:
        d = tb["x"] - (x0 + x1) / 2        # shift the centre by d
        sp["spacingLeft" if d > 0 else "spacingRight"] = 2 * abs(d)
    d = tb["cy"] - (n["y"] + n["h"] / 2)
    sp["spacingTop" if d > 0 else "spacingBottom"] = 2 * abs(d)
    return sp


def font_style(bold, italic):
    return (1 if bold else 0) | (2 if italic else 0)


def along(pts, p):
    """where on the polyline pts the point nearest p lies: (fraction of the
    length 0..1, that point)"""
    total = sum(math.dist(a, b) for a, b in zip(pts, pts[1:])) or 1.0
    best, run = None, 0.0
    for a, b in zip(pts, pts[1:]):
        L = math.dist(a, b) or 1e-9
        t = max(0.0, min(1.0, ((p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])) / L / L))
        q = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
        d = math.dist(p, q)
        if best is None or d < best[0]:
            best = (d, (run + t * L) / total, q)
        run += L
    return best[1], best[2]


def cell(ident, value, kind, props, attrs, geometry):
    """One cell. With a kind, it is wrapped in draw.io's <object>, which holds
    the cell's id and label and the element's own data as custom properties
    (draw.io's Edit Data): its kind in the model (ubl-kind) and, on a flow, the
    id of the guard that labels it (ubl-guard). They keep what the SVG says in
    its data- attributes, so a draw.io file can be read back into the JSONs."""
    if not kind:
        return '<mxCell id="%s" value="%s" %s>%s</mxCell>' % (esc(ident), esc(value), attrs, geometry)
    data = "".join(' %s="%s"' % (k, esc(v)) for k, v in props.items() if v)
    return ('<object id="%s" label="%s" ubl-kind="%s"%s><mxCell %s>%s</mxCell></object>'
            % (esc(ident), esc(value), esc(kind), data, attrs, geometry))


def lane_of(spec, n):
    """The lane a node lies wholly inside, or None. A node across a lane
    boundary - a document passed between the parties, drawn on the divider -
    belongs to neither lane: it is a top-level cell, drawn over both lanes, so
    the divider runs under it as in the SVG."""
    for l in spec["lanes"]:
        if l["x"] <= n["x"] and n["x"] + n["w"] <= l["x"] + l["w"]:
            return l
    return None


def mxfile(spec):
    S, F = spec["stroke"], spec["font"]
    W, H = spec["canvas"]["w"], spec["canvas"]["h"]
    fam = F["family"].split(",")[0].strip()
    fb = spec.get("frameBox") or [S["frame"] / 2, S["frame"] / 2, W - S["frame"] / 2, H - S["frame"] / 2]
    cells = []

    def vertex(ident, value, st, x, y, w, h, parent="1", kind=None, **props):
        cells.append(cell(ident, value, kind, props,
                          'style="%s" vertex="1" parent="%s"' % (st, parent),
                          '<mxGeometry x="%s" y="%s" width="%s" height="%s" as="geometry"/>'
                          % (num(x), num(y), num(w), num(h))))

    # the activity's frame: a plain box at the measured weight, under everything
    vertex("frame", "", style(rounded=0, fillColor="none", strokeColor="#000000",
                              strokeWidth=float(S["frame"]), connectable=0, html=1),
           fb[0], fb[1], fb[2] - fb[0], fb[3] - fb[1], kind="frame")

    # Lanes are draw.io swimlanes, so a node dropped in a lane belongs to it. A
    # measured divider that runs from frame to frame on a lane boundary is drawn
    # as the lanes' own border; any other divider is a line of its own and the
    # lanes' borders are hidden.
    dividers = [d if isinstance(d, (list, tuple)) else [d, S["divider"], 0.0, H]
                for d in spec.get("dividers", [])]
    bounds = {round(l["x"] + l["w"], 1) for l in spec["lanes"][:-1]}
    reach = S["frame"] + 3.0
    as_border = [d for d in dividers
                 if round(d[0], 1) in bounds and d[2] <= fb[1] + reach and d[3] >= fb[3] - reach]
    lane_stroke = as_border[0][1] if as_border and len(as_border) == len(dividers) \
        and len(as_border) == len(bounds) else None
    for i, l in enumerate(spec["lanes"]):
        size = l.get("size") or F["lane"]
        # the title's middle where it was measured: its baseline less 0.35 of
        # its size, as the SVG sets it; startSize is twice that
        cy = l["baseline"] - size * 0.35 if l.get("baseline") else l.get("cy", size)
        d = l.get("cx", l["x"] + l["w"] / 2) - (l["x"] + l["w"] / 2)
        st = style(swimlane="", horizontal=1, startSize=2 * cy, swimlaneLine=0, collapsible=0, html=1,
                   fillColor="none", strokeColor="#000000" if lane_stroke else "none",
                   strokeWidth=float(lane_stroke or S["divider"]), fontFamily=fam,
                   fontSize=float(size), fontStyle=1 if l.get("bold") else 0,
                   spacing=0, **{"spacingLeft" if d > 0 else "spacingRight": 2 * abs(d)})
        vertex(l.get("id") or "lane%d" % i, l["title"], st.replace("swimlane=;", "swimlane;"),
               l["x"], 0, l["w"], H, kind="lane")
    if not lane_stroke:
        for i, d in enumerate(dividers):
            vertex("divider%d" % i, "", style(shape="line", direction="south", html=1,
                                               strokeWidth=float(d[1]), strokeColor="#000000",
                                               connectable=0),
                   d[0] - 5, d[2], 10, d[3] - d[2], kind="lane-divider")

    for i, gr in enumerate(spec.get("greyRules", [])):
        # a rule the artwork draws in grey beside a divider: black at its own
        # width, the whole height or width, as the SVG draws it (the diagrams
        # use no grey, the TC 2026-09-27); a line cell of its own
        c = gr["at"] + gr["w"] / 2
        if gr["axis"] == "v":
            geo = (c - 5, 0, 10, H)
        else:
            geo = (0, c - 5, W, 10)
        vertex("greyrule%d" % i, "", style(shape="line", direction="south" if gr["axis"] == "v" else "east",
                                           html=1, strokeWidth=float(gr["w"]), strokeColor="#000000",
                                           connectable=0),
               *geo, kind="lane-divider", **{"ubl-artwork-tone": gr.get("colour")})

    grow = {n["id"]: min(4.0, (n["w"] + 8) / 5, (n["h"] + 8) / 5)
            for n in spec["nodes"] if n["kind"] == "initial"}
    for n in spec["nodes"]:
        k = n["kind"]
        lane = lane_of(spec, n)
        parent, ox = (lane["id"], lane["x"]) if lane and lane.get("id") else ("1", 0.0)
        x, y, w, h = n["x"] - ox, n["y"], n["w"], n["h"]
        value, st = "", ""
        if k in ("action", "object", "decision", "note"):
            tb = text_block(n, F["node"])
            value = html_lines(tb["lines"])
            bold = n.get("bold") if n.get("bold") is not None else k in ("action", "object")
            italic = n.get("italic") if n.get("italic") is not None else k == "object"
            text = dict(html=1, whiteSpace="wrap", fontFamily=fam, fontSize=float(tb["size"]),
                        fontStyle=font_style(bold, italic), align=tb["align"],
                        verticalAlign="middle", **placed_label(n, tb))
        if k == "action":
            # draw.io rounds a corner with one radius; the artwork's are a
            # little elliptical (rx, ry), so their mean is taken
            r = (n.get("rx", h / 2) + n.get("ry", n.get("rx", h / 2))) / 2
            st = style(rounded=1, absoluteArcSize=1, arcSize=2 * r, fillColor="#ffffff",
                       strokeColor="#000000", strokeWidth=float(S["action"]), **text)
        elif k == "object":
            st = style(rounded=0, fillColor="#ffffff", strokeColor="#000000",
                       strokeWidth=float(S["object"]), **text)
        elif k == "decision":
            st = style(rhombus="", fillColor="#ffffff", strokeColor="#000000",
                       strokeWidth=float(S["action"]), **text).replace("rhombus=;", "rhombus;")
        elif k == "note":
            st = style(shape="note", size=float(n.get("fold") or min(w, h) * 0.30),
                       fillColor="#ffffff", strokeColor="#000000",
                       strokeWidth=float(S["action"]), **text)
        elif k == "initial":
            # draw.io's start state draws its disc inset by min(4, w/5, h/5)
            # inside its box; the box is grown by that much, so the disc is the
            # one measured
            g = grow[n["id"]]
            x, y, w, h = x - g, y - g, w + 2 * g, h + 2 * g
            st = style(ellipse="", shape="startState", fillColor="#000000",
                       strokeColor="none", html=1).replace("ellipse=;", "ellipse;")
        elif k == "final":
            # draw.io's end state insets its disc by at most 4px; the artwork's
            # ring is wider (innerRatio), which draw.io cannot say
            st = style(ellipse="", shape="endState", fillColor="#000000", strokeColor="#000000",
                       strokeWidth=float(S["action"]), html=1).replace("ellipse=;", "ellipse;")
        elif k == "fork":
            # the fork/join bar of draw.io's UML palette: a box filled with its
            # own stroke colour, horizontal or upright as measured
            st = style(html=1, points="[]", perimeter="orthogonalPerimeter",
                       fillColor="strokeColor", strokeColor="#000000", strokeWidth=0.0)
        vertex(n["id"], value, st, x, y, w, h, parent, kind=k)

    # Edges. A hop is draw.io's own line jump (jumpStyle=arc), set only on the
    # flows the TC's rule hops. draw.io jumps an edge only over edges drawn
    # before it, so the hopping flows go last; a dashed flow is never jumped
    # (noJump=1). jumpSize is chosen so draw.io's radius, (jumpSize-2)/2 plus
    # the stroke, is the SVG's.
    hops = bd.line_hops(spec)
    r = bd.hop_radius(spec)
    mw = spec.get("arrow", 20)
    mh = spec.get("arrowWidth") or mw
    # The SVG's open head (build_diagram.py's marker) has barbs 0.8 of the
    # measured length long and, each side, 0.4 of the measured width less half
    # a stroke across, centre-line to centre-line. draw.io's open head has barbs
    # size + stroke long and half that across: it cannot be longer than it is
    # wide. The size that fits both best is taken.
    end_size = 0.4 * (mw + mh) - 1.5 * S["edge"]
    guards = {g["onFlow"]: g for g in spec.get("guards", []) if g.get("onFlow")}
    order = [i for i in range(len(spec["edges"])) if i not in hops] + sorted(hops)
    for i in order:
        e = spec["edges"][i]
        pts = bd.polyline(spec, e)
        fx, fy = e.get("exitXY") or bd.SIDE[e["exit"]]
        tx, ty = e.get("entryXY") or bd.SIDE[e["entry"]]

        def regrown(ident, f):
            """a contact point as a fraction of a grown box"""
            n, g = spec["byid"][ident], grow.get(ident, 0.0)
            return ((f[0] * n["w"] + g) / (n["w"] + 2 * g), (f[1] * n["h"] + g) / (n["h"] + 2 * g))
        fx, fy = regrown(e["from"], (fx, fy))
        tx, ty = regrown(e["to"], (tx, ty))
        kv = dict(edgeStyle="none" if e.get("straight") else "orthogonalEdgeStyle", rounded=0,
                  html=1, endArrow="open", endFill=0, endSize=end_size,
                  strokeColor="#000000", strokeWidth=float(S["edge"]),
                  exitX=fx, exitY=fy, exitPerimeter=0, entryX=tx, entryY=ty, entryPerimeter=0)
        if e.get("arrowBoth"):
            kv.update(startArrow="open", startFill=0, startSize=end_size)
        if e.get("dash"):
            kv.update(dashed=1, dashPattern="%s %s" % (num(e["dash"] / S["edge"]),
                                                       num(e["gap"] / S["edge"])), noJump=1)
        if i in hops:
            kv.update(jumpStyle="arc", jumpSize=int(round(2 * (r - S["edge"]) + 2)))
        value, geo = "", '<mxGeometry relative="1" as="geometry">'
        g = guards.get(e.get("id"))
        if g is not None:
            # the guard is the edge's own label, so it moves with the flow; it
            # stands where the SVG has it: at the nearest point of the line,
            # plus an offset
            tb = text_block(g, F["guard"])
            value = html_lines(tb["lines"])
            t, q = along(pts, (tb["x"], tb["cy"]))
            ground = bd.guard_ground(g, pts)
            kv.update(fontFamily=fam, fontSize=float(tb["size"]), fontStyle=0, align=tb["align"],
                      verticalAlign="middle", labelBackgroundColor="#ffffff" if ground else "none")
            geo = ('<mxGeometry x="%s" relative="1" as="geometry">'
                   '<mxPoint x="%s" y="%s" as="offset"/>'
                   % (num(2 * t - 1), num(tb["x"] - q[0]), num(tb["cy"] - q[1])))
        inner = e.get("points") or []
        if inner and not e.get("straight"):
            inner = pts[1:-1]
        if inner:
            geo += '<Array as="points">%s</Array>' % "".join(
                '<mxPoint x="%s" y="%s"/>' % (num(p[0]), num(p[1])) for p in inner)
        cells.append(cell(e.get("id") or "e%d" % i, value, "flow",
                          {"ubl-guard": g and g.get("id")},
                          'style="%s" edge="1" parent="1" source="%s" target="%s"'
                          % (style(**kv), esc(e["from"]), esc(e["to"])), geo + "</mxGeometry>"))

    for g in spec.get("guards", []):
        if g.get("onFlow"):
            continue
        # a text that labels no flow - a decision's question, a remark - is a
        # free text cell
        tb = text_block(g, F["guard"])
        vertex(g.get("id"), html_lines(tb["lines"]),
               style(text="", html=1, fontFamily=fam, fontSize=float(tb["size"]), align=tb["align"],
                     verticalAlign="middle", spacing=0, **placed_label(g, tb)).replace("text=;", "text;"),
               g["x"], g["y"], g["w"], g["h"], kind=g.get("role", "text"))
    missing = [k for k in ("bands", "bandLabels", "dashed", "openEnds", "crossMarks",
                           "captions") if spec.get(k)]
    if missing:
        print("  not yet drawn by the proof of concept: %s" % ", ".join(missing), file=sys.stderr)

    model = ('<mxGraphModel dx="%d" dy="%d" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" '
             'arrows="1" fold="1" page="1" pageScale="1" pageWidth="%d" pageHeight="%d" math="0" shadow="0">'
             '<root><mxCell id="0"/><mxCell id="1" parent="0"/>%s</root></mxGraphModel>'
             % (round(W), round(H), math.ceil(W), math.ceil(H), "".join(cells)))
    return ('<mxfile host="UBL-TC" agent="UBL artwork pipeline, draw.io proof of concept" type="device">'
            '<diagram id="%s" name="%s">%s</diagram></mxfile>'
            % (esc(spec.get("name", "figure")), esc(spec.get("name", "figure")), model))


def main(spec_path, out):
    spec = bd.load(spec_path)
    bd.clear_guards(spec)              # the guards where the SVG draws them
    spec.setdefault("name", os.path.basename(out).rsplit(".", 1)[0])
    open(out, "w", encoding="utf-8").write(mxfile(spec) + "\n")
    print("  %s   (%d nodes, %d edges)" % (out, len(spec["nodes"]), len(spec["edges"])))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
