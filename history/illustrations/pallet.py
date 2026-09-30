# Draws the pallet of boxes (the Fulfilment figures' "pic03", a photo of
# 400 x 361 px) as a greyscale vector picture, in 3D: an EPAL pallet (epal.py)
# with a stack of 2 x 2 x 2 boxes on it, drawn through the camera fitted to
# the photo (camera.py). The print on the boxes is measured once, in mm on a
# box face (backproject.py), and every box carries the same.
import json, math
import numpy as np
import epal
from camera import project

import os
from paths import HERE, WORK, PARTS
CAM = json.load(open(os.path.join(WORK, 'camera.json')))
BX0, BZ0, BXL, BZL, YT = CAM[7:]      # the stack: front-left corner, size, top (mm)
XS = [BX0, 639.4, BX0 + BXL]          # the boxes along the front (the seam measured)
ZS = [BZ0, 463.2, BZ0 + BZL]          # and along the side
YS = [144, 571.5, YT]                 # the two tiers

def pr(P):
    return [tuple(q) for q in project(CAM, np.array(P, float))]

out = []
def P(pts):
    return ' '.join('%.2f,%.2f' % p for p in pts)
def poly(pts, fill, stroke=None, sw=0.6):
    s = ' stroke="%s" stroke-width="%s" stroke-linejoin="round"' % (stroke, sw) if stroke else ''
    out.append('<polygon points="%s" fill="%s"%s/>' % (P(pts), fill, s))
def path(rings, fill):
    d = ' '.join('M' + ' L'.join('%.2f,%.2f' % p for p in r) + 'Z' for r in rings)
    out.append('<path d="%s" fill="%s" fill-rule="evenodd"/>' % (d, fill))
def pline(pts, stroke, sw=1.0):
    out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%.2f" '
               'stroke-linecap="round" stroke-linejoin="round"/>' % (P(pts), stroke, sw))

# tones: the photo's own brightness per surface
CARD_F, CARD_S = '#acacac', '#8e8e8e'
EDGE, GAP, LIT = '#5c5c5c', '#4a4a4a', '#c8c8c8'
INK, TAPE = '#262626', '#5a5a5a'

# ---- the pallet ----
def emit(pts, t, fname, part):
    g = int(255 * t)
    poly([tuple(q) for q in pts], '#%02x%02x%02x' % (g, g, g), EDGE, 0.5)
    layer, name, x, y, z, grain = part
    if layer == 'block' and fname in ('front', 'left') and t > 0.6:   # upright grain
        lo, hi = (x if fname == 'front' else z)
        for k in range(1, 5):
            u = lo + (hi - lo) * k / 5
            ends = ([(u, y[0] + 8, z[0]), (u, y[1] - 8, z[0])] if fname == 'front'
                    else [(x[0], y[0] + 8, u), (x[0], y[1] - 8, u)])
            pline(pr(ends), '#%02x%02x%02x' % ((g - 24,) * 3), 0.6)
epal.draw(lambda Q: project(CAM, Q), CAM[4:7], emit)

# ---- the boxes: the stack's two visible faces, the seams, the tiers ----
F = lambda x, y: (x, y, BZ0)           # a point on the stack's front, mm
S = lambda z, y: (BX0, y, z)           # a point on its left side
poly(pr([S(ZS[0], YS[0]), S(ZS[2], YS[0]), S(ZS[2], YT), S(ZS[0], YT)]), CARD_S, EDGE, 0.8)
poly(pr([F(XS[0], YS[0]), F(XS[2], YS[0]), F(XS[2], YT), F(XS[0], YT)]), CARD_F, EDGE, 0.8)
pline(pr([F(XS[1], YS[0]), F(XS[1], YT)]), GAP, 1.4)
pline(pr([F(XS[1] + 6, YS[0] + 2), F(XS[1] + 6, YT - 2)]), LIT, 0.8)
pline(pr([S(ZS[1], YS[0]), S(ZS[1], YT)]), GAP, 1.4)
pline(pr([S(ZS[1] - 12, YS[0] + 2), S(ZS[1] - 12, YT - 2)]), '#a4a4a4', 0.8)
pline(pr([S(ZS[2], YS[1]), S(ZS[0], YS[1]), F(XS[2], YS[1])]), GAP, 1.5)
pline(pr([F(XS[0], YS[1] - 4), F(XS[2], YS[1] - 4)]), LIT, 0.8)
pline(pr([S(ZS[2], YS[1] - 4), S(ZS[0], YS[1] - 4)]), '#a4a4a4', 0.8)
pline(pr([S(ZS[2], YT), S(ZS[0], YT), F(XS[2], YT)]), '#e6e6e6', 1.2)
pline(pr([F(XS[0] + 3, YS[0] + 2), F(XS[0] + 3, YT - 2)]), '#cfcfcf', 1.0)

# ---- the print, in mm on a box face: (u across, v up) from the face's
# lower-left corner; `at` maps it to a point in the picture ----
def rect(u0, v0, u1, v1):
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
def frame_ring(u0, v0, u1, v1, w):
    return [rect(u0, v0, u1, v1), rect(u0 + w, v0 + w, u1 - w, v1 - w)]
def arc(cu, cv, r, a0, a1, n=16):
    return [(cu + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
             cv + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]
def thick(p, q, w):
    """a straight stroke from p to q, w mm wide, as a polygon"""
    (x1, y1), (x2, y2) = p, q
    L = math.hypot(x2 - x1, y2 - y1); nx, ny = -(y2 - y1) / L * w / 2, (x2 - x1) / L * w / 2
    return [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)]
def stroke_path(pts, w):
    return [thick(pts[i], pts[i + 1], w) for i in range(len(pts) - 1)]

# the handling marks (ISO 780), 82 x 88 mm frames, 32 mm above the foot
MARK_U = [(44, 126), (151, 231), (257, 340)]
MARK_V = (32, 120)
def this_way_up(u0, v0, u1, v1):
    g = lambda s, t: (u0 + (u1 - u0) * s, v1 - (v1 - v0) * t)   # s right, t down, in the frame
    shapes = []
    for s in (0.36, 0.64):
        shapes.append([g(s, 0.1), g(s + 0.12, 0.36), g(s + 0.045, 0.36), g(s + 0.045, 0.72),
                       g(s - 0.045, 0.72), g(s - 0.045, 0.36), g(s - 0.12, 0.36)])
    shapes.append([g(0.16, 0.8), g(0.84, 0.8), g(0.84, 0.89), g(0.16, 0.89)])
    return shapes, []
def fragile(u0, v0, u1, v1):
    g = lambda s, t: (u0 + (u1 - u0) * s, v1 - (v1 - v0) * t)
    shapes, strokes = [], []
    # two glasses with straight-sided cups: the left drawn in outline, the right filled
    def cup(s0):
        return [g(s0 - 0.13, 0.12), g(s0 + 0.13, 0.12), g(s0 + 0.12, 0.42), g(s0 + 0.07, 0.5),
                g(s0 - 0.07, 0.5), g(s0 - 0.12, 0.42)]
    left = cup(0.31)
    strokes += stroke_path(left + [left[0]], 2.4)
    shapes.append(cup(0.69))
    for sx in (0.31, 0.69):
        strokes += stroke_path([g(sx, 0.5), g(sx, 0.8)], 2.8)
        strokes += stroke_path([g(sx - 0.11, 0.82), g(sx + 0.11, 0.82)], 3.4)
    return shapes + strokes, []
def keep_dry(u0, v0, u1, v1):
    g = lambda s, t: (u0 + (u1 - u0) * s, v1 - (v1 - v0) * t)
    top = [g(0.5 + 0.4 * math.cos(math.radians(a)), 0.48 - 0.38 * math.sin(math.radians(a)))
           for a in range(180, -1, -12)]
    scallops = []
    for i in range(3, 0, -1):   # three scallops along the canopy's edge, right to left
        a, b = 0.1 + 0.8 * i / 3, 0.1 + 0.8 * (i - 1) / 3
        m = (a + b) / 2
        scallops += [g(m, 0.42)]
        scallops += [g(b, 0.48)]
    shapes = [top + scallops]
    shapes += stroke_path([g(0.5, 0.45), g(0.5, 0.8), g(0.47, 0.87), g(0.4, 0.88), g(0.35, 0.82)], 3.4)
    return shapes, []
GLYPHS = [this_way_up, fragile, keep_dry]

# the address label: 256 x 74 mm, 299 mm above the foot
LABEL = (46, 299, 302, 373)
BARS = [(0.05, 0.075), (0.09, 0.1), (0.115, 0.14), (0.155, 0.165), (0.18, 0.2),
        (0.215, 0.225), (0.24, 0.27), (0.29, 0.3), (0.32, 0.345), (0.36, 0.37), (0.385, 0.42)]
def label(u0, v0, u1, v1):
    g = lambda s, t: (u0 + (u1 - u0) * s, v1 - (v1 - v0) * t)
    white = [[g(0, 0), g(1, 0), g(1, 1), g(0, 1)]]
    ink = [[g(a, 0.14), g(b, 0.14), g(b, 0.86), g(a, 0.86)] for a, b in BARS]
    for t, w, s1 in ((0.2, 0.08, 0.96), (0.33, 0.08, 0.92)):          # two bold lines
        ink.append([g(0.5, t - w / 2), g(s1, t - w / 2), g(s1, t + w / 2), g(0.5, t + w / 2)])
    grey = [[g(0.5, t - 0.02), g(s1, t - 0.02), g(s1, t + 0.02), g(0.5, t + 0.02)]
            for t, s1 in ((0.5, 0.94), (0.64, 0.9), (0.78, 0.86))]    # three thin ones
    brackets = []
    for s, t, ds, dt in ((0, 0, 1, 1), (1, 0, -1, 1), (1, 1, -1, -1), (0, 1, 1, -1)):
        o = (-0.012 * ds, -0.04 * dt)
        c = (s + o[0], t + o[1])
        brackets.append([g(*c), g(c[0] + 0.07 * ds, c[1]), g(c[0] + 0.07 * ds, c[1] + 0.05 * dt),
                         g(c[0] + 0.02 * ds, c[1] + 0.05 * dt), g(c[0] + 0.02 * ds, c[1] + 0.22 * dt),
                         g(c[0], c[1] + 0.22 * dt)])
    return white, ink, grey, brackets

# the recycling mark (the Moebius loop, in outline), about 100 mm across,
# centred 80 mm from the box's front edge and 80 mm above its foot, on the side; and the tape of the top flaps, 50 mm wide,
# centred on the side, coming 100 mm down
def moebius(cu, cv, size):
    """The recycling symbol as Wikipedia draws it (Recycle001.svg, Wikimedia
    Commons, public domain: its six outlines, the curves flattened), size mm
    across, centred at (cu, cv); seen from outside the side, whose u runs
    from the box's front edge back, so the symbol's right is toward u = 0."""
    import re
    src = open(os.path.join(HERE, 'Recycle001.svg')).read()
    rings = []
    for d in re.findall(r'<path d="([^"]+)"', src):
        toks = re.findall(r'[MCz]|-?[\d.]+', d)
        pts, i, cur = [], 0, None
        while i < len(toks):
            t = toks[i]
            if t == 'M':
                cur = (float(toks[i + 1]), float(toks[i + 2])); pts.append(cur); i += 3
            elif t == 'C':
                c1 = (float(toks[i + 1]), float(toks[i + 2])); c2 = (float(toks[i + 3]), float(toks[i + 4]))
                e = (float(toks[i + 5]), float(toks[i + 6]))
                for k in range(1, 9):
                    q = k / 8
                    pts.append(tuple((1 - q) ** 3 * cur[j] + 3 * (1 - q) ** 2 * q * c1[j] + 3 * (1 - q) * q ** 2 * c2[j] + q ** 3 * e[j]
                                     for j in range(2)))
                cur = e; i += 7
            else:
                i += 1
        rings.append(pts)
    # the file draws each arrow in two halves, a small gap apart at the fold:
    # joined here into one outline per arrow (the gap between arrows is twice as wide)
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    polys = [Polygon(r).buffer(0) for r in rings]
    arrows, used = [], set()
    for a in range(len(polys)):
        if a in used: continue
        b = min((j for j in range(len(polys)) if j != a and j not in used), key=lambda j: polys[a].distance(polys[j]))
        used |= {a, b}
        merged = unary_union([polys[a].buffer(16, join_style=2), polys[b].buffer(16, join_style=2)]).buffer(-16, join_style=2)
        arrows.append(list(merged.exterior.coords))
    rings = arrows
    allp = np.array([p for r in rings for p in r])
    (x0, y0), (x1, y1) = allp.min(0), allp.max(0)
    k = size / (x1 - x0); mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    return [[(cu - (x - mx) * k, cv - (y - my) * k) for x, y in r] for r in rings]

for bi in range(2):
    for ti in range(2):
        at = lambda u, v, bi=bi, ti=ti: F(XS[bi] + u, YS[ti] + v)
        prj = lambda pts: pr([at(*p) for p in pts])
        for (u0, u1), glyph in zip(MARK_U, GLYPHS):
            v0, v1 = MARK_V
            path([prj(r) for r in frame_ring(u0, v0, u1, v1, 4.5)], INK)
            shapes, _ = glyph(u0 + 4.5, v0 + 4.5, u1 - 4.5, v1 - 4.5)
            for sh in shapes:
                poly(prj(sh), INK)
        white, ink, grey, brackets = label(*LABEL)
        for sh in white: poly(prj(sh), '#ffffff')
        for sh in ink: poly(prj(sh), INK)
        for sh in grey: poly(prj(sh), '#6e6e6e')
        for sh in brackets: poly(prj(sh), INK)
for bj in range(2):
    for ti in range(2):
        # on the side, u runs from the box's front edge (small Z) back
        at = lambda u, v, bj=bj, ti=ti: S(ZS[bj] + u, YS[ti] + v)
        prj = lambda pts: pr([at(*p) for p in pts])
        for r in moebius(80, 80, 100):
            poly(prj(r), 'none', '#303030', 0.9)
        box_h = YS[ti + 1] - YS[ti]; mid = (ZS[bj + 1] - ZS[bj]) / 2
        poly(prj(rect(mid - 35, box_h - 100, mid + 35, box_h)), TAPE)

svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 361" width="400" height="361">\n'
       '<title>Pallet of boxes</title>\n' + '\n'.join(out) + '\n</svg>\n')
os.makedirs(PARTS, exist_ok=True)
open(os.path.join(PARTS, 'pallet.svg'), 'w').write(svg)
print(len(out), 'elements', len(svg), 'bytes')
