"""Make every arrow at least 3 times its head long (the stretch after its
last bend), by inserting space across the whole figure, as draw.io's own
"insert space" does: a band of height for an up/down arrow, a column of width
for a left/right one. Everything beyond the cut moves by the extra length;
a container the cut runs through (the pool, a lane, a phase box) grows by it;
a shape keeps its size, and stays or moves whole past the cut, wherever every
flow still meets it within its side (else it grows too). Line ends keep their
point on the page, so level and upright flows stay level and upright, and
nothing comes to overlap.

    python3 insert_space.py <diagrams dir> [<figure> ...]
"""
import glob, math, os, re, sys, collections
import xml.etree.ElementTree as ET

RATIO = 3.0


def style(c):
    return [p.split('=', 1) if '=' in p else [p, None] for p in (c.get('style') or '').split(';') if p]


def put(c, pairs):
    c.set('style', ''.join((k if v is None else '%s=%s' % (k, v)) + ';' for k, v in pairs))


def num(v, places=6):
    s = ('%.*f' % (places, v)).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


class Figure:
    def __init__(self, path):
        self.path = path
        self.tree = ET.parse(path)
        self.model = self.tree.getroot().find('.//mxGraphModel')
        self.root = self.model.find('root')
        self.cells = {}
        for el in self.root:
            c = el if el.tag == 'mxCell' else el.find('mxCell')
            self.cells[el.get('id')] = (el, c)

    def kind(self, i):
        return self.cells[i][0].get('ubl-kind')

    def is_vertex(self, i):
        el, c = self.cells[i]
        g = c.find('mxGeometry') if c is not None else None
        return c is not None and c.get('vertex') == '1' and g is not None and g.get('relative') != '1'

    def boxes(self):
        """every vertex's page box (x0, y0, x1, y1)"""
        out = {}

        def place(i):
            if i in out:
                return out[i]
            if i not in self.cells or not self.is_vertex(i):
                return None
            el, c = self.cells[i]
            g = c.find('mxGeometry')
            p = place(c.get('parent'))
            px, py = (p[0], p[1]) if p else (0.0, 0.0)
            x, y = px + float(g.get('x', 0)), py + float(g.get('y', 0))
            out[i] = (x, y, x + float(g.get('width', 0)), y + float(g.get('height', 0)))
            return out[i]
        for i in self.cells:
            place(i)
        return out

    def flows(self, boxes):
        """(id, stretch start, stretch end, head) for every flow with a head"""
        out = []
        for i, (el, c) in self.cells.items():
            if c is None or c.get('edge') != '1':
                continue
            d = dict(style(c))
            if d.get('endArrow') in (None, 'none') or not c.get('target') or 'entryX' not in d:
                continue
            t = boxes[c.get('target')]
            q = (t[0] + float(d['entryX']) * (t[2] - t[0]), t[1] + float(d['entryY']) * (t[3] - t[1]))
            g = c.find('mxGeometry')
            arr = g.find('Array')
            pb = boxes.get(c.get('parent'))
            ox, oy = (pb[0], pb[1]) if pb else (0.0, 0.0)
            if arr is not None and len(arr):
                m = arr.findall('mxPoint')[-1]
                p = (float(m.get('x', 0)) + ox, float(m.get('y', 0)) + oy)
            elif c.get('source') and 'exitX' in d:
                s = boxes[c.get('source')]
                p = (s[0] + float(d['exitX']) * (s[2] - s[0]), s[1] + float(d['exitY']) * (s[3] - s[1]))
            else:
                sp = g.find('mxPoint[@as="sourcePoint"]')
                if sp is None:
                    continue
                p = (float(sp.get('x')) + ox, float(sp.get('y')) + oy)
            out.append((i, p, q, float(d.get('endSize', 6))))
        return out

    def insert(self, axis, cut, extra):
        """space of `extra` px at page coordinate `cut` along axis 0 (x) or 1 (y)"""
        old = self.boxes()
        T = lambda v: v + extra if v > cut else v
        new = {i: tuple(T(v) if k % 2 == axis else v for k, v in enumerate(b)) for i, b in old.items()}
        # A shape the cut runs through (not a container) keeps its size where it
        # can: it stays, or moves whole past the cut, if every flow still meets
        # it within its side; only if neither does it grow with the space.
        ends = collections.defaultdict(list)
        for i, (el, c) in self.cells.items():
            if c is None or c.get('edge') != '1':
                continue
            d = dict(style(c))
            for end, key in ((c.get('source'), 'exit'), (c.get('target'), 'entry')):
                if end in old and key + 'X' in d:
                    ob = old[end]; f = float(d[key + ('X' if axis == 0 else 'Y')])
                    ends[end].append(ob[axis] + f * (ob[axis + 2] - ob[axis]))
        for i, ob in old.items():
            if self.kind(i) in FIXED + ('band-divider', 'band-title', 'lane-divider', None) or not ob[axis] < cut < ob[axis + 2]:
                continue
            size = ob[axis + 2] - ob[axis]
            options = [(ob[axis], ob[axis + 2]), (ob[axis] + extra, ob[axis + 2] + extra)]
            if (ob[axis] + ob[axis + 2]) / 2 > cut:
                options.reverse()          # try the side its middle is on first
            for a0, a1 in options:
                if all(a0 + 1 <= T(v) <= a1 - 1 or (T(v) in (a0, a1)) for v in ends[i]):
                    b = list(new[i]); b[axis], b[axis + 2] = a0, a1; new[i] = tuple(b)
                    self.kept = getattr(self, 'kept', 0) + 1
                    break
            else:
                self.stretched = getattr(self, 'stretched', 0) + 1
        # geometry, relative to the parent's new place
        for i, b in new.items():
            el, c = self.cells[i]
            g = c.find('mxGeometry')
            p = new.get(c.get('parent'))
            px, py = (p[0], p[1]) if p else (0.0, 0.0)
            g.set('x', num(b[0] - px, 2)); g.set('y', num(b[1] - py, 2))
            g.set('width', num(b[2] - b[0], 2)); g.set('height', num(b[3] - b[1], 2))
        # flows: their ends keep their page point; bends and free ends follow
        for i, (el, c) in self.cells.items():
            if c is None or c.get('edge') != '1':
                continue
            pairs = style(c); d = dict(pairs); changed = False
            for end, key in ((c.get('source'), 'exit'), (c.get('target'), 'entry')):
                if end in old and key + 'X' in d:
                    ob, nb = old[end], new[end]
                    f = float(d[key + ('X' if axis == 0 else 'Y')])
                    pt = ob[axis] + f * (ob[axis + 2] - ob[axis])
                    nf = (T(pt) - nb[axis]) / (nb[axis + 2] - nb[axis])
                    if abs(nf - f) > 1e-9:
                        d[key + ('X' if axis == 0 else 'Y')] = num(nf); changed = True
            if changed:
                put(c, [[k, d.get(k, v)] for k, v in pairs])
            g = c.find('mxGeometry')
            po, pn = old.get(c.get('parent')), new.get(c.get('parent'))
            for pt in g.iter('mxPoint'):
                if pt.get('as') == 'offset':
                    continue
                k = 'xy'[axis]
                o = (po[axis] if po else 0.0)
                a = float(pt.get(k, 0)) + o
                pt.set(k, num(T(a) - (pn[axis] if pn else 0.0), 2))
        # an element's own connection points (points=) follow, where it grew
        for i in old:
            el, c = self.cells[i]
            pairs = style(c); d = dict(pairs)
            if not d.get('points') or d['points'] == '[]' or old[i] == new[i]:
                continue
            ob, nb = old[i], new[i]
            pts = [[float(v) for v in p.split(',')] for p in d['points'][2:-2].split('],[')]
            for p in pts:
                a = ob[axis] + p[axis] * (ob[axis + 2] - ob[axis])
                p[axis] = (T(a) - nb[axis]) / (nb[axis + 2] - nb[axis])
            d['points'] = '[%s]' % ','.join('[%s,%s]' % (num(x), num(y)) for x, y in pts)
            put(c, [[k, d.get(k, v)] for k, v in pairs])
        # the page
        key = 'pageWidth' if axis == 0 else 'pageHeight'
        self.model.set(key, str(int(round(float(self.model.get(key)) + extra))))

    def save(self):
        self.tree.write(self.path, encoding='unicode')


FIXED = ('frame', 'lane', 'phase-boundary')     # containers: they grow where cut


def fix(path, log):
    fig = Figure(path)
    grown = collections.Counter()
    for _ in range(400):
        boxes = fig.boxes()
        short = []
        for i, p, q, head in fig.flows(boxes):
            L = math.dist(p, q)
            if L + 0.01 < RATIO * head:
                short.append((RATIO * head - L, i, p, q, head))
        if not short:
            break
        short.sort(reverse=True)
        need, i, p, q, head = short[0]
        dx, dy = abs(q[0] - p[0]), abs(q[1] - p[1])
        axis = 1 if dy >= dx else 0
        other = dx if axis == 1 else dy
        along = dy if axis == 1 else dx
        extra = math.ceil(math.sqrt(max(0.0, (RATIO * head) ** 2 - other ** 2)) - along - 1e-9)
        lo, hi = sorted((p[axis], q[axis]))
        # the cut: through the stretch, where it crosses the fewest shapes
        # (containers and lines drawn across the figure do not count), nearest
        # the middle
        solid = [b for j, b in boxes.items() if fig.kind(j) not in FIXED + ('band-divider', 'band-title', 'lane-divider', None)]
        best = None
        for k in range(int(math.floor(lo)) + 1, int(math.ceil(hi))):
            c = k + 0.5
            if not lo < c < hi:
                continue
            n = sum(1 for b in solid if b[axis] < c < b[axis + 2])
            score = (n, abs(c - (lo + hi) / 2))
            if best is None or score < best[0]:
                best = (score, c)
        if best is None:
            best = ((0, 0), (lo + hi) / 2)
        fig.insert(axis, best[1], extra)
        grown['xy'[axis]] += extra
        log.append((os.path.basename(path)[:-7], i, 'height' if axis else 'width', extra, best[0][0]))
    # by hand, found on the way: a flow that left its document 1 px beside it
    # (from rounding before this step) leaves from its corner
    if os.path.basename(path) == 'UBL-2.2-CPFR-CreateOrderForecast.drawio':
        el, c = fig.cells['flow-forecast-revision-order-to-receive-revision']
        put(c, [[k, '0' if k == 'exitX' else v] for k, v in style(c)])
        c.find('mxGeometry').find('Array').findall('mxPoint')[0].set('x', '392')
    fig.save()
    return grown


if __name__ == '__main__':
    d = sys.argv[1]
    figs = sys.argv[2:] or sorted(os.listdir(d))
    log = []
    total = {}
    for n in figs:
        p = os.path.join(d, n, n + '.drawio')
        if os.path.exists(p):
            g = fix(p, log)
            if g:
                total[n] = g
    for r in log:
        print('%-50s %-70s +%-2d %s%s' % (r[0][4:], r[1][:70], r[3], r[2], '' if not r[4] else '  (cut through %d shape%s)' % (r[4], 's' if r[4] > 1 else '')))
    print('insertions: %d in %d figures' % (len(log), len(total)))
    print('growth per figure (px):', {k[4:]: dict(v) for k, v in sorted(total.items(), key=lambda kv: -sum(kv[1].values()))})
