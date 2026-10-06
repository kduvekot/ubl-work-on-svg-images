"""The Group C drawings (reference figures drawn from the UBL repository's PNGs): helpers on
history/group-b/lib_b.py. Everything is given in PNG px (of art/<figure>.png) and written at the scale
`S` (PNG px per drawing px), so a build script reads like the measurements it was made from.

    f = Figure('UBL-2.2-X', W, H, S, __file__, grey=False)
    f.frame(stroke px)
    f.box('id', x0, y0, x1, y1, stroke=5, fill='white'|'grey'|None, dashed=(dash, gap), arc=radius, shape='rect'|'ellipse'|'triangle-w'..)
    f.label('id', ['line 1', 'line 2'], cap_top, cx=.. | left=.., font=12, pitch=.., italic=False, bold=True)
    f.flow('id', source, target, (x, y), (x, y), via=[(x, y)...], head='block', dash=(dash, gap))
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'group-b'))
from lib_b import Fig, n, q, stencil  # noqa: E402,F401

GREY = '#e6e6e6'            # the PNGs' fill, 230 of 255


class Figure(Fig):
    def __init__(self, name, W, H, S, script, grey=False):
        self.S, self.W, self.H = S, W, H
        self.turn = {}
        self.geo = {}          # id -> (x0, y0, x1, y1) PNG px, outer (stroke included)
        super().__init__(name, round(W / S, 2), round(H / S, 2), 'UBL artwork, Group C (history/group-c/%s)' % os.path.basename(script))
        self.grey = grey

    def r(self, v):
        return round(v / self.S, 2)

    def frame(self, stroke=9, notation='reference', **extra):
        r, S = self.r, self.S
        d = stroke / 2
        extra['ubl-notation'] = notation
        if self.grey:
            extra['ubl-art'] = 'grey'
        self.vertex('frame', 'frame', '', 'rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeWidth=%s;' % n(stroke / S),
                    r(d), r(d), r(self.W - stroke), r(self.H - stroke), **extra)

    def box(self, ident, x0, y0, x1, y1, stroke=5, fill='white', dashed=None, arc=None, shape='rect', kind='box', **extra):
        """(x0, y0)-(x1, y1): the shape's OUTER edge in PNG px; `fill`: 'white', 'grey' or None;
        `dashed`: (dash, gap) in PNG px; `arc`: corner radius in PNG px (a rounded rectangle);
        `shape`: 'rect', 'ellipse', 'triangle-w' (apex left), 'triangle-e', 'triangle-n', 'triangle-s'"""
        r, S = self.r, self.S
        d = stroke / 2
        fillc = {'white': 'fillColor=#ffffff;', 'grey': 'fillColor=%s;' % GREY, None: 'fillColor=none;'}[fill]
        st = {'rect': 'rounded=0;', 'ellipse': 'ellipse;',
              'triangle-w': 'triangle;direction=west;', 'triangle-e': 'triangle;direction=east;',
              'triangle-n': 'triangle;direction=north;', 'triangle-s': 'triangle;direction=south;'}[shape]
        if arc:
            st = 'rounded=1;absoluteArcSize=1;arcSize=%s;' % n(round(2 * arc / S))   # arcSize is the diameter
        st += 'whiteSpace=wrap;html=1;' + fillc + 'strokeWidth=%s;' % n(stroke / S)
        if dashed:
            st += 'dashed=1;dashPattern=%s %s;' % (n(dashed[0] / S), n(dashed[1] / S))
        self.geo[ident] = (x0, y0, x1, y1)
        self.turn[ident] = shape.endswith('-w')     # a triangle that points west is turned half way: so are its exits
        self.vertex(ident, kind, '', st, r(x0 + d), r(y0 + d), r(x1 - x0 - stroke), r(y1 - y0 - stroke), **extra)

    TEXT = ('text;html=1;align=%s;verticalAlign=middle;whiteSpace=nowrap;strokeColor=none;fillColor=none;'
            'fontSize=%s;spacing=0;%s')

    def label(self, ident, lines, cap_top, cx=None, left=None, right=None, font=12, pitch=None, italic=False, bold=True,
             asc=0.72, shift=3, white=None, kind='text', **extra):
        """lines of text; the first line's capital top (PNG px) is `cap_top`; centred on `cx` or left-aligned
        with its ink at `left`; `pitch` the line distance in PNG px (default 1.15 times the font)"""
        r, S = self.r, self.S
        fpx = font * S
        nl = len(lines)
        pitch = pitch or 1.15 * fpx
        centre = cap_top + (asc - 0.3465) * fpx + (nl - 1) * pitch / 2 + shift
        h = nl * pitch
        label = '<br>'.join(lines)
        if nl > 1:
            label = '<div style="line-height: %d%%">%s</div>' % (round(100 * pitch / fpx), label)
        fs = ('fontStyle=%d;' % ((1 if bold else 0) + (2 if italic else 0))) if (bold or italic) else ''
        w = white or round(max(len(l) for l in lines) * (0.6 if bold else 0.52) * fpx + 30)     # wide enough for the longest line
        if not white:       # and inside the frame
            w = min(w, self.W - left - 10) if left is not None else min(w, right - 10) if right is not None else min(w, 2 * (cx - 10), 2 * (self.W - cx - 10))
        if left is not None:
            style = self.TEXT % ('left', n(font), fs)
            x = left
        elif right is not None:
            style = self.TEXT % ('right', n(font), fs)
            x = right - w
        else:
            style = self.TEXT % ('center', n(font), fs)
            x = cx - w / 2
        if white:
            style = style.replace('fillColor=none', 'fillColor=#ffffff')
        self.vertex(ident, kind, label, style, r(x), r(centre - h / 2), r(w), r(h), **extra)

    def flow(self, ident, source, target, p0, p1, via=(), stroke=5, head='block', start=None, dash=None,
             size=None, kind='flow', **extra):
        """an arrow from p0 (PNG px; on `source`'s edge) to p1 (on `target`'s edge), through `via`;
        `head`: draw.io's endArrow; `start`: its startArrow (a both-ended arrow)"""
        r, S = self.r, self.S

        def frac(shape, p):
            g = self.geo[shape]
            fx, fy = (p[0] - g[0]) / (g[2] - g[0]), (p[1] - g[1]) / (g[3] - g[1])
            return (1 - fx, 1 - fy) if self.turn[shape] else (fx, fy)
        st = 'html=1;rounded=0;endArrow=%s;endFill=%d;strokeWidth=%s;' % (head, 0 if head in ('open', 'openThin') else 1, n(stroke / S))
        if size:
            st += 'endSize=%s;' % n(size)
        if start:
            st += 'startArrow=%s;startFill=1;startSize=%s;' % (start, n(size or 6))
        if dash:
            st += 'dashed=1;dashPattern=%s %s;' % (n(dash[0] / S), n(dash[1] / S))
        if source in self.geo:
            fx, fy = frac(source, p0)
            st += 'exitX=%s;exitY=%s;exitDx=0;exitDy=0;exitPerimeter=0;' % (n(round(fx, 4)), n(round(fy, 4)))
        if target in self.geo:
            fx, fy = frac(target, p1)
            st += 'entryX=%s;entryY=%s;entryDx=0;entryDy=0;entryPerimeter=0;' % (n(round(fx, 4)), n(round(fy, 4)))
        pts = [(r(p0[0]), r(p0[1]))] + [(r(x), r(y)) for x, y in via] + [(r(p1[0]), r(p1[1]))]
        self.edge(ident, kind, '', st, pts, source=source, target=target, via=pts[1:-1], **extra)
