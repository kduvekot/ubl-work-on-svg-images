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
import collections, json, math, os, statistics, sys, xml.etree.ElementTree as ET, xml.sax.saxutils as su

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import build_diagram as bd          # noqa: E402  (read only: geometry helpers)


def num(v, places=2):
    """a style or geometry number, without trailing noise"""
    return ("%.*f" % (places, v)).rstrip("0").rstrip(".")


# draw.io's own defaults, left out of a style as its palettes leave them out:
# a vertex is filled white and drawn black, and all text is Helvetica. (A
# drawing then also follows draw.io's dark theme on screen; print is black on
# white either way.)
DEFAULTS = {"fillColor": "#ffffff", "strokeColor": "#000000", "fontFamily": "Helvetica"}


def style(**kv):
    # a contact point is a fraction of the node's box: four places keep it
    # within a hundredth of a pixel
    return "".join("%s=%s;" % (k, num(v, 4 if k[:4] in ("exit", "entr") else 2)
                               if isinstance(v, float) else v) for k, v in kv.items()
                   if DEFAULTS.get(k) != v)


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
    lies wholly in neither: the writer puts it in the lane to the boundary's
    right, drawn after that lane, so the divider runs under it as in the SVG."""
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


def free_edge(cells, ident, kind, pts, kv, props=None, value="", src=None, dst=None, parent="1", at=(0.0, 0.0)):
    """An edge that is not a flow between two nodes: a flow leaving the page
    (one end on its node, one end free) or a plain stroke (both ends free). A
    free end is a sourcePoint or targetPoint, the points between are
    waypoints; `src`/`dst` is (node id, fraction of its box) for an attached
    end. `parent` is the container it belongs to and `at` that container's
    place on the page: its points are relative to it."""
    kv = dict(kv)
    geo = ""
    pts = [(p[0] - at[0], p[1] - at[1]) for p in pts]
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
                      'style="%s" edge="1" parent="%s"%s' % (style(**kv), esc(parent), ends),
                      '<mxGeometry relative="1" as="geometry">%s</mxGeometry>' % geo))


def straighten(body, lo=0.05, hi=8.0):
    """Make the flows the artwork draws almost level or upright (off by less
    than 8px) exactly so, by moving their elements, never their contact
    points: a level flow by moving an element up or down, an upright one left
    or right (which leaves the other kind as it is). Elements tied by such
    flows move together; in each group the element with the most of them
    (then the largest: mostly a document) stays where it was measured. A
    flow in a loop whose ends cannot all agree (IMFM, Fulfilment Receipt
    Advice) stays as it is. A bent flow or a flow leaving the page keeps its
    first or last stretch square: the bend (or free end) next to a moved
    element moves with it. Returns the flows left tilted."""
    info = {}
    for el in body:
        c = el if el.tag == "mxCell" else el.find("mxCell")
        if c is None:
            continue
        info[el.get("id")] = (el, c, c.find("mxGeometry"))

    def box(i):
        el, c, g = info[i]
        if g is None or g.get("relative") == "1" or c.get("edge") == "1":
            return (0.0, 0.0, 0.0, 0.0)
        px, py = box(c.get("parent"))[:2] if c.get("parent") in info else (0.0, 0.0)
        return (px + float(g.get("x", 0)), py + float(g.get("y", 0)),
                float(g.get("width", 0)), float(g.get("height", 0)))

    def kv(c):
        return dict(p.split("=", 1) for p in (c.get("style") or "").split(";") if "=" in p)

    def contact(i, fx, fy):
        b = box(i)
        return (b[0] + float(fx) * b[2], b[1] + float(fy) * b[3])
    edges = [(i, c, g, kv(c)) for i, (el, c, g) in info.items() if c.get("edge") == "1" and g is not None]
    shift = collections.defaultdict(lambda: [0.0, 0.0])
    tilted = []
    for k in (1, 0):            # level flows (moved in y), then upright ones (in x)
        adj = collections.defaultdict(list)
        for i, c, g, st in edges:
            a, b = c.get("source"), c.get("target")
            if not a or not b or g.find("Array") is not None:
                continue
            p, q = contact(a, st["exitX"], st["exitY"]), contact(b, st["entryX"], st["entryY"])
            d, other = q[k] - p[k], q[1 - k] - p[1 - k]
            if abs(d) < hi and abs(d) <= abs(other):
                adj[a].append((b, d, i))
                adj[b].append((a, -d, i))
        seen = set()
        for start in sorted(adj):
            if start in seen:
                continue
            comp, stack = {start}, [start]
            while stack:
                for v, _, _ in adj[stack.pop()]:
                    if v not in comp:
                        comp.add(v)
                        stack.append(v)
            seen |= comp
            b = {c: box(c) for c in comp}
            anchor = max(sorted(comp), key=lambda c: (len(adj[c]), b[c][2] * b[c][3]))
            by, stack = {anchor: 0.0}, [anchor]
            while stack:
                u = stack.pop()
                for v, d, i in adj[u]:
                    if v not in by:
                        by[v] = by[u] + d if abs(d) >= lo else by[u]
                        stack.append(v)
                    elif abs(by[v] - by[u] - d) >= lo and i not in tilted:
                        tilted.append(i)
            for c, dv in by.items():
                if abs(dv) >= lo:
                    # moved against the measurement by -dv: the flow's end
                    # comes to the other end's level
                    shift[c][k] -= dv
    for c, (dx, dy) in shift.items():
        g = info[c][2]
        g.set("x", num(float(g.get("x", 0)) + dx))
        g.set("y", num(float(g.get("y", 0)) + dy))
    # the bend or free end next to a moved element keeps its stretch square
    for i, c, g, st in edges:
        for end, key, pick in ((c.get("source"), "exit", 0), (c.get("target"), "entry", -1)):
            if not end or end not in shift:
                continue
            arr = g.find("Array")
            near = arr.findall("mxPoint")[pick] if arr is not None and len(arr) else \
                g.find('mxPoint[@as="%s"]' % ("targetPoint" if pick == 0 else "sourcePoint"))
            if near is None:
                continue
            dx, dy = shift[end]
            old = contact(end, st[key + "X"], st[key + "Y"])
            old = (old[0] - dx, old[1] - dy)
            ox, oy = box(c.get("parent"))[:2] if c.get("parent") in info else (0.0, 0.0)
            nx, ny = float(near.get("x", 0)) + ox, float(near.get("y", 0)) + oy
            if abs(ny - old[1]) < 0.5 <= abs(nx - old[0]):
                near.set("y", num(float(near.get("y", 0)) + dy))
            elif abs(nx - old[0]) < 0.5 <= abs(ny - old[1]):
                near.set("x", num(float(near.get("x", 0)) + dx))
    return tilted


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


    phase_titles = {c["id"]: c for c in spec.get("captions", []) if c.get("role") == "phase-title"}
    # a phase's or a lane's title the reading kept as a free text (CPFR
    # Establishing Collaborative Relationships and Exception Monitor; Waste
    # Movement's and Freight Status Reporting's lane names) is still that
    # phase box's or lane's own label, as draw.io has it, in its own weight
    phase_titles.update({g["id"]: g for g in spec.get("guards", []) if g.get("role") == "phase-title"
                         and g["id"] not in phase_titles})
    lane_titles = {g["id"][:-len("-title")]: g for g in spec.get("guards", [])
                   if g.get("role") == "lane-title" and g["id"].endswith("-title")}
    taken = set()
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
            tb = text_block(c, F["guard"]) if c.get("labelLines") else caption_block(c, F)
            title = html_lines(tb["lines"])
            taken.add(ident)
            dx = tb["x"] - (d["x"] + d["w"] / 2)
            kv.update(fontFamily=fam, fontSize=float(tb["size"]), fontStyle=1 if c.get("bold") else 0,
                      align="center", verticalAlign="top", spacing=0,
                      spacingTop=tb["cy"] - 0.6 * tb["size"] - d["y"],
                      **{"spacingLeft" if dx > 0 else "spacingRight": 2 * abs(dx)})
        vertex(ident, title, style(**kv), d["x"], d["y"], d["w"], d["h"], kind="phase-boundary")

    # the rule under the lane titles, across the whole frame and above every
    # node (the 2.3 customs figures, IMFM's top rule), is the lanes' own
    # header line (swimlaneLine), under a header as deep as the rule is low
    bands = [b if isinstance(b, (list, tuple)) else [b, S["divider"], 0.0, W] for b in spec.get("bands", [])]
    top = min((n["y"] for n in spec["nodes"]), default=H)
    header = next((b for b in sorted(bands) if b[0] < top and len(b) > 3
                   and b[3] - b[2] >= 0.9 * (fb[2] - fb[0])
                   and all(b[0] > (l.get("baseline") or l.get("cy", 0)) for l in spec["lanes"])), None)
    for i, b in enumerate(spec.get("bands", [])):
        if header is not None and bands[i] is header:
            continue
        # a band's rule across the lanes (the 2.3 customs figures' rule under
        # the lane titles; IMFM's planning, execution and completion): a line
        # cell, where and as heavy as measured - drawn before the lanes, so
        # under the actions in them, as the SVG has it (IMFM's Provide
        # Transportation Network Information spans two bands, and the rule
        # ran through it)
        at, wt, a, z = (b, S["divider"], 0.0, W) if not isinstance(b, (list, tuple)) else \
            (b[0], b[1] if len(b) > 1 else S["divider"], b[2] if len(b) > 3 else 0.0, b[3] if len(b) > 3 else W)
        vertex("band%d" % i, "", style(shape="line", html=1, strokeWidth=float(wt), strokeColor="#000000",
                                       connectable=0),
               a, at - 5, z - a, 10, kind="band-divider")

    # Lanes are draw.io swimlanes, so a node dropped in a lane belongs to it;
    # expand=0 keeps a lane its size when something is dropped across its
    # edge (draw.io widened the lane over its neighbour otherwise). A
    # measured divider on a lane boundary is drawn as the lanes' own border;
    # any other divider is a line of its own.
    dividers = [d if isinstance(d, (list, tuple)) else [d, S["divider"], 0.0, H]
                for d in spec.get("dividers", [])]
    # a divider on a lane boundary: within 1.5 px of it (the two are
    # measured apart and differ by a few tenths of a pixel in 37 figures)
    bounds = [l["x"] + l["w"] for l in spec["lanes"][:-1]]
    on_bound = {i: min(bounds, key=lambda b: abs(b - d[0])) for i, d in enumerate(dividers)
                if bounds and min(abs(b - d[0]) for b in bounds) <= 1.5}
    # Every divider on a lane boundary is the lanes' own border, as a lane in
    # draw.io has it: full height, and one weight for the figure - the median
    # of its dividers, never heavier than the frame. The artwork's heavier,
    # lighter or shorter dividers are its rendering, not a line of their own
    # (the Tender figures' 5-6 px inside a 4.3 px frame, CPFR's 0.4 px, GIP
    # Approval's that stop short of the frame).
    # A rule the artwork draws in grey on a lane boundary (within 3 px) is
    # that boundary's divider too: Procurement's grey edges either side of
    # its dividers, CPFR Creating Sales Forecast's only divider
    grey_on = [g for g in spec.get("greyRules", []) if g["axis"] == "v" and bounds
               and min(abs(b - g["at"] - g["w"] / 2) for b in bounds) <= 3.0]
    wts = sorted(dividers[i][1] for i in on_bound) or sorted(g["w"] for g in grey_on)
    lane_stroke = min(wts[len(wts) // 2] if len(wts) % 2 else (wts[len(wts) // 2 - 1] + wts[len(wts) // 2]) / 2,
                      S["frame"]) if wts else None
    # the lanes' edges then where the dividers were measured
    at_divider = {round(b, 3): dividers[i][0] for i, b in on_bound.items()}
    # A lane runs from the frame to the frame, not from the page's edge: its
    # outer borders then lie under the frame's heavier line, and no stroke
    # reaches past the page, which draw.io answers by adding a ring of pages
    # round the drawing and opening it at a quarter of its size.
    #
    # The frame is draw.io's pool (its BPMN palette's "Vertical Pool 1": a
    # swimlane that lays its lanes out side by side), at the frame's measured
    # weight and with no title bar of its own; the lanes are its lanes. So a
    # lane added, removed or widened in draw.io moves its neighbours along, as
    # in a pool drawn by hand. Nothing but lanes goes into the pool, which
    # would lay it out as one more lane: a document on a divider stays on the
    # page, over the pool.
    vertex("frame", "", style(swimlane="", html=1, childLayout="stackLayout", resizeParent=1, resizeParentMax=0,
                              startSize=0, whiteSpace="wrap", collapsible=0, fillColor="none",
                              strokeColor="#000000", strokeWidth=float(S["frame"])).replace("swimlane=;", "swimlane;"),
           fb[0], fb[1], fb[2] - fb[0], fb[3] - fb[1], kind="frame")
    lane_box = {}
    # the lanes edge to edge, from the frame's left to its right, as the
    # pool's layout keeps them
    order = sorted(range(len(spec["lanes"])), key=lambda i: spec["lanes"][i]["x"])
    edges_x = [fb[0]] + [at_divider.get(round(spec["lanes"][i]["x"] + spec["lanes"][i]["w"], 3),
                                        min(max(spec["lanes"][i]["x"] + spec["lanes"][i]["w"], fb[0]), fb[2]))
                         for i in order[:-1]] + [fb[2]]
    span = {i: (edges_x[k], edges_x[k + 1]) for k, i in enumerate(order)}
    for i, l in enumerate(spec["lanes"]):
        x0, x1 = span[i]
        lane_box[l.get("id")] = (x0, fb[1])
        g = lane_titles.get(l.get("id")) if not l.get("title") else None
        if g:
            tb = text_block(g, F["lane"])
            l = dict(l, title="\n".join(tb["lines"]), size=tb["size"], cy=tb["cy"], cx=tb["x"],
                     bold=g.get("bold"), baseline=None)
            taken.add(g["id"])
        size = l.get("size") or F["lane"]
        # the title's middle where it was measured: its baseline less 0.35 of
        # its size, as the SVG sets it; startSize is twice its depth in the lane
        cy = (l["baseline"] - size * 0.35 if l.get("baseline") else l.get("cy", size)) - fb[1]
        d = l.get("cx", (x0 + x1) / 2) - (x0 + x1) / 2
        head = dict(startSize=2 * cy, swimlaneLine=0)
        if header is not None:
            # the title's middle where it was measured, within the header
            dy = cy - (header[0] - fb[1]) / 2
            head = dict(startSize=header[0] - fb[1], swimlaneLine=1,
                        **{"spacingTop" if dy > 0 else "spacingBottom": 2 * abs(dy)})
        st = style(swimlane="", expand=0, horizontal=1, **head, collapsible=0, html=1,
                   fillColor="none", strokeColor="#000000" if lane_stroke else "none",
                   strokeWidth=float(lane_stroke or S["divider"]), fontFamily=fam,
                   fontSize=float(size), fontStyle=1 if l.get("bold") else 0,
                   spacing=0, **{"spacingLeft" if d > 0 else "spacingRight": 2 * abs(d)})
        # a title on two lines (Manifest's "Sending Logistics / Operator Party")
        # keeps its break: the label is html, where only <br> breaks a line
        vertex(l.get("id") or "lane%d" % i, html_lines(l["title"].split("\n")), st.replace("swimlane=;", "swimlane;"),
               x0 - fb[0], 0, x1 - x0, fb[3] - fb[1], parent="frame", kind="lane")
    # What stands at a place in the frame belongs to the lane there, and moves
    # with it when a lane beside it is widened in draw.io; on a lane's left
    # edge (a divider), to that lane - drawn after the lane, so over its border
    lanes_lr = [(span[i][0], span[i][1], spec["lanes"][i].get("id") or "lane%d" % i) for i in order]

    def lane_at(x):
        for x0, x1, ident in lanes_lr:
            if x0 - 0.01 <= x < x1 - 0.01:
                return ident, x0
        return lanes_lr[-1][2], lanes_lr[-1][0]

    def in_lane(x, y, w, h, at=None):
        """the parent and the place within it of a box at (x, y, w, h)"""
        ident, x0 = lane_at(x + w / 2 if at is None else at)
        return dict(parent=ident), x - x0, y - fb[1]

    # a divider not on a lane boundary: a line of its own
    for i, d in enumerate(dividers):
        if i not in on_bound:
            p, x, y = in_lane(d[0] - 5, d[2], 10, d[3] - d[2])
            vertex("divider%d" % i, "", style(shape="line", direction="south", html=1,
                                               strokeWidth=float(d[1]), strokeColor="#000000",
                                               connectable=0),
                   x, y, 10, d[3] - d[2], kind="lane-divider", **p)

    for i, gr in enumerate(spec.get("greyRules", [])):
        if any(gr is g for g in grey_on):
            continue
        # a rule the artwork draws in grey beside a divider: black at its own
        # width, the whole height or width, as the SVG draws it (the diagrams
        # use no grey, the TC 2026-09-27); a line cell of its own
        c = gr["at"] + gr["w"] / 2
        # (frame to frame: the frame's line covers the rest, and nothing
        # reaches past the page)
        p = {}
        if gr["axis"] == "v":
            p, x, y = in_lane(c - 5, fb[1], 10, fb[3] - fb[1])
            geo = (x, y, 10, fb[3] - fb[1])
        else:
            geo = (fb[0], c - 5, fb[2] - fb[0], 10)
        vertex("greyrule%d" % i, "", style(shape="line", direction="south" if gr["axis"] == "v" else "east",
                                           html=1, strokeWidth=float(gr["w"]), strokeColor="#000000",
                                           connectable=0),
               *geo, kind="lane-divider", **dict(p, **{"ubl-artwork-tone": gr.get("colour")}))

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
    home = {}
    # A text beside a decision, a start or an end - the decision's question,
    # where the flow comes from or goes to - is that node's own label, placed
    # beside it where the SVG has it, as draw.io labels a node outside its
    # shape; it then moves with the node. The nearest such node within 60px
    # takes it, one text to a node; any other text stays a text of its own.
    def gap(a, b):
        dx = max(b["x"] - a["x"] - a["w"], a["x"] - b["x"] - b["w"], 0)
        dy = max(b["y"] - a["y"] - a["h"], a["y"] - b["y"] - b["h"], 0)
        return math.hypot(dx, dy)
    loose = [(g, text_block(g, F["guard"])) for g in spec.get("guards", [])
             if not g.get("onFlow") and g["id"] not in taken and g["id"] not in offpage_guard
             and g.get("role") not in ("lane-title", "phase-title")]
    for c in spec.get("captions", []):
        if c.get("role") != "phase-title" and c["id"] not in offpage_guard:
            tb = caption_block(c, F)
            w = (c.get("textWidth") or 40) + 8
            loose.append((dict(c, x=tb["x"] - w / 2, y=tb["cy"] - tb["size"], w=w, h=2 * tb["size"]), tb))
    beside = sorted((gap(t, n), n["id"], t["id"], tb) for t, tb in loose for n in spec["nodes"]
                    if n["kind"] in ("decision", "initial", "final") and not (n.get("labelLines") or n.get("label")))
    node_text = {}
    for d, nid, tid, tb in beside:
        if d <= 60 and nid not in node_text and tid not in taken:
            node_text[nid] = tb
            taken.add(tid)
    for n in spec["nodes"]:
        k = n["kind"]
        lane = lane_of(spec, n)
        if lane and lane.get("id"):
            parent, (ox, oy) = lane["id"], lane_box[lane["id"]]
        else:
            # across a lane boundary (a document passed between the parties,
            # on the divider): in the lane to the boundary's right
            cuts = [x0 for x0, x1, ident in lanes_lr[1:] if n["x"] < x0 < n["x"] + n["w"]]
            at = min(cuts, key=lambda c: abs(c - (n["x"] + n["w"] / 2))) if cuts else None
            p, _, _ = in_lane(n["x"], n["y"], n["w"], n["h"], at)
            parent = p["parent"]
            ox, oy = lane_box[parent]
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
        if n["id"] in node_text:
            tb = node_text[n["id"]]
            value = html_lines(tb["lines"])
            g = grow.get(n["id"], 0.0)
            box = dict(x=n["x"] - g, y=n["y"] - g, w=n["w"] + 2 * g, h=n["h"] + 2 * g)
            sp = placed_label(box, tb)
            if k in ("initial", "final"):
                # draw.io sets a left- or right-aligned label on its start and
                # end states in from the side by the disc's inset, min(4, w/5,
                # h/5) (measured: 4px on a 58.6px state)
                inset = min(4.0, box["w"] / 5, box["h"] / 5)
                for key in ("spacingLeft", "spacingRight"):
                    if key in sp and tb["align"] != "center":
                        sp[key] -= inset
            text = dict(html=1, whiteSpace="nowrap", fontFamily=fam, fontSize=float(tb["size"]),
                        fontStyle=0, align=tb["align"], verticalAlign="middle", **sp)
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
                       strokeColor="none", **(text if n["id"] in node_text else dict(html=1))).replace("ellipse=;", "ellipse;")
        elif k == "final":
            # draw.io's end state insets its disc by at most 4px; the artwork's
            # ring is wider (innerRatio), which draw.io cannot say
            st = style(ellipse="", shape="endState", fillColor="#000000", strokeColor="#000000",
                       strokeWidth=float(S["action"]),
                       **(text if n["id"] in node_text else dict(html=1))).replace("ellipse=;", "ellipse;")
        elif k == "fork":
            # the fork/join bar of draw.io's UML palette, horizontal or upright
            # as measured. The palette fills it with "strokeColor"; inside a
            # lane whose own stroke is none (a divider drawn as a line of its
            # own) draw.io resolved that to nothing and the bar vanished, so
            # it is filled black outright
            st = style(html=1, points="[]", perimeter="orthogonalPerimeter",
                       fillColor="#000000", strokeColor="none")
        vertex(n["id"], value, st, x, y, w, h, parent, kind=k)
        home[n["id"]] = parent

    # Edges. A hop is draw.io's own line jump (jumpStyle=arc), set only on the
    # flows the TC's rule hops. draw.io jumps an edge only over edges drawn
    # before it, so the hopping flows go last; a dashed flow is never jumped
    # (noJump=1). jumpSize is chosen so draw.io's radius, (jumpSize-2)/2 plus
    # the stroke, is the SVG's.
    # A flow the reading found only in part (BusinessCard, DigitalCapability:
    # the document's flow runs down the lane divider, and only its last
    # stretch was read as a line of its own) is still that flow, when the
    # model names both its ends: attached to the document and the action, with
    # its bend where the stretch begins, so it moves with them
    model_flows = {f["id"]: f for f in model.get("flows", [])}
    spec_ids = {e.get("id") for e in spec["edges"]}
    joined = set()
    for oe in spec.get("openEnds", []):
        f = model_flows.get(oe.get("id"))
        if not f or oe["id"] in offpage or oe["id"] in spec_ids or oe.get("role") == "lane-divider" \
                or f["from"] not in spec["byid"] or f["to"] not in spec["byid"]:
            continue
        a, b = spec["byid"][f["from"]], spec["byid"][f["to"]]
        p, q = oe["points"][0], oe["points"][-1]
        if math.dist(q, (b["x"] + b["w"] / 2, b["y"] + b["h"] / 2)) > math.dist(p, (b["x"] + b["w"] / 2, b["y"] + b["h"] / 2)):
            p, q = q, p

        def side_point(n, pt):
            """pt carried straight onto n's outline, as a fraction"""
            return [min(max((pt[0] - n["x"]) / n["w"], 0.0), 1.0), min(max((pt[1] - n["y"]) / n["h"], 0.0), 1.0)]
        spec["edges"].append(dict(id=oe["id"], **{"from": f["from"], "to": f["to"]},
                                  exitXY=side_point(a, p), entryXY=side_point(b, q),
                                  points=[list(p)], confidence="joined"))
        joined.add(oe["id"])
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
    edge_pts = {}
    # A flow belongs to the container its two ends share, as draw.io files a
    # line drawn by hand: the lane when both are in one lane, else the pool;
    # its bends and free ends are relative to that container, so they move
    # with it (on the page, moving the pool had left them behind)
    origin = dict(lane_box, frame=(fb[0], fb[1]))
    origin["1"] = (0.0, 0.0)

    def shared(a, b=None):
        pa, pb = home.get(a, "1"), home.get(b, home.get(a, "1"))
        return pa if pa == pb else ("frame" if "1" not in (pa, pb) else "1")
    for i in order:
        e = spec["edges"][i]
        pts = bd.polyline(spec, e)
        edge_pts[e.get("id") or "e%d" % i] = pts
        fx, fy = e.get("exitXY") or bd.SIDE[e["exit"]]
        tx, ty = e.get("entryXY") or bd.SIDE[e["entry"]]

        def regrown(ident, f):
            """a contact point as a fraction of a grown box"""
            n, g = spec["byid"][ident], grow.get(ident, 0.0)
            return ((f[0] * n["w"] + g) / (n["w"] + 2 * g), (f[1] * n["h"] + g) / (n["h"] + 2 * g))
        if e.get("points") and not e.get("straight") and len(pts) > 2:
            # a bent flow drawn square in draw.io: its first and last stretch
            # must be level or upright, or draw.io adds a step of its own - a
            # stub of a few pixels at the box, and the arrowhead turned along
            # it (GoodsItemPassport's "Yes" into Apply Stamps: 2px off,
            # the head pointing up). The contact point moves onto the line of
            # the bend next to it, when they are a few pixels apart.
            def square(end, near, f, ident):
                n = spec["byid"][ident]
                dx, dy = near[0] - end[0], near[1] - end[1]
                if abs(dx) > abs(dy) and 0 < abs(dy) <= 6 and f[0] in (0.0, 1.0) and n["y"] < near[1] < n["y"] + n["h"]:
                    return (f[0], (near[1] - n["y"]) / n["h"])
                if abs(dy) > abs(dx) and 0 < abs(dx) <= 6 and f[1] in (0.0, 1.0) and n["x"] < near[0] < n["x"] + n["w"]:
                    return ((near[0] - n["x"]) / n["w"], f[1])
                return f
            fx, fy = square(pts[0], pts[1], (fx, fy), e["from"])
            tx, ty = square(pts[-1], pts[-2], (tx, ty), e["to"])
        if not e.get("points"):
            # a contact point within 2px of one of draw.io's own connection
            # points on that side (a quarter, the middle, three quarters of a
            # box's side; the tip of a diamond) is that point, as a line drawn
            # in draw.io would have it - unless that tilts a level or upright
            # line
            def snapped(ident, f):
                n = spec["byid"][ident]
                marks = {"action": (0.25, 0.5, 0.75), "object": (0.25, 0.5, 0.75), "note": (0.25, 0.5, 0.75),
                         "decision": (0.5,)}.get(n["kind"])
                if not marks:
                    return f
                f = list(f)
                for a, size in ((0, n["w"]), (1, n["h"])):
                    if f[1 - a] in (0.0, 1.0):
                        c = min(marks, key=lambda m: abs(m - f[a]))
                        if abs(c - f[a]) * size <= 2.0:
                            f[a] = c
                return tuple(f)

            def at(ident, f):
                n = spec["byid"][ident]
                return (n["x"] + f[0] * n["w"], n["y"] + f[1] * n["h"])
            sf, st = snapped(e["from"], (fx, fy)), snapped(e["to"], (tx, ty))
            a0, a1, b0, b1 = at(e["from"], (fx, fy)), at(e["to"], (tx, ty)), at(e["from"], sf), at(e["to"], st)
            if all(abs(b0[k] - b1[k]) < 0.5 for k in (0, 1) if abs(a0[k] - a1[k]) < 0.5):
                (fx, fy), (tx, ty) = sf, st
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
        box = shared(e["from"], e["to"])
        ox, oy = origin[box]
        if inner:
            geo += '<Array as="points">%s</Array>' % "".join(
                '<mxPoint x="%s" y="%s"/>' % (num(p[0] - ox), num(p[1] - oy)) for p in inner)
        cells.append(cell(e.get("id") or "e%d" % i, value, "flow",
                          {"ubl-guard": g and g.get("id")},
                          'style="%s" edge="1" parent="%s" source="%s" target="%s"'
                          % (style(**kv), esc(box), esc(e["from"]), esc(e["to"])), geo + "</mxGeometry>"))

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
        if ident in joined:
            continue
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
        box = shared((src or dst)[0]) if (src or dst) else "1"
        free_edge(cells, ident, "off-page-flow", pts, base, props, value, src, dst, box, origin[box])
        if value:
            # the label's place: as for a guard, a fraction along the flow and an offset
            c = cells[-1]
            cells[-1] = c.replace('<mxGeometry relative="1" as="geometry">',
                                  '<mxGeometry x="%s" relative="1" as="geometry"><mxPoint x="%s" y="%s" as="offset"/>'
                                  % (num(2 * t - 1), num(tb["x"] - q[0]), num(tb["cy"] - q[1])), 1)
    for i, m in enumerate(spec.get("crossMarks", [])):
        # a short stroke across a flow (BusinessCard's "//"): a line that
        # belongs to the flow, as a label does - a child of the flow, placed a
        # fraction along it, so it goes where the flow goes
        mid = ((m["x1"] + m["x2"]) / 2, (m["y1"] + m["y2"]) / 2)
        near = min(((math.dist(mid, along(p, mid)[1]), k) for k, p in edge_pts.items()), default=None)
        if near and near[0] <= 40:
            k = near[1]
            t, q = along(edge_pts[k], mid)
            ln = math.dist((m["x1"], m["y1"]), (m["x2"], m["y2"]))
            ang = math.degrees(math.atan2(m["y2"] - m["y1"], m["x2"] - m["x1"]))
            cells.append(cell(m.get("id") or "mark%d" % i, "", "mark", {},
                              'style="%s" vertex="1" connectable="0" parent="%s"'
                              % (style(shape="line", html=1, rotation=num(ang), strokeColor="#000000",
                                       strokeWidth=float(m.get("weight") or S["divider"]), resizable=0), esc(k)),
                              '<mxGeometry x="%s" y="0" width="%s" height="10" relative="1" as="geometry">'
                              '<mxPoint x="%s" y="%s" as="offset"/></mxGeometry>'
                              % (num(2 * t - 1), num(ln), num(mid[0] - q[0] - ln / 2), num(mid[1] - q[1] - 5))))
            continue
        # otherwise a short stroke across a partition rule: a plain line, both ends free
        free_edge(cells, m.get("id") or "mark%d" % i, "mark", [(m["x1"], m["y1"]), (m["x2"], m["y2"])],
                  dict(edgeStyle="none", rounded=0, html=1, endArrow="none", strokeColor="#000000",
                       strokeWidth=float(m.get("weight") or S["divider"])))

    for c in spec.get("captions", []):
        # a guard the reading took for a title, labelling no flow: a free text
        if c.get("role") == "phase-title" or c["id"] in used or c["id"] in taken:
            continue
        g, tb = guard_text[c["id"]]
        box = dict(x=tb["x"] - (c.get("textWidth") or 40) / 2 - 4, y=tb["cy"] - tb["size"],
                   w=(c.get("textWidth") or 40) + 8, h=2 * tb["size"])
        p, x, y = in_lane(box["x"], box["y"], box["w"], box["h"])
        vertex(c["id"], html_lines(tb["lines"]),
               style(text="", html=1, whiteSpace="nowrap", fontFamily=fam, fontSize=float(tb["size"]),
                     align="center", verticalAlign="middle", **placed_label(box, tb)).replace("text=;", "text;"),
               x, y, box["w"], box["h"], kind=c.get("role", "text"), **p)
    for g in spec.get("guards", []):
        if g.get("onFlow") or g["id"] in used or g["id"] in taken:
            continue
        # a text that labels no flow - a decision's question, a remark - is a
        # free text cell
        tb = text_block(g, F["guard"])
        p, x, y = in_lane(g["x"], g["y"], g["w"], g["h"])
        vertex(g.get("id"), html_lines(tb["lines"]),
               style(text="", html=1, fontFamily=fam, fontSize=float(tb["size"]), align=tb["align"],
                     verticalAlign="middle", **placed_label(g, tb)).replace("text=;", "text;"),
               x, y, g["w"], g["h"], kind=g.get("role", "text"), **p)

    # A margin round the drawing. draw.io grows an edge's bounds by its
    # arrowhead's size on every side, so a flow that runs off the page with a
    # head on it (the CPFR figures) reached past the page, and draw.io opened
    # the figure among a ring of extra pages. The page is one arrowhead wider
    # on each side and the drawing moved in by as much; the frame records the
    # offset (ubl-offset), and a reader of the file takes it off again.
    M = math.ceil(end_size + 2 * S["edge"]) + 2
    body = ET.fromstring('<root><mxCell id="0"/><mxCell id="1" parent="0"/>%s</root>' % "".join(cells))
    straighten(body)
    for c in body.iter("mxCell"):
        geo = c.find("mxGeometry")
        if geo is None:
            continue
        if c.get("vertex") == "1" and c.get("parent") == "1":
            geo.set("x", num(float(geo.get("x", 0)) + M))
            geo.set("y", num(float(geo.get("y", 0)) + M))
        if c.get("edge") == "1" and c.get("parent") == "1":
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
