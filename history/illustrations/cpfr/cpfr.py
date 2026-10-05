"""What the CPFR step drawings share: a drawing measured on its UBL 2.2 PNG, written as a draw.io illustration.

The drawing edits as a draw.io diagram: each step panel is a container (what is in it is its child, and moves
with it); every flow is attached to the shapes at its ends, at the points the PNG has (exit/entry), and routed
through its bends (as the UML diagrams have them: edgeStyle=none), so it follows when a shape moves; a guard is its flow's own label.

Every shape is given in the PNG's px and divided by S, the PNG's px per the drawing's: the drawing is the
figure at the size of its source (the iSURF D6.1.1 figure, framed), the PNG that times S with a frame of F px
round it. The pictures are the parts in illustrations/parts/ (cpfr-*), where parts_fit.py found them.
"""
import base64, html, json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PARTS = os.path.join(ROOT, 'illustrations', 'parts')
FONT = 'fontFamily=Helvetica;'
GREY_TEXT = '#505050'


class Drawing:
    def __init__(self, name, png_size, frame, source_width):
        self.name, (self.PW, self.PH), self.F = name, png_size, frame
        self.S = (self.PW - 2 * frame) / source_width
        self.v, self.e, self.guards, self.n = [], [], [], 0
        self.fit = json.load(open(os.path.join(HERE, 'parts_fit.json')))[name]

    def nid(self):
        self.n += 1
        return 'c%d' % self.n

    def vertex(self, style, box, label='', obj=None, panel=False):
        i = self.nid()
        self.v.append(dict(id=i, style=style, box=tuple(box), label=label, obj=obj, panel=panel))
        return i

    def edge(self, pts, src=None, tgt=None):
        """a flow through pts (PNG px); its ends attached to the shapes they lie in (or src, tgt: ids)"""
        self.e.append(dict(id=self.nid(), pts=[tuple(p) for p in pts], src=src, tgt=tgt))

    def picture(self, part, key, flip=False):
        x, y, w, h = self.fit[key]
        b64 = base64.b64encode(open(os.path.join(PARTS, part + '.svg'), 'rb').read()).decode()
        return self.vertex('shape=image;imageAspect=0;verticalLabelPosition=bottom;%simage=data:image/svg+xml,%s;' % ('flipH=1;' if flip else '', b64),
                           (x, y, x + w, y + h), obj={'ubl-part': part})

    def text(self, label, box, size, color='#000000', align='center', extra=''):
        return self.vertex('text;html=1;whiteSpace=nowrap;overflow=visible;align=%s;verticalAlign=middle;spacing=0;fontSize=%s;fontColor=%s;%s%s'
                           % (align, size, color, FONT, extra), box, label)

    # the figures' own shapes
    def panel(self, box, dashed=False, label='', size=15.3):
        st = 'rounded=1;absoluteArcSize=1;arcSize=22;whiteSpace=wrap;html=1;fillColor=#e0e0e0;strokeColor=#000000;strokeWidth=1;'
        if dashed:
            return self.vertex(st + 'dashed=1;dashPattern=7 4;fontSize=%s;fontColor=%s;%s' % (size, GREY_TEXT, FONT), box, label)
        return self.vertex(st + 'container=1;collapsible=0;', box, label, panel=True)

    def title(self, label, box, size=12.7):
        return self.text(label, box, size, GREY_TEXT, 'right')

    def arrow(self, label, x0, x1, y0, y1, body, head, direction, size=13, fill='#e4e4e4', cx=None):
        """a block arrow: direction 'west', 'east', or None for both; body: its shaft's height, head: the head's
        length (PNG px); the label centred at cx (default 8.5 px right of the shape's middle)"""
        w = x1 - x0
        off = 2 * ((cx if cx is not None else (x0 + x1) / 2 + 8.5) - (x0 + x1) / 2)
        st = 'html=1;whiteSpace=wrap;fillColor=%s;strokeColor=#000000;strokeWidth=1;fontSize=%s;fontColor=#404040;%s' % (fill, size, FONT)
        if direction:
            st += '%s=%.1f;shape=singleArrow;direction=%s;arrowWidth=%.3f;arrowSize=%.3f;' % (
                'spacingLeft' if off >= 0 else 'spacingRight', abs(off) / self.S, direction, body / (y1 - y0), head / w)
        else:
            st += 'shape=doubleArrow;arrowWidth=%.3f;arrowSize=%.3f;' % (body / (y1 - y0), head / w)
        return self.vertex(st, (x0, y0, x1, y1), label)

    def decision(self, label, box, size=10.2, lift=10):
        return self.vertex('rhombus;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#000000;strokeWidth=1;fontSize=%s;spacingBottom=%.1f;%s'
                           % (size, lift / self.S, FONT), box, label)

    def resolve(self, box, size=15.25):
        """the Resolve Exception box: over the people at their desks, see-through, as the PNG has it"""
        return self.vertex('rounded=0;whiteSpace=wrap;html=1;fillColor=#7f7f7f;fillOpacity=55;strokeColor=#000000;strokeWidth=1;dashed=1;'
                           'dashPattern=8 3.5 1.5 3.5;fontSize=%s;%s' % (size, FONT), box, 'Resolve Exception')

    def guard(self, label, cx, cy, size=10):
        """a guard: the label of the flow it lies on, centred where the PNG has it"""
        self.guards.append((label, cx, cy, size))

    def end(self, box):
        return self.vertex('ellipse;html=1;shape=endState;fillColor=#000000;strokeColor=#000000;strokeWidth=1;', box)

    # writing
    def write(self):
        S, f = self.S, lambda v: '%.2f' % (v / self.S)
        V = {c['id']: c for c in self.v}
        inside = lambda b, p, m=0: b[0] - m <= p[0] <= b[2] + m and b[1] - m <= p[1] <= b[3] + m
        area = lambda b: (b[2] - b[0]) * (b[3] - b[1])
        panels = [c for c in self.v if c['panel']]
        # each shape's parent: the panel its middle is in
        for c in self.v:
            b = c['box']; mid = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
            c['parent'] = next((p['id'] for p in panels if p is not c and inside(p['box'], mid)), '1')
        origin = lambda pid: (0, 0) if pid == '1' else V[pid]['box'][:2]
        # each flow's ends: the smallest shape (not a panel, unless only a panel) the end lies in
        def terminal(p):
            cs = [c for c in self.v if inside(c['box'], p, 1.5)]
            cs.sort(key=lambda c: (c['panel'], area(c['box'])))
            return cs[0]['id'] if cs else None
        for e in self.e:
            e['src'] = e['src'] or terminal(e['pts'][0]); e['tgt'] = e['tgt'] or terminal(e['pts'][-1])
            ps = [V[e[k]]['parent'] for k in ('src', 'tgt')]
            e['parent'] = ps[0] if ps[0] == ps[1] and ps[0] != '1' and all(inside(V[ps[0]]['box'], q) for q in e['pts']) else '1'
            e['label'] = None
        # each guard on the flow it lies on: its place along the flow and its offset from it
        def along(pts, q):
            best, run, tot = None, 0, sum(math.dist(a, b) for a, b in zip(pts[:-1], pts[1:]))
            for a, b in zip(pts[:-1], pts[1:]):
                L = math.dist(a, b) or 1e-9; t = max(0, min(1, ((q[0] - a[0]) * (b[0] - a[0]) + (q[1] - a[1]) * (b[1] - a[1])) / L ** 2))
                o = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])); d = math.dist(o, q)
                if best is None or d < best[0]:
                    best = (d, (run + t * L) / tot, (q[0] - o[0], q[1] - o[1]))
                run += L
            return best
        for lab, cx, cy, size in self.guards:
            d, t, off = min((along(e['pts'], (cx, cy)) + (e,) for e in self.e), key=lambda r: r[0])[:3]
            e = min(self.e, key=lambda e: along(e['pts'], (cx, cy))[0])
            e['label'] = (lab, 2 * t - 1, off, size)
        cells = ['<object id="frame" label="" ubl-kind="illustration" ubl-png-scale="%.4f"><mxCell style="rounded=0;whiteSpace=wrap;html=1;'
                 'fillColor=none;strokeColor=#000000;strokeWidth=%.2f;" vertex="1" parent="1"><mxGeometry x="%.2f" y="%.2f" width="%.2f" '
                 'height="%.2f" as="geometry"/></mxCell></object>' % (S, self.F / S, self.F / S / 2, self.F / S / 2, self.PW / S - self.F / S, self.PH / S - self.F / S)]
        def vcell(c):
            o = origin(c['parent']); b = c['box']
            g = '<mxGeometry x="%s" y="%s" width="%s" height="%s" as="geometry"/>' % (f(b[0] - o[0]), f(b[1] - o[1]), f(b[2] - b[0]), f(b[3] - b[1]))
            lab = html.escape(c['label'], quote=True)
            if c['obj']:
                attrs = ' '.join('%s="%s"' % (k, html.escape(v, quote=True)) for k, v in c['obj'].items())
                return '<object id="%s" label="%s" %s><mxCell style="%s" vertex="1" parent="%s">%s</mxCell></object>' % (c['id'], lab, attrs, c['style'], c['parent'], g)
            return '<mxCell id="%s" value="%s" style="%s" vertex="1" parent="%s">%s</mxCell>' % (c['id'], lab, c['style'], c['parent'], g)
        def point(c, p, which):
            """where the flow meets the shape, as draw.io's exit or entry: a fraction of the shape's box"""
            b = c['box']; fx, fy = (p[0] - b[0]) / (b[2] - b[0]), (p[1] - b[1]) / (b[3] - b[1])
            return '%sX=%.4f;%sY=%.4f;%sDx=0;%sDy=0;%sPerimeter=0;' % (which, fx, which, fy, which, which, which)
        def ecell(e):
            o = origin(e['parent']); pts = e['pts']
            st = 'edgeStyle=none;endArrow=block;endFill=1;endSize=4;html=1;rounded=0;strokeWidth=1;'
            st += point(V[e['src']], pts[0], 'exit') + point(V[e['tgt']], pts[-1], 'entry')
            lab, geo_lab = '', ''
            if e['label']:
                l, x, off, size = e['label']
                lab = html.escape(l, quote=True)
                st += 'labelBackgroundColor=#ffffff;fontSize=%s;%s' % (size, FONT)
                geo_lab = ' x="%.4f"' % x
                off = '<mxPoint x="%s" y="%s" as="offset"/>' % (f(off[0]), f(off[1]))
            else:
                off = ''
            mids = ''.join('<mxPoint x="%s" y="%s"/>' % (f(x - o[0]), f(y - o[1])) for x, y in pts[1:-1])
            return ('<mxCell id="%s" value="%s" style="%s" edge="1" parent="%s" source="%s" target="%s"><mxGeometry%s relative="1" as="geometry">%s%s'
                    '</mxGeometry></mxCell>' % (e['id'], lab, st, e['parent'], e['src'], e['tgt'], geo_lab, off,
                                                ('<Array as="points">%s</Array>' % mids) if mids else ''))
        # in the order they were drawn: a panel before what is in it, a flow after its ends
        order = sorted(self.v + self.e, key=lambda c: int(c['id'][1:]))
        done = set()
        for c in order:
            cells.append(ecell(c) if 'pts' in c else vcell(c))
        W, H = self.PW / S, self.PH / S
        xml = ('<mxfile host="UBL-TC" agent="UBL artwork pipeline, the CPFR step illustrations (history/illustrations/cpfr)" type="device">'
               '<diagram id="%s" name="%s"><mxGraphModel grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" '
               'page="1" pageScale="1" pageWidth="%d" pageHeight="%d" math="0" shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
               '%s</root></mxGraphModel></diagram></mxfile>' % (self.name, self.name, round(W), round(H), ''.join(cells)))
        d = os.path.join(ROOT, 'diagrams', self.name)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, self.name + '.drawio'), 'w', encoding='utf-8').write(xml)
        print(self.name, '%.1f x %.1f' % (W, H), len(cells), 'cells,', sum(e['parent'] != '1' for e in self.e), 'of', len(self.e), 'flows in a panel')
