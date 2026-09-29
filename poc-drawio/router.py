#!/usr/bin/env python3
"""Route flows across and down, around the boxes: an orthogonal router.

The approach of libavoid (Wybrow, Marriott and Stuckey, the router behind
Inkscape's and Dunnart's connectors), in a small form:

1. The routing grid: lines a margin away from every box's sides, plus the
   middle of every gap between boxes (so a route runs down the middle of a
   channel, not along a box), plus the lines of the contact points. A route
   may only use grid points outside every box.
2. Contact points: any side of the source and of the target, at its middle,
   at its thirds, or level with the other box, so a flow can be straight.
   A diamond, a disc or a bar is met at the middle of a side (a diamond's
   corners). A route leaves and meets a box square to its side.
3. The search: the cheapest route through the grid, where a route costs its
   length, plus a charge for every bend, for every crossing of a flow already
   routed or drawn, for every stretch run along another flow, and for a
   contact point another flow already uses. So it prefers short routes with
   few bends that keep clear of other flows.
4. One flow at a time, shortest first, each seeing those before it.
5. A guard of a re-routed flow is put beside the start of its route, where
   it is clear of boxes, flows and other words.

Used by house_style.py (--route): the flows that run at an angle are routed
anew; flows already straight across or down, or already bent, stay.
"""
import heapq, math, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import build_diagram as bd          # noqa: E402

DIRS = {"r": (1, 0), "l": (-1, 0), "d": (0, 1), "u": (0, -1)}
OUT = {"l": "l", "r": "r", "t": "u", "b": "d"}     # the way out of a side
INTO = {"l": "r", "r": "l", "t": "d", "b": "u"}    # the way into a side


class Router:
    def __init__(self, spec, em=12.0):
        self.s, self.em = spec, em
        self.margin = 0.75 * em
        self.bend = 3.0 * em          # a bend costs as much as this much length
        self.cross = 2.0 * em         # crossing another flow
        self.along = 8.0              # per px run along another flow (within 3 px)
        self.near = 1.5               # per px run close beside another flow
        self.gap = 1.0 * em           # ... closer than this
        self.merge = 2.0 * em         # a contact point shared by two flows into the same box
        self.clash = 1000.0 * em      # a contact point shared by a flow in and a flow out
        self.byid = {n["id"]: n for n in spec["nodes"]}
        self.segs = []                # segments already drawn: (a, b, edge id)
        self.used = []                # contact points already used: (point, node, "in" or "out")
        sp = dict(spec, byid=self.byid)
        for e in spec["edges"]:
            if not e.get("reroute"):
                pts = bd.polyline(sp, e)
                self.segs += [(a, b, e.get("id")) for a, b in zip(pts, pts[1:])]
                self.used += [(pts[0], e["from"], "out"), (pts[-1], e["to"], "in")]
        for o in spec.get("openEnds", []):
            pts = [tuple(p) for p in o["points"]]
            self.segs += [(a, b, o.get("id")) for a, b in zip(pts, pts[1:])]

    # -- obstacles and grid ----------------------------------------------------

    def obstacles(self, skip):
        m = self.margin
        out = []
        for n in self.s["nodes"]:
            if n["id"] in skip:
                continue
            out.append((n["x"] - m, n["y"] - m, n["x"] + n["w"] + m, n["y"] + n["h"] + m))
        for g in self.s.get("guards", []):
            if g.get("onFlow") in skip or not g.get("labelLines"):
                continue
            ll = g["labelLines"]
            out.append((min(l["cx"] - l["w"] / 2 for l in ll) - 2, min(l["cy"] for l in ll) - 0.6 * self.em,
                        max(l["cx"] + l["w"] / 2 for l in ll) + 2, max(l["cy"] for l in ll) + 0.6 * self.em))
        for t in self.s["lanes"]:
            if t.get("title"):
                out.append((t["cx"] - t["textWidth"] / 2 - 2, t["cy"] - 0.7 * self.em,
                            t["cx"] + t["textWidth"] / 2 + 2, t["cy"] + 0.7 * self.em))
        return out

    @staticmethod
    def inside(p, obs):
        return any(o[0] < p[0] < o[2] and o[1] < p[1] < o[3] for o in obs)

    @staticmethod
    def blocked(a, b, obs):
        """does the axis-aligned segment a-b pass through an obstacle's inside"""
        if a[1] == b[1]:
            y, x0, x1 = a[1], min(a[0], b[0]), max(a[0], b[0])
            return any(o[1] < y < o[3] and x0 < o[2] and o[0] < x1 for o in obs)
        x, y0, y1 = a[0], min(a[1], b[1]), max(a[1], b[1])
        return any(o[0] < x < o[2] and y0 < o[3] and o[1] < y1 for o in obs)

    def grid(self, obs, extra_x, extra_y):
        fb = self.s.get("frameBox") or [0, 0, self.s["canvas"]["w"], self.s["canvas"]["h"]]
        xs = {fb[0] + self.margin, fb[2] - self.margin} | set(extra_x)
        ys = {fb[1] + self.margin, fb[3] - self.margin} | set(extra_y)
        for o in obs:
            xs |= {o[0], o[2]}
            ys |= {o[1], o[3]}
        for c in (xs, ys):                         # the middle of every gap
            v = sorted(c)
            c |= {(a + b) / 2 for a, b in zip(v, v[1:]) if b - a > 2 * self.margin}
        lo_x, hi_x = fb[0] + 1, fb[2] - 1
        lo_y, hi_y = fb[1] + 1, fb[3] - 1
        # rounded, and each line once: two values that round alike would put
        # the same line in twice, and a step to "the next line" go nowhere
        xs = sorted({round(x, 1) for x in xs if lo_x <= x <= hi_x})
        ys = sorted({round(y, 1) for y in ys if lo_y <= y <= hi_y})
        return xs, ys

    # -- contact points --------------------------------------------------------

    def ports(self, n, other):
        """(side, point, preference cost) where a route may meet box n"""
        x0, y0, x1, y1 = n["x"], n["y"], n["x"] + n["w"], n["y"] + n["h"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        ox, oy = other["x"] + other["w"] / 2, other["y"] + other["h"] / 2
        out = [("l", (x0, cy), 0), ("r", (x1, cy), 0), ("t", (cx, y0), 0), ("b", (cx, y1), 0)]
        if n["kind"] in ("action", "object", "note") or n["kind"] == "fork":
            for f in (1 / 3, 2 / 3):
                out += [("l", (x0, y0 + f * (y1 - y0)), 0.5 * self.em), ("r", (x1, y0 + f * (y1 - y0)), 0.5 * self.em),
                        ("t", (x0 + f * (x1 - x0), y0), 0.5 * self.em), ("b", (x0 + f * (x1 - x0), y1), 0.5 * self.em)]
            # level with the other box: a straight route
            if y0 + 4 < oy < y1 - 4:
                out += [("l", (x0, oy), 0), ("r", (x1, oy), 0)]
            if x0 + 4 < ox < x1 - 4:
                out += [("t", (ox, y0), 0), ("b", (ox, y1), 0)]
        if n["kind"] == "fork":                    # a bar is met on its long sides only
            long_h = n["w"] >= n["h"]
            out = [p for p in out if (p[0] in "tb") == long_h]
        return out

    def port_cost(self, p, node, role):
        """sharing a contact point: two flows into the same box may merge there
        (as UML draws a merge), and two flows out of it may split there, at a
        small cost; a flow in and a flow out never share one"""
        c = 0
        for q, n, r in self.used:
            if n == node and math.dist(p, q) < 0.5 * self.em:
                c += self.merge if r == role else self.clash
        return c

    # -- the search ------------------------------------------------------------

    def seg_cost(self, a, b, eid):
        """what running from a to b costs beyond its length: crossings, and
        running along or close beside other flows"""
        c = 0.0
        horiz = a[1] == b[1]
        for p, q, other in self.segs:
            if other == eid:
                continue
            ph = abs(p[1] - q[1]) < 0.5
            pv = abs(p[0] - q[0]) < 0.5
            if horiz and pv:
                x, y0, y1 = p[0], min(p[1], q[1]), max(p[1], q[1])
                if min(a[0], b[0]) < x < max(a[0], b[0]) and y0 < a[1] < y1:
                    c += self.cross
            elif not horiz and ph:
                y, x0, x1 = p[1], min(p[0], q[0]), max(p[0], q[0])
                if min(a[1], b[1]) < y < max(a[1], b[1]) and x0 < a[0] < x1:
                    c += self.cross
            elif horiz and ph:
                d = abs(a[1] - p[1])
                ov = min(max(a[0], b[0]), max(p[0], q[0])) - max(min(a[0], b[0]), min(p[0], q[0]))
                if ov > 0 and d < self.gap:
                    c += ov * (self.along if d < 3 else self.near)
            elif not horiz and pv:
                d = abs(a[0] - p[0])
                ov = min(max(a[1], b[1]), max(p[1], q[1])) - max(min(a[1], b[1]), min(p[1], q[1]))
                if ov > 0 and d < self.gap:
                    c += ov * (self.along if d < 3 else self.near)
            elif not ph and not pv:               # a flow at an angle: count a crossing
                if bd._cross(a, b, p, q):
                    c += self.cross
        return c

    def route(self, e):
        A, B = self.byid[e["from"]], self.byid[e["to"]]
        obs = self.obstacles({A["id"], B["id"], e.get("id")})
        # the ends' own boxes are obstacles too, but a route may leave and
        # enter them through its contact points
        m = self.margin
        own = [(n["x"], n["y"], n["x"] + n["w"], n["y"] + n["h"]) for n in (A, B)]
        starts, ends = self.ports(A, B), self.ports(B, A)
        stub = lambda side, p: (p[0] + DIRS[OUT[side]][0] * m, p[1] + DIRS[OUT[side]][1] * m)   # noqa: E731
        xs, ys = self.grid(obs + [(o[0] - m, o[1] - m, o[2] + m, o[3] + m) for o in own],
                           [p[1][0] for p in starts + ends] + [stub(*p[:2])[0] for p in starts + ends],
                           [p[1][1] for p in starts + ends] + [stub(*p[:2])[1] for p in starts + ends])
        allobs = obs + own
        xi = {x: i for i, x in enumerate(xs)}
        yi = {y: i for i, y in enumerate(ys)}
        goal = {}
        for side, p, pc in ends:
            q = stub(side, p)
            q = (round(q[0], 1), round(q[1], 1))
            if q in goal and goal[q][2] <= pc:
                continue
            goal[q] = (side, p, pc + self.port_cost(p, B["id"], "in"))
        # Dijkstra over (point, heading)
        pq, best = [], {}
        for side, p, pc in starts:
            q = stub(side, p)
            q = (round(q[0], 1), round(q[1], 1))
            if self.inside(q, obs) or q[0] not in xi or q[1] not in yi:
                continue
            c = pc + self.port_cost(p, A["id"], "out") + m + self.seg_cost(p, q, e.get("id"))
            heapq.heappush(pq, (c, q, OUT[side], (p, q)))
        tx, ty = B["x"] + B["w"] / 2, B["y"] + B["h"] / 2
        while pq:
            c, q, h, path = heapq.heappop(pq)
            if h == "done":                         # a finished route, its end's cost counted
                return list(path), None, path[0], c
            if best.get((q, h), 1e18) <= c:
                continue
            best[(q, h)] = c
            if q in goal and h == INTO[goal[q][0]]:
                side, p, pc = goal[q]
                heapq.heappush(pq, (c + pc + m, q, "done", tuple(path) + (p,)))
                continue
            if q in goal:
                side, p, pc = goal[q]
                # turn at the stub into the side
                nh = INTO[side]
                cc = c + (self.bend if nh != h else 0)
                heapq.heappush(pq, (cc, q, nh, path))
            i, j = xi[q[0]], yi[q[1]]
            for nh, (dx, dy) in DIRS.items():
                if (dx, dy) == (-DIRS[h][0], -DIRS[h][1]):
                    continue                        # no turning back
                ni, nj = i + dx, j + dy
                if not (0 <= ni < len(xs) and 0 <= nj < len(ys)):
                    continue
                r = (xs[ni], ys[nj])
                if self.inside(r, allobs) or self.blocked(q, r, allobs):
                    continue
                cc = c + math.dist(q, r) + (self.bend if nh != h else 0) + self.seg_cost(q, r, e.get("id"))
                if best.get((r, nh), 1e18) <= cc:
                    continue
                np_ = path + (r,) if nh != h else path[:-1] + (r,)
                heapq.heappush(pq, (cc, r, nh, np_))
        return None

    def run(self, edges):
        sp = dict(self.s, byid=self.byid)
        edges = sorted(edges, key=lambda e: math.dist(*[(n["x"] + n["w"] / 2, n["y"] + n["h"] / 2)
                                                           for n in (self.byid[e["from"]], self.byid[e["to"]])]))
        done = []
        for e in edges:
            r = self.route(e)
            if r is None:
                continue
            pts, _, _, _ = r
            pts = simplify(pts)
            A, B = self.byid[e["from"]], self.byid[e["to"]]
            e["exitXY"] = [(pts[0][0] - A["x"]) / A["w"], (pts[0][1] - A["y"]) / A["h"]]
            e["entryXY"] = [(pts[-1][0] - B["x"]) / B["w"], (pts[-1][1] - B["y"]) / B["h"]]
            e["points"] = [list(p) for p in pts[1:-1]]
            e["straight"] = len(pts) == 2
            e.pop("reroute", None)
            self.segs += [(a, b, e.get("id")) for a, b in zip(pts, pts[1:])]
            self.used += [(pts[0], e["from"], "out"), (pts[-1], e["to"], "in")]
            done.append(e)
        # rip up and re-route: each flow again, with all the others in place
        for _ in range(2):
            for e in done:
                pts = [tuple(p) for p in bd.polyline(dict(self.s, byid=self.byid), e)]
                self.segs = [t for t in self.segs if t[2] != e.get("id")]
                self.used = [u for u in self.used if not (math.dist(u[0], pts[0]) < 0.5 and u[1] == e["from"])
                             and not (math.dist(u[0], pts[-1]) < 0.5 and u[1] == e["to"])]
                r = self.route(e)
                new = simplify(r[0]) if r else pts
                A, B = self.byid[e["from"]], self.byid[e["to"]]
                e["exitXY"] = [(new[0][0] - A["x"]) / A["w"], (new[0][1] - A["y"]) / A["h"]]
                e["entryXY"] = [(new[-1][0] - B["x"]) / B["w"], (new[-1][1] - B["y"]) / B["h"]]
                e["points"] = [list(p) for p in new[1:-1]]
                e["straight"] = len(new) == 2
                self.segs += [(a, b, e.get("id")) for a, b in zip(new, new[1:])]
                self.used += [(new[0], e["from"], "out"), (new[-1], e["to"], "in")]
        return done


def simplify(pts):
    """drop points that lie on the straight line between their neighbours"""
    out = [tuple(pts[0])]
    for p, q in zip(pts[1:], pts[2:]):
        a = out[-1]
        if (abs(a[0] - p[0]) < 0.5 and abs(p[0] - q[0]) < 0.5) or (abs(a[1] - p[1]) < 0.5 and abs(p[1] - q[1]) < 0.5):
            continue
        out.append(tuple(p))
    out.append(tuple(pts[-1]))
    return out


def _clear_test(s, g, em=12.0):
    """a test: is a box for g's words inside the frame and clear of boxes,
    flows, lane titles and other words"""
    sp = dict(s, byid={n["id"]: n for n in s["nodes"]})
    boxes = [(n["x"], n["y"], n["x"] + n["w"], n["y"] + n["h"]) for n in s["nodes"]]
    for o in s.get("guards", []):
        if o is not g and o.get("labelLines"):
            L = o["labelLines"]
            boxes.append((min(l["cx"] - l["w"] / 2 for l in L), min(l["cy"] for l in L) - 0.6 * em,
                          max(l["cx"] + l["w"] / 2 for l in L), max(l["cy"] for l in L) + 0.6 * em))
    segs = []
    for f in s["edges"]:
        q = bd.polyline(sp, f)
        segs += list(zip(q, q[1:]))
    pad = 0.3 * em

    def free(bx):
        if any(bx[0] < b[2] + pad and b[0] < bx[2] + pad and bx[1] < b[3] + pad and b[1] < bx[3] + pad for b in boxes):
            return False
        return all(bd._seg_box_dist(a, b, bx) > 1 for a, b in segs)
    fb = s.get("frameBox") or [0, 0, s["canvas"]["w"], s["canvas"]["h"]]
    for t in s["lanes"]:
        if t.get("title"):
            boxes.append((t["cx"] - t["textWidth"] / 2, t["cy"] - 0.7 * em, t["cx"] + t["textWidth"] / 2, t["cy"] + 0.7 * em))

    def fits(bx):
        return fb[0] + pad <= bx[0] and bx[2] <= fb[2] - pad and fb[1] + pad <= bx[1] and bx[3] <= fb[3] - pad \
            and free(bx)
    return fits


def place_question(s, g, em=12.0):
    """a decision's question (words on no flow) that a route or box now runs
    through: put at the first clear place round its diamond - above left,
    above right, below left, below right, then beside the side corners"""
    n = next((m for m in s["nodes"] if m["id"] == g.get("near")), None)
    ll = g.get("labelLines") or []
    if n is None or not ll:
        return False
    w = max(l["w"] for l in ll)
    h = len(ll) * 1.2 * em
    fits = _clear_test(s, g, em)
    pad = 0.3 * em
    cx, cy = n["x"] + n["w"] / 2, n["y"] + n["h"] / 2
    x0, x1, y0, y1 = n["x"], n["x"] + n["w"], n["y"], n["y"] + n["h"]
    spots = [(cx - pad - w, y0 - h + n["h"] / 4), (cx + pad, y0 - h + n["h"] / 4),
             (cx - pad - w, y1 - n["h"] / 4), (cx + pad, y1 - n["h"] / 4),
             (x0 - pad - w, cy - h - pad), (x1 + pad, cy - h - pad),
             (x0 - pad - w, cy + pad), (x1 + pad, cy + pad)]
    for px, py in spots:
        bx = (px, py, px + w, py + h)
        if fits(bx):
            for i, l in enumerate(ll):
                l["cx"] = bx[0] + l["w"] / 2
                l["cy"] = bx[1] + (i + 0.5) * 1.2 * em
            g["x"], g["y"], g["w"], g["h"] = bx[0], bx[1], w, h
            return True
    return False


def place_guard(s, g, e, em=12.0):
    """a re-routed flow's guard beside the start of its new route: the first
    free place along its first stretch, on either side, clear of boxes, flows
    and other words"""
    sp = dict(s, byid={n["id"]: n for n in s["nodes"]})
    pts = bd.polyline(sp, e)
    ll = g.get("labelLines") or []
    if not ll:
        return
    w = max(l["w"] for l in ll)
    h = len(ll) * 1.2 * em
    fits = _clear_test(s, g, em)
    pad = 0.3 * em
    for a, b in zip(pts, pts[1:]):                 # the first stretch first
        L = math.dist(a, b)
        if L < 1:
            continue
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        for t in [0.6 * em + k * 0.5 * em for k in range(max(1, int((L - 0.6 * em) / (0.5 * em))))]:
            px, py = a[0] + ux * t, a[1] + uy * t
            for sgn in (1, -1):
                if abs(ux) > abs(uy):          # a level stretch: the words above or below it
                    x0 = px if ux > 0 else px - w
                    bx = (x0, py - pad - h, x0 + w, py - pad) if sgn > 0 else (x0, py + pad, x0 + w, py + pad + h)
                else:                          # an upright stretch: the words beside it
                    y0 = py if uy > 0 else py - h
                    bx = (px + pad, y0, px + pad + w, y0 + h) if sgn > 0 else (px - pad - w, y0, px - pad, y0 + h)
                if fits(bx):
                    for i, l in enumerate(ll):
                        l["cx"] = bx[0] + l["w"] / 2
                        l["cy"] = bx[1] + (i + 0.5) * 1.2 * em
                    g["x"], g["y"], g["w"], g["h"] = bx[0], bx[1], w, h
                    return True
    return False


def guard_blocked(s, g, em=12.0):
    """does a line or a box now run through a guard's words"""
    ll = g.get("labelLines") or []
    if not ll:
        return False
    bx = (min(l["cx"] - l["w"] / 2 for l in ll), min(l["cy"] for l in ll) - 0.5 * em,
          max(l["cx"] + l["w"] / 2 for l in ll), max(l["cy"] for l in ll) + 0.5 * em)
    sp = dict(s, byid={n["id"]: n for n in s["nodes"]})
    for f in s["edges"]:
        q = bd.polyline(sp, f)
        if any(bd._seg_box_dist(a, b, bx) == 0 for a, b in zip(q, q[1:])):
            return True
    return any(bx[0] < n["x"] + n["w"] and n["x"] < bx[2] and bx[1] < n["y"] + n["h"] and n["y"] < bx[3]
               for n in s["nodes"])


def route_figure(s, em=12.0, which="angled"):
    """Route the flows of a house spec anew: 'angled' - the ones that run at
    an angle; 'all' - also the ones already bent. Returns (routed, guards
    placed)."""
    sp = dict(s, byid={n["id"]: n for n in s["nodes"]})
    pick = []
    for e in s["edges"]:
        pts = bd.polyline(sp, e)
        axis = all(abs(a[0] - b[0]) < 1 or abs(a[1] - b[1]) < 1 for a, b in zip(pts, pts[1:]))
        if (not axis) or (which == "all" and len(pts) > 2):
            e["reroute"] = True
            pick.append(e)
    r = Router(s, em)
    done = r.run(pick)
    for e in pick:
        e.pop("reroute", None)
    placed = 0
    guards = {g.get("onFlow"): g for g in s.get("guards", [])}
    for e in done:
        g = guards.get(e.get("id"))
        if g is not None and place_guard(s, g, e, em):
            placed += 1
    return len(done), len(pick), placed


# ---- libavoid ---------------------------------------------------------------

UP, DOWN, LEFT, RIGHT = 1, 2, 4, 8


def _side(f):
    """which side of a box a contact point (as fractions) lies on"""
    return min((f[0], "l"), (1 - f[0], "r"), (f[1], "t"), (1 - f[1], "b"))[1]


SIDE_DIR = {"t": UP, "b": DOWN, "l": LEFT, "r": RIGHT}


def free_pins(n):
    """where a flow routed anew may meet a node: libavoid chooses among these"""
    k = n["kind"]
    mids = [(0.5, 0, UP, False), (0.5, 1, DOWN, False), (0, 0.5, LEFT, False), (1, 0.5, RIGHT, False)]
    if k in ("decision", "initial", "final"):
        return mids                                    # the corners of a diamond; shared
    if k == "fork":
        long_h = n["w"] >= n["h"]
        fs = [i / 6 for i in range(1, 6)]
        return [(f, 0, UP, True) for f in fs] + [(f, 1, DOWN, True) for f in fs] if long_h else \
            [(0, f, LEFT, True) for f in fs] + [(1, f, RIGHT, True) for f in fs]
    fs = [0.5, 1 / 3, 2 / 3, 0.25, 0.75]
    return [(f, 0, UP, True) for f in fs] + [(f, 1, DOWN, True) for f in fs] + \
        [(0, f, LEFT, True) for f in fs] + [(1, f, RIGHT, True) for f in fs]


CORNERS = {"t": (0.5, 0.0), "b": (0.5, 1.0), "l": (0.0, 0.5), "r": (1.0, 0.5)}
CORNER_OUT = {"t": (0, -1), "b": (0, 1), "l": (-1, 0), "r": (1, 0)}
# the middles of a diamond's four slanted sides, and the way out of each at 45 degrees
FACETS = {"tl": (0.25, 0.25), "tr": (0.75, 0.25), "bl": (0.25, 0.75), "br": (0.75, 0.75)}
FACET_OUT = {"tl": (-1, -1), "tr": (1, -1), "bl": (-1, 1), "br": (1, 1)}


def assign_corners(s):
    """Where each flow meets a diamond, a disc or a fork bar: chosen here,
    since libavoid cannot tell a flow in from a flow out.

    A diamond (a decision or merge) offers its four corners, where a flow
    leaves or arrives square; only a diamond with more flows than corners
    also offers the middles of its four slanted sides, where a flow leaves
    or arrives at 45 degrees and turns square a little way out - so such a
    decision need not crowd its flows into its corners. Every assignment of the node's flows to these eight places is
    tried, and the cheapest kept: a flow should leave towards the box at its
    other end; a corner costs less than a slanted side; a flow in and a flow
    out never share a place; flows in may share one (they merge) at a small
    cost, flows out (a split) only at a larger one, since the branches of a
    decision read best each from its own place. A disc offers its four corners
    only. A fork or join bar takes its flows in on one long side and its
    flows out on the other - the side facing most of where the flows in come
    from - spread along it in the order of where they go.

    Returns {(edge id, "exit"|"entry"): (fx, fy, (dx, dy) or None)}: the place
    as fractions of the node's box, and for a slanted side the 45-degree way
    out."""
    import itertools
    byid = {n["id"]: n for n in s["nodes"]}
    out = {}
    centre = lambda n: (n["x"] + n["w"] / 2, n["y"] + n["h"] / 2)   # noqa: E731
    for n in s["nodes"]:
        ends = [(e, "exit", byid[e["to"]]) for e in s["edges"] if e["from"] == n["id"]] + \
               [(e, "entry", byid[e["from"]]) for e in s["edges"] if e["to"] == n["id"]]
        if not ends:
            continue
        c = centre(n)
        if n["kind"] == "fork":
            long_h = n["w"] >= n["h"]
            a, b = ("t", "b") if long_h else ("l", "r")
            k = 1 if long_h else 0
            ins = [centre(o)[k] for e, w, o in ends if w == "entry"]
            # flows in from another figure (leaving the page) count too
            for oe in s.get("openEnds", []):
                p0 = oe["points"][-1]
                if oe.get("arrow") and n["x"] - 4 <= p0[0] <= n["x"] + n["w"] + 4 and n["y"] - 20 <= p0[1] <= n["y"] + n["h"] + 20:
                    ins.append(oe["points"][0][k])
            if ins:
                side_in = a if sum(v - c[k] for v in ins) < 0 else b
                side_out = b if side_in == a else a
            else:                                    # no flow in: out on the side facing where they go
                side_out = a if sum(centre(o)[k] - c[k] for e, w, o in ends) < 0 else b
                side_in = b if side_out == a else a
            for side, group in ((side_in, [t for t in ends if t[1] == "entry"]),
                                (side_out, [t for t in ends if t[1] == "exit"])):
                group = sorted(group, key=lambda t: centre(t[2])[0 if long_h else 1])
                for i, (e, w, o) in enumerate(group):
                    f = (i + 1) / (len(group) + 1)
                    out[(e.get("id"), w)] = ((f, CORNERS[side][1]) if long_h else (CORNERS[side][0], f)) + (None,)
            continue
        if n["kind"] not in ("decision", "initial", "final"):
            continue
        places = dict((k, (v, CORNER_OUT[k], 0.0)) for k, v in CORNERS.items())
        # the slanted sides only when a diamond has more flows than corners
        if n["kind"] == "decision" and len(ends) > len(CORNERS):
            places.update((k, (v, FACET_OUT[k], 0.35)) for k, v in FACETS.items())
        names = list(places)
        # a way out that runs into another box before the one the flow goes
        # to is a detour; on a tie, the side of the lane with more room
        rules = sorted(d[0] if isinstance(d, list) else d for d in s.get("dividers", []))
        fb = s.get("frameBox") or [0, 0, s["canvas"]["w"], s["canvas"]["h"]]
        left = max([r for r in rules if r < c[0]] + [fb[0]])
        right = min([r for r in rules if r > c[0]] + [fb[2]])
        roomy = 1 if right - c[0] > c[0] - left else -1

        def blocked(p, o):
            f, v = places[p][0], places[p][1]
            vl = math.hypot(*v)
            x, y = n["x"] + n["w"] * f[0], n["y"] + n["h"] * f[1]
            far = math.hypot(centre(o)[0] - x, centre(o)[1] - y)
            for k in range(1, 60):
                d = far * k / 60
                px, py = x + v[0] / vl * d, y + v[1] / vl * d
                if o["x"] <= px <= o["x"] + o["w"] and o["y"] <= py <= o["y"] + o["h"]:
                    return False
                if any(m is not n and m is not o and m["x"] <= px <= m["x"] + m["w"] and m["y"] <= py <= m["y"] + m["h"]
                       for m in s["nodes"]):
                    return True
            return False
        blocked_ = {}
        best = None
        for combo in itertools.product(names, repeat=len(ends)):
            cost = 0.0
            for (e, w, o), p in zip(ends, combo):
                ox, oy = centre(o)
                d = math.hypot(ox - c[0], oy - c[1]) or 1
                vx, vy = places[p][1]
                vl = math.hypot(vx, vy)
                cost += 1 - (vx * (ox - c[0]) + vy * (oy - c[1])) / (d * vl) + places[p][2]
                if (p, o["id"]) not in blocked_:
                    blocked_[(p, o["id"])] = blocked(p, o)
                if blocked_[(p, o["id"])]:
                    cost += 0.8
                if vx and vx * roomy < 0:
                    cost += 0.01
            for i in range(len(ends)):
                for j in range(i + 1, len(ends)):
                    if combo[i] == combo[j]:
                        # flows in may merge at one place; the branches out of
                        # a decision each leave by their own, where there is one
                        cost += 100 if ends[i][1] != ends[j][1] else 0.3 if ends[i][1] == "entry" else 1.2
            if best is None or cost < best[0]:
                best = (cost, combo)
        for (e, w, o), p in zip(ends, best[1]):
            f, v, _ = places[p]
            # a diamond's flows run straight out of it for a stretch (see
            # route_libavoid); a disc's meet it at its corner
            out[(e.get("id"), w)] = (f[0], f[1], v if p in FACETS or n["kind"] == "decision" else None)
    return out


def room_for_head(s, pts, B, head):
    """A route whose last stretch into B is shorter than the arrowhead needs
    (the head pressed into the bend): the stretch before it, parallel to B's
    side, moved out from B by what is missing - where it then runs clear of
    every box. Returns the route."""
    if len(pts) < 3:
        return pts
    pts = [tuple(p) for p in pts]
    (x2, y2), (x1, y1), (x0, y0) = pts[-3], pts[-2], pts[-1]
    last = abs(x0 - x1) + abs(y0 - y1)
    if last >= head - 0.5:
        return pts
    if abs(y0 - y1) < 0.5 and abs(x2 - x1) < 0.5:          # into a left or right side, after a run up or down
        d = (head - last) * (1 if x1 > x0 else -1)
        new = [(x2 + d, y2), (x1 + d, y1)]
    elif abs(x0 - x1) < 0.5 and abs(y2 - y1) < 0.5:        # into a top or bottom, after a run across
        d = (head - last) * (1 if y1 > y0 else -1)
        new = [(x2, y2 + d), (x1, y1 + d)]
    else:
        return pts
    if len(pts) == 3:
        return pts                                        # the run starts at the other box: not moved
    seg = [pts[-4], new[0], new[1], (x0, y0)]
    for m in s["nodes"]:
        if m is B:
            continue
        # a box shrunk by a pixel: a route may start on the other box's side
        n = dict(x=m["x"] + 1, y=m["y"] + 1, w=m["w"] - 2, h=m["h"] - 2)
        for a, b in zip(seg, seg[1:]):
            if min(a[0], b[0]) < n["x"] + n["w"] and n["x"] < max(a[0], b[0]) and \
               min(a[1], b[1]) < n["y"] + n["h"] and n["y"] < max(a[1], b[1]):
                return pts
            if (abs(a[0] - b[0]) < 0.5 and n["x"] < a[0] < n["x"] + n["w"] and min(a[1], b[1]) < n["y"] + n["h"]
                    and n["y"] < max(a[1], b[1])) or (abs(a[1] - b[1]) < 0.5 and n["y"] < a[1] < n["y"] + n["h"]
                                                      and min(a[0], b[0]) < n["x"] + n["w"] and n["x"] < max(a[0], b[0])):
                return pts
    return pts[:-3] + new + [(x0, y0)]


def route_libavoid(s, em=12.0):
    """Route the flows of a house spec with libavoid (avoid_route.mjs): the
    flows that run at an angle anew, on pins libavoid chooses; the others on
    their own contact points, routed with them so that libavoid can nudge all
    of them apart. Diamonds, discs and bars are met where assign_corners
    says. Returns (routed anew, guards placed)."""
    import json, subprocess
    here = os.path.dirname(os.path.abspath(__file__))
    sp = dict(s, byid={n["id"]: n for n in s["nodes"]})
    anew = set()
    for e in s["edges"]:
        pts = bd.polyline(sp, e)
        if not all(abs(a[0] - b[0]) < 1 or abs(a[1] - b[1]) < 1 for a, b in zip(pts, pts[1:])):
            anew.add(e.get("id"))
        # a flow that bends on its way from (or to) a decision: its place on
        # the diamond is chosen anew (assign_corners), so its other end is too
        elif len(pts) > 2 and "decision" in (sp["byid"][e["from"]]["kind"], sp["byid"][e["to"]]["kind"]):
            anew.add(e.get("id"))
    # a document on a lane divider is not met at the middle of its top or
    # bottom: a flow leaving there would run down the divider itself
    rules = [d[0] if isinstance(d, list) else d for d in s.get("dividers", [])]
    on_rule = {n["id"] for n in s["nodes"] if n["kind"] == "object" and any(n["x"] < r < n["x"] + n["w"] for r in rules)}

    def off_rule(n, f):
        if n["id"] in on_rule and f[1] in (0, 1) and abs(f[0] - 0.5) < 0.1:
            return [0.3 if f[0] <= 0.5 else 0.7, f[1]]
        return list(f)
    shapes = {n["id"]: dict(id=n["id"], kind=n["kind"], x=n["x"], y=n["y"], w=n["w"], h=n["h"],
                            pins=[dict(cls=1, fx=f[0], fy=f[1], dir=f[2], exclusive=f[3]) for f in free_pins(n)
                                  if not (n["id"] in on_rule and f[1] in (0, 1) and abs(f[0] - 0.5) < 0.1)])
              for n in s["nodes"]}
    conns, cls = [], 100
    placed_at = assign_corners(s)
    slanted = {}                                   # (edge id, which): (point on the diamond, point out along the lead)
    # a flow leaves (or meets) a diamond straight for a stretch before it may
    # turn - at a corner square, at a slanted side at 45 degrees - long
    # enough for an arrowhead and a label size more: the head is never
    # pressed into the first bend
    stub = s.get("arrow", 1.35 * em) + em
    corner_pin = {}
    for e in s["edges"]:
        end = {}
        for which, node, key in (("src", e["from"], "exitXY"), ("dst", e["to"], "entryXY")):
            at = placed_at.get((e.get("id"), "exit" if which == "src" else "entry"))
            if at is not None:
                e[key] = [at[0], at[1]]
                if at[2] is not None:
                    # a diamond: the route starts (or ends) a lead's length
                    # out - from a slanted side along 45 degrees, from a
                    # corner square - and the lead is put back in afterwards
                    n = sp["byid"][node]
                    p = (n["x"] + n["w"] * at[0], n["y"] + n["h"] * at[1])
                    k = math.hypot(at[2][0], at[2][1])
                    # as long as there is room: the lead's end clear of every
                    # other box and the margin libavoid keeps round it
                    buf = 0.75 * em
                    def clear_at(q):
                        return not any(o["id"] != node and o["x"] - buf <= q[0] <= o["x"] + o["w"] + buf
                                       and o["y"] - buf <= q[1] <= o["y"] + o["h"] + buf for o in s["nodes"])
                    ln = stub
                    while ln > 0.9 * em and not clear_at((p[0] + at[2][0] * ln / k, p[1] + at[2][1] * ln / k)):
                        ln -= 2
                    q = (p[0] + at[2][0] * ln / k, p[1] + at[2][1] * ln / k)
                    other = sp["byid"][e["to"] if which == "src" else e["from"]]
                    straight_on = (at[2][0] == 0 and other["x"] < p[0] < other["x"] + other["w"]) or \
                                  (at[2][1] == 0 and other["y"] < p[1] < other["y"] + other["h"])
                    if not clear_at(q) or straight_on:
                        # no room for a lead, or none needed: the flow runs
                        # straight on to the box it joins - met at the corner
                        if at[2][0] and at[2][1]:
                            ln = 0.9 * em               # a slanted side: the short lead, as before
                            q = (p[0] + at[2][0] * ln / k, p[1] + at[2][1] * ln / k)
                        else:
                            ln = 0
                    if ln:
                        slanted[(e.get("id"), which)] = (p, q)
                    dirs = (UP if at[2][1] < 0 else 0) | (DOWN if at[2][1] > 0 else 0) | \
                           (LEFT if at[2][0] < 0 else 0) | (RIGHT if at[2][0] > 0 else 0)
                    if ln == 0:
                        f = [at[0], at[1]]
                        sh = shapes[node]
                        same = [pp for pp in sh["pins"] if pp["cls"] >= 100 and pp["fx"] == f[0] and pp["fy"] == f[1]
                                and not pp.get("offset")]
                        if same:
                            end[which] = dict(shape=node, cls=same[0]["cls"])
                        else:
                            sh["pins"].append(dict(cls=cls, fx=f[0], fy=f[1], dir=dirs, exclusive=False))
                            end[which] = dict(shape=node, cls=cls)
                            cls += 1
                    elif at[2][0] == 0 or at[2][1] == 0:
                        # at a corner: a pin moved out along the lead (libavoid
                        # starts there, square); flows merging at a corner
                        # share one pin, as two pins on one point find nothing
                        key_ = (node, at[0], at[1], round(ln))
                        if key_ not in corner_pin:
                            shapes[node]["pins"].append(dict(cls=cls, fx=at[0], fy=at[1], dir=dirs, exclusive=False,
                                                             offset=-ln))
                            corner_pin[key_] = cls
                            cls += 1
                        end[which] = dict(shape=node, cls=corner_pin[key_])
                    else:
                        # at a slanted side: the route starts at the lead's end
                        end[which] = dict(point=list(q))
                    continue
            if at is None and e.get("id") in anew:
                end[which] = dict(shape=node, cls=1)
            else:
                f = off_rule(sp["byid"][node], e.get(key) or bd.SIDE[e["exit" if which == "src" else "entry"]])
                sh = shapes[node]
                # two flows meeting a box at one point share one pin: two pins
                # on one point, and libavoid finds neither
                same = [p for p in sh["pins"] if p["cls"] >= 100 and abs(p["fx"] - f[0]) * sh["w"] <= 2
                        and abs(p["fy"] - f[1]) * sh["h"] <= 2]
                if same:
                    end[which] = dict(shape=node, cls=same[0]["cls"])
                    continue
                sh["pins"].append(dict(cls=cls, fx=f[0], fy=f[1], dir=SIDE_DIR[_side(f)], exclusive=False))
                end[which] = dict(shape=node, cls=cls)
                cls += 1
        conns.append(dict(id=e.get("id"), **end))
    # a free pin where a fixed pin already sits is left out: two pins on one
    # point and libavoid found neither, and ran the route to the box's centre
    for sh in shapes.values():
        fixed = [(p["fx"], p["fy"]) for p in sh["pins"] if p["cls"] >= 100]
        sh["pins"] = [p for p in sh["pins"] if p["cls"] >= 100 or
                      all(abs(p["fx"] - f[0]) * sh["w"] > 2 or abs(p["fy"] - f[1]) * sh["h"] > 2 for f in fixed)]
    # Guards are not obstacles: the routes take the best way, and a guard a
    # route then runs through is put somewhere clear afterwards (it moves more
    # easily than a flow). As obstacles, two guards beside a fork blocked the
    # natural way up and sent a flow round, across another.
    obst = []
    for t in s["lanes"]:
        if t.get("title"):
            obst.append(dict(id="title-" + str(t.get("id")), x=t["cx"] - t["textWidth"] / 2, y=t["cy"] - 0.7 * em,
                             w=t["textWidth"], h=1.4 * em, pins=[]))
    job = dict(params=dict(
        parameters=dict(shapeBufferDistance=0.75 * em, idealNudgingDistance=1.0 * em, segmentPenalty=4 * em,
                        crossingPenalty=8 * em, portDirectionPenalty=10 * em),
        # flows merging at one point (or splitting from one) share their last
        # stretch, as a UML merge is drawn, instead of being nudged apart
        options=dict(nudgeOrthogonalSegmentsConnectedToShapes=True, nudgeSharedPathsWithCommonEndPoint=False,
                     penaliseOrthogonalSharedPathsAtConnEnds=True, performUnifyingNudgingPreprocessingStep=True)),
        shapes=list(shapes.values()) + obst, conns=conns)
    env = dict(os.environ, NODE_PATH=os.path.join(here, "node_modules"))
    out = subprocess.run(["node", os.path.join(here, "avoid_route.mjs")], input=json.dumps(job),
                         capture_output=True, text=True, env=env, cwd=here, check=True).stdout
    routes = json.loads(out)
    # a flow libavoid found no route for (it runs a line from centre to
    # centre): tried again on its own, free to meet both boxes anywhere
    lost = [c for c in conns if c["id"] in routes and len(routes[c["id"]]) >= 2 and c["src"].get("shape") in sp["byid"]
            and c["dst"].get("shape") in sp["byid"] and (lambda n, p: n["x"] + 2 < p[0] < n["x"] + n["w"] - 2 and n["y"] + 2 < p[1]
                                         < n["y"] + n["h"] - 2)(sp["byid"][c["src"]["shape"]], routes[c["id"]][0])]
    if lost:
        again = dict(job, conns=[dict(c, src=dict(shape=c["src"]["shape"], cls=1), dst=dict(shape=c["dst"]["shape"], cls=1))
                                 for c in lost])
        for sh in again["shapes"]:
            for p in sh["pins"]:
                p["exclusive"] = False
        retry = json.loads(subprocess.run(["node", os.path.join(here, "avoid_route.mjs")], input=json.dumps(again),
                                          capture_output=True, text=True, env=env, cwd=here, check=True).stdout)
        routes.update(retry)
    byid = sp["byid"]
    failed = []
    for e in s["edges"]:
        pts = [tuple(p) for p in routes.get(e.get("id")) or []]
        if len(pts) < 2:
            continue
        A, B = byid[e["from"]], byid[e["to"]]
        pts = simplify(pts)
        # no route found: libavoid runs a line from centre to centre. The
        # flow then stays as it was drawn.
        inner = lambda n, p: n["x"] + 2 < p[0] < n["x"] + n["w"] - 2 and n["y"] + 2 < p[1] < n["y"] + n["h"] - 2  # noqa: E731
        sa, sb = slanted.get((e.get("id"), "src")), slanted.get((e.get("id"), "dst"))
        if (not sa and inner(A, pts[0])) or (not sb and inner(B, pts[-1])):
            failed.append(e.get("id"))
            continue
        # the 45-degree stretch from (or to) a diamond's slanted side
        if sa:
            pts = [sa[0]] + pts
        if sb:
            pts = pts + [sb[0]]
        pts = simplify(pts)
        pts = room_for_head(s, pts, B, s.get("arrow", 1.35 * em) + 0.5 * em)
        e["exitXY"] = [min(1, max(0, (pts[0][0] - A["x"]) / A["w"])), min(1, max(0, (pts[0][1] - A["y"]) / A["h"]))]
        e["entryXY"] = [min(1, max(0, (pts[-1][0] - B["x"]) / B["w"])), min(1, max(0, (pts[-1][1] - B["y"]) / B["h"]))]
        e["points"] = [list(p) for p in pts[1:-1]]
        # a route with a slanted stretch is drawn point for point as routed;
        # one across and down stays an orthogonal flow in draw.io
        slant = any(abs(a[0] - b[0]) > 0.5 and abs(a[1] - b[1]) > 0.5 for a, b in zip(pts, pts[1:]))
        e["straight"] = len(pts) == 2 or slant
    placed = 0
    eby = {e.get("id"): e for e in s["edges"]}
    for g in s.get("guards", []):
        e = eby.get(g.get("onFlow"))
        if e is None or e.get("id") in failed:
            continue
        if (e.get("id") in anew or guard_blocked(s, g, em)) and place_guard(s, g, e, em):
            placed += 1
    for g in s.get("guards", []):
        if not g.get("onFlow") and g.get("near") and guard_blocked(s, g, em) and place_question(s, g, em):
            placed += 1
    s["unrouted"] = failed
    return len(anew) - len([f for f in failed if f in anew]), placed
