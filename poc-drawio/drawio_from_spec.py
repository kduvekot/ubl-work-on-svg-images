#!/usr/bin/env python3
"""A native draw.io model of a figure, as close to its SVG as draw.io allows.

    python3 drawio_from_spec.py <spec.json> <out.drawio> [<figure>-diagram.json]

The diagram JSON, when given, adds what the spec does not carry: where a flow
leaving the page continues, and which guard labels it.

Proof of concept, kept apart from the pipeline: it reads the same spec as
tools/build_diagram.py (made by tools/spec_from_model.py from the JSONs) and
reuses its geometry - the guards moved off their lines, the hops, the routed
lines - without changing it. Where draw.io has a native way to say something
(a swimlane, a fork bar, an edge label, a line jump) that is used, set to the
measured sizes; where draw.io cannot say what the SVG says, the nearest native
setting is taken and the difference is written up in poc-drawio/README.md.
"""
import json, math, os, statistics, sys, xml.etree.ElementTree as ET, xml.sax.saxutils as su

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


def caption_block(c, F):
    """a caption (a phase's title, a guard the reading took for a title) as a
    text block: one line, centred where the SVG sets it"""
    size = c.get("size") or F["lane"]
    cy = c["baseline"] - size * 0.35 if c.get("baseline") else c["cy"]
    return dict(lines=c["text"].split("\n"), size=size, align="center", x=c["cx"], cy=cy)


def free_edge(cells, ident, kind, pts, kv, props=None, value="", src=None, dst=None):
    """An edge that is not a flow between two nodes: a flow leaving the page
    (one end on its node, one end free) or a plain stroke (both ends free). A
    free end is a sourcePoint or targetPoint, the points between are
    waypoints; `src`/`dst` is (node id, fraction of its box) for an attached
    end."""
    kv = dict(kv)
    geo = ""
    if src:
        kv.update(exitX=src[1][0], exitY=src[1][1], exitPerimeter=0)
    else:
        geo += '<mxPoint x="%s" y="%s" as="sourcePoint"/>' % (num(pts[0][0]), num(pts[0][1]))
    if dst:
        kv.update(entryX=dst[1][0], entryY=dst[1][1], entryPerimeter=0)
    else:
        geo += '<mxPoint x="%s" y="%s" as="targetPoint"/>' % (num(pts[-1][0]), num(pts[-1][1]))
    if len(pts) > 2:
        geo += '<Array as="points">%s</Array>' % "".join(
            '<mxPoint x="%s" y="%s"/>' % (num(p[0]), num(p[1])) for p in pts[1:-1])
    ends = (' source="%s"' % esc(src[0]) if src else "") + (' target="%s"' % esc(dst[0]) if dst else "")
    cells.append(cell(ident, value, kind, props or {},
                      'style="%s" edge="1" parent="1"%s' % (style(**kv), ends),
                      '<mxGeometry relative="1" as="geometry">%s</mxGeometry>' % geo))


def touching(n, p, tol=4.0):
    """the fraction of n's box at point p, when p lies on (or within tol of) its
    outline; else None"""
    x0, y0, x1, y1 = n["x"], n["y"], n["x"] + n["w"], n["y"] + n["h"]
    if not (x0 - tol <= p[0] <= x1 + tol and y0 - tol <= p[1] <= y1 + tol):
        return None
    return (max(0.0, min(1.0, (p[0] - x0) / n["w"])), max(0.0, min(1.0, (p[1] - y0) / n["h"])))


def mxfile(spec, model=None):
    S, F = spec["stroke"], spec["font"]
    model = model or {}
    offpage = {o["id"]: o for o in model.get("offPage", [])}
    offpage_guard = {o["guard"]: o["id"] for o in offpage.values() if o.get("guard")}
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
                              strokeWidth=float(S["frame"]), connectable=0, pointerEvents=0, html=1),
           fb[0], fb[1], fb[2] - fb[0], fb[3] - fb[1], kind="frame")

    phase_titles = {c["id"]: c for c in spec.get("captions", []) if c.get("role") == "phase-title"}
    for i, d in enumerate(spec.get("dashed", [])):
        # a CPFR phase: the dashed rounded box the diagram is drawn inside, at
        # the artwork's dash, gap and corner; its title is the box's own label,
        # at the top, where it was measured. Under the lanes, as in the SVG,
        # and with pointerEvents=0: a click inside it reaches the action
        # there, not the box (in the editor, a drag meant for an action moved
        # the phase box into a lane)
        ident = d.get("id") or "phase%d" % i
        wt = d.get("weight") or S["divider"]
        kv = dict(rounded=1, absoluteArcSize=1, arcSize=2 * d["rx"], fillColor="none",
                  strokeColor="#000000", strokeWidth=float(wt), dashed=1,
                  dashPattern="%s %s" % (num(max(d["dash"], 0.5) / wt), num(max(d["gap"], 0.5) / wt)),
                  connectable=0, pointerEvents=0, html=1, whiteSpace="nowrap")
        title = ""
        c = phase_titles.get(ident)
        if c:
            tb = caption_block(c, F)
            title = html_lines(tb["lines"])
            dx = tb["x"] - (d["x"] + d["w"] / 2)
            if spec.get("house"):
                # the house style: the title on a white ground, where a lane
                # divider runs through it
                kv.update(labelBackgroundColor="#ffffff")
            kv.update(fontFamily=fam, fontSize=float(tb["size"]), fontStyle=1 if c.get("bold") else 0,
                      align="center", verticalAlign="top", spacing=0,
                      spacingTop=tb["cy"] - 0.6 * tb["size"] - d["y"],
                      **{"spacingLeft" if dx > 0 else "spacingRight": 2 * abs(dx)})
        vertex(ident, title, style(**kv), d["x"], d["y"], d["w"], d["h"], kind="phase-boundary")

    # Lanes are draw.io swimlanes, so a node dropped in a lane belongs to it;
    # expand=0 keeps a lane its size when something is dropped across its
    # edge (draw.io widened the lane over its neighbour otherwise). A
    # measured divider that runs from frame to frame on a lane boundary is drawn
    # as the lanes' own border; any other divider is a line of its own and the
    # lanes' borders are hidden.
    dividers = [d if isinstance(d, (list, tuple)) else [d, S["divider"], 0.0, H]
                for d in spec.get("dividers", [])]
    bounds = {round(l["x"] + l["w"], 1) for l in spec["lanes"][:-1]}
    reach = S["frame"] + 3.0
    as_border = [d for d in dividers
                 if round(d[0], 1) in bounds and d[2] <= fb[1] + reach and d[3] >= fb[3] - reach]
    # ... and only when the frame's line is at least as heavy: a lane's outer
    # borders lie on the frame, and a heavier one would show beside it (the
    # Tender figures draw 9.5px dividers inside a 4.3px frame)
    lane_stroke = as_border[0][1] if as_border and len(as_border) == len(dividers) \
        and len(as_border) == len(bounds) and max(d[1] for d in as_border) <= S["frame"] \
        and len({d[1] for d in as_border}) == 1 else None
    # A lane runs from the frame to the frame, not from the page's edge: its
    # outer borders then lie under the frame's heavier line, and no stroke
    # reaches past the page, which draw.io answers by adding a ring of pages
    # round the drawing and opening it at a quarter of its size.
    lane_box = {}
    for i, l in enumerate(spec["lanes"]):
        x0, x1 = max(l["x"], fb[0]), min(l["x"] + l["w"], fb[2])
        lane_box[l.get("id")] = (x0, fb[1])
        size = l.get("size") or F["lane"]
        # the title's middle where it was measured: its baseline less 0.35 of
        # its size, as the SVG sets it; startSize is twice its depth in the lane
        cy = (l["baseline"] - size * 0.35 if l.get("baseline") else l.get("cy", size)) - fb[1]
        d = l.get("cx", (x0 + x1) / 2) - (x0 + x1) / 2
        st = style(swimlane="", expand=0, horizontal=1, startSize=2 * cy, swimlaneLine=0, collapsible=0, html=1,
                   fillColor="none", strokeColor="#000000" if lane_stroke else "none",
                   strokeWidth=float(lane_stroke or S["divider"]), fontFamily=fam,
                   fontSize=float(size), fontStyle=1 if l.get("bold") else 0,
                   spacing=0, **{"spacingLeft" if d > 0 else "spacingRight": 2 * abs(d)})
        vertex(l.get("id") or "lane%d" % i, l["title"], st.replace("swimlane=;", "swimlane;"),
               x0, fb[1], x1 - x0, fb[3] - fb[1], kind="lane")
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
        # (frame to frame: the frame's line covers the rest, and nothing
        # reaches past the page)
        if gr["axis"] == "v":
            geo = (c - 5, fb[1], 10, fb[3] - fb[1])
        else:
            geo = (fb[0], c - 5, fb[2] - fb[0], 10)
        vertex("greyrule%d" % i, "", style(shape="line", direction="south" if gr["axis"] == "v" else "east",
                                           html=1, strokeWidth=float(gr["w"]), strokeColor="#000000",
                                           connectable=0),
               *geo, kind="lane-divider", **{"ubl-artwork-tone": gr.get("colour")})

    for i, b in enumerate(spec.get("bands", [])):
        # a band's rule across the lanes (the 2.3 customs figures' rule under
        # the lane titles; IMFM's planning, execution and completion): a line
        # cell, where and as heavy as measured
        at, wt, a, z = (b, S["divider"], 0.0, W) if not isinstance(b, (list, tuple)) else \
            (b[0], b[1] if len(b) > 1 else S["divider"], b[2] if len(b) > 3 else 0.0, b[3] if len(b) > 3 else W)
        vertex("band%d" % i, "", style(shape="line", html=1, strokeWidth=float(wt), strokeColor="#000000",
                                       connectable=0),
               a, at - 5, z - a, 10, kind="band-divider")
    for i, b in enumerate(spec.get("bandLabels", [])):
        # a band's title, running up the gutter: draw.io's vertical text
        # (horizontal=0), which reads upwards as the SVG's rotate(-90) does
        size = F["lane"]
        long_ = 0.62 * size * len(b["title"]) + size
        vertex(b.get("id") or "bandtitle%d" % i, su.escape(b["title"]),
               style(text="", html=1, horizontal=0, whiteSpace="nowrap", fontFamily=fam,
                     fontSize=float(size), fontStyle=1 if b.get("bold") else 0, align="center",
                     verticalAlign="middle", spacing=0).replace("text=;", "text;"),
               b["cx"] - size, b["cy"] - long_ / 2, 2 * size, long_, kind="band-title")

    grow = {n["id"]: min(4.0, (n["w"] + 8) / 5, (n["h"] + 8) / 5)
            for n in spec["nodes"] if n["kind"] == "initial"}
    for n in spec["nodes"]:
        k = n["kind"]
        lane = lane_of(spec, n)
        parent, (ox, oy) = (lane["id"], lane_box[lane["id"]]) if lane and lane.get("id") else ("1", (0.0, 0.0))
        x, y, w, h = n["x"] - ox, n["y"] - oy, n["w"], n["h"]
        value, st = "", ""
        if k in ("action", "object", "decision", "note"):
            tb = text_block(n, F["node"])
            value = html_lines(tb["lines"])
            bold = n.get("bold") if n.get("bold") is not None else k in ("action", "object")
            italic = n.get("italic") if n.get("italic") is not None else k == "object"
            # nowrap: the lines break where the artwork breaks them (the
            # label's own <br>), never where draw.io finds the box too narrow
            # - with wrap on, a line that nearly fills its box went onto two
            # (CRP Synchronizing's "Synchronize stock information")
            text = dict(html=1, whiteSpace="nowrap", fontFamily=fam, fontSize=float(tb["size"]),
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
            # the fork/join bar of draw.io's UML palette, horizontal or upright
            # as measured. The palette fills it with "strokeColor"; inside a
            # lane whose own stroke is none (a divider drawn as a line of its
            # own) draw.io resolved that to nothing and the bar vanished, so
            # it is filled black outright
            st = style(html=1, points="[]", perimeter="orthogonalPerimeter",
                       fillColor="#000000", strokeColor="none")
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
    # the 2.3 transport figures' filled head, notched at the back three
    # quarters of the way, is draw.io's classic head, filled
    head, fill = ("classic", 1) if spec.get("arrowStyle") == "filled" else ("open", 0)
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
                  html=1, endArrow=head, endFill=fill, endSize=end_size,
                  strokeColor="#000000", strokeWidth=float(S["edge"]),
                  exitX=fx, exitY=fy, exitPerimeter=0, entryX=tx, entryY=ty, entryPerimeter=0)
        if e.get("arrowBoth"):
            kv.update(startArrow=head, startFill=fill, startSize=end_size)
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

    # Flows that leave the page. One end lies on its node and is attached
    # there, so the flow moves with it; the other end is free, where the
    # artwork runs it off the page. The model says where it continues (the
    # figure and its counterpart flow there) and which guard labels it: the
    # guard is the flow's own label, as on any other flow.
    guard_text = {g["id"]: (g, text_block(g, F["guard"])) for g in spec.get("guards", [])}
    guard_text.update({c["id"]: (c, caption_block(c, F)) for c in spec.get("captions", [])
                       if c.get("role") != "phase-title"})
    used = set()
    ids = {e.get("id") for e in spec["edges"]}
    for i, oe in enumerate(spec.get("openEnds", [])):
        pts = [tuple(p) for p in oe["points"]]
        base = dict(edgeStyle="none", rounded=0, html=1, strokeColor="#000000",
                    strokeWidth=float(S["edge"]), endArrow=head if oe.get("arrow") else "none",
                    endFill=fill, endSize=end_size)
        ident = oe.get("id") or "open%d" % i
        if oe.get("role") == "lane-divider" or ident not in offpage:
            # a piece of a divider the reading took for a flow, or the stretch
            # of a flow run down a divider after it leaves it: a plain stroke,
            # both ends free
            if ident in ids:
                ident += "-continued"
            free_edge(cells, ident, oe.get("role") or "line", pts, base)
            continue
        om = offpage[ident]
        n = spec["byid"].get(om.get("node"))
        src = dst = None
        if n is not None:
            # the artwork can stop an arrow's tip a few pixels short of the
            # outline (CPFR Exception Handling: 5.9px); up to half an
            # arrowhead off still counts as meeting the node
            tol = max(4.0, mw / 2)
            a, z = touching(n, pts[0], tol), touching(n, pts[-1], tol)
            if a is not None and (z is None or math.dist(pts[0], (n["x"] + n["w"] / 2, n["y"] + n["h"] / 2))
                                  <= math.dist(pts[-1], (n["x"] + n["w"] / 2, n["y"] + n["h"] / 2))):
                src = (n["id"], a)
            elif z is not None:
                dst = (n["id"], z)
        value = ""
        if om.get("guard") in guard_text:
            g, tb = guard_text[om["guard"]]
            used.add(om["guard"])
            value = html_lines(tb["lines"])
            t, q = along(pts, (tb["x"], tb["cy"]))
            base.update(fontFamily=fam, fontSize=float(tb["size"]), fontStyle=0, align=tb["align"],
                        verticalAlign="middle", labelBackgroundColor="none")
        props = {"ubl-continues": om.get("continues"), "ubl-counterpart": om.get("counterpart"),
                 "ubl-port": str(om["port"]) if om.get("port") is not None else None,
                 "ubl-direction": om.get("direction"), "ubl-guard": om.get("guard")}
        free_edge(cells, ident, "off-page-flow", pts, base, props, value, src, dst)
        if value:
            # the label's place: as for a guard, a fraction along the flow and an offset
            c = cells[-1]
            cells[-1] = c.replace('<mxGeometry relative="1" as="geometry">',
                                  '<mxGeometry x="%s" relative="1" as="geometry"><mxPoint x="%s" y="%s" as="offset"/>'
                                  % (num(2 * t - 1), num(tb["x"] - q[0]), num(tb["cy"] - q[1])), 1)
    for i, m in enumerate(spec.get("crossMarks", [])):
        # a short stroke across a partition rule: a plain line, both ends free
        free_edge(cells, m.get("id") or "mark%d" % i, "mark", [(m["x1"], m["y1"]), (m["x2"], m["y2"])],
                  dict(edgeStyle="none", rounded=0, html=1, endArrow="none", strokeColor="#000000",
                       strokeWidth=float(m.get("weight") or S["divider"])))

    for c in spec.get("captions", []):
        # a guard the reading took for a title, labelling no flow: a free text
        if c.get("role") == "phase-title" or c["id"] in used:
            continue
        g, tb = guard_text[c["id"]]
        box = dict(x=tb["x"] - (c.get("textWidth") or 40) / 2 - 4, y=tb["cy"] - tb["size"],
                   w=(c.get("textWidth") or 40) + 8, h=2 * tb["size"])
        vertex(c["id"], html_lines(tb["lines"]),
               style(text="", html=1, whiteSpace="nowrap", fontFamily=fam, fontSize=float(tb["size"]),
                     align="center", verticalAlign="middle", **placed_label(box, tb)).replace("text=;", "text;"),
               box["x"], box["y"], box["w"], box["h"], kind=c.get("role", "text"))
    for g in spec.get("guards", []):
        if g.get("onFlow") or g["id"] in used:
            continue
        # a text that labels no flow - a decision's question, a remark - is a
        # free text cell
        tb = text_block(g, F["guard"])
        vertex(g.get("id"), html_lines(tb["lines"]),
               style(text="", html=1, fontFamily=fam, fontSize=float(tb["size"]), align=tb["align"],
                     verticalAlign="middle", **placed_label(g, tb)).replace("text=;", "text;"),
               g["x"], g["y"], g["w"], g["h"], kind=g.get("role", "text"))

    # A margin round the drawing. draw.io grows an edge's bounds by its
    # arrowhead's size on every side, so a flow that runs off the page with a
    # head on it (the CPFR figures) reached past the page, and draw.io opened
    # the figure among a ring of extra pages. The page is one arrowhead wider
    # on each side and the drawing moved in by as much; the frame records the
    # offset (ubl-offset), and a reader of the file takes it off again.
    M = math.ceil(end_size + 2 * S["edge"]) + 2
    body = ET.fromstring('<root><mxCell id="0"/><mxCell id="1" parent="0"/>%s</root>' % "".join(cells))
    for c in body.iter("mxCell"):
        geo = c.find("mxGeometry")
        if geo is None:
            continue
        if c.get("vertex") == "1" and c.get("parent") == "1":
            geo.set("x", num(float(geo.get("x", 0)) + M))
            geo.set("y", num(float(geo.get("y", 0)) + M))
        if c.get("edge") == "1":
            for p in geo.iter("mxPoint"):
                if p.get("as") != "offset":
                    p.set("x", num(float(p.get("x", 0)) + M))
                    p.set("y", num(float(p.get("y", 0)) + M))
    for o in body.iter("object"):
        if o.get("ubl-kind") == "frame":
            o.set("ubl-offset", str(M))
    model = ('<mxGraphModel dx="%d" dy="%d" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" '
             'arrows="1" fold="1" page="1" pageScale="1" pageWidth="%d" pageHeight="%d" math="0" shadow="0">'
             '%s</mxGraphModel>'
             % (round(W), round(H), math.ceil(W) + 2 * M, math.ceil(H) + 2 * M,
                ET.tostring(body, encoding="unicode")))
    return ('<mxfile host="UBL-TC" agent="UBL artwork pipeline, draw.io proof of concept" type="device">'
            '<diagram id="%s" name="%s">%s</diagram></mxfile>'
            % (esc(spec.get("name", "figure")), esc(spec.get("name", "figure")), model))


def main(spec_path, out, model_path=None):
    spec = bd.load(spec_path)
    model = json.load(open(model_path, encoding="utf-8")) if model_path else None
    bd.clear_guards(spec)              # the guards where the SVG draws them
    spec.setdefault("name", os.path.basename(out).rsplit(".", 1)[0])
    open(out, "w", encoding="utf-8").write(mxfile(spec, model) + "\n")
    print("  %s   (%d nodes, %d edges)" % (out, len(spec["nodes"]), len(spec["edges"])))


if __name__ == "__main__":
    main(*sys.argv[1:4])
