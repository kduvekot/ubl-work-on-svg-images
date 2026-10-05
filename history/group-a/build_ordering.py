"""UBL-2.3-OrderingProcess: the ordering collaboration of buyer and seller as a BPMN drawing.

The UBL repository has its source as an SVG made by bpmn-js (images/, sources/): vector, with every
element's BPMN id and place, but not an editable drawing. This reads that SVG and draws the same
collaboration as draw.io's own BPMN parts: two pools; tasks, exclusive gateways, a start event and
end events in them; sequence flows (filled head) and message flows (dashed, a circle at the sender,
an open head at the receiver) attached to their shapes, with the bends the SVG has. The BPMN ids of
the SVG are kept (ubl-bpmn-id). Places and sizes are the SVG's (text is 12 px there, as here)."""
import html, os, re
import xml.etree.ElementTree as ET
from lib import Fig

NS = '{http://www.w3.org/2000/svg}'
NAME = 'UBL-2.3-OrderingProcess'
svg = ET.parse(os.path.join(os.path.dirname(__file__), 'sources', 'UBL-2.3-OrderingProcess.svg')).getroot()
LINE = 'strokeWidth=2;'

shapes, flows, labels = {}, {}, {}


def lines_of(g):
    return [''.join(t.itertext()).strip() for t in g.iter(NS + 'tspan')]


def walk(e, off=(0, 0), pool=None):
    for g in e:
        if g.tag != NS + 'g':
            continue
        cls = g.get('class') or ''
        if 'djs-element' in cls:
            ident = g.get('data-element-id')
            m = re.match(r'matrix\(1 0 0 1 ([\d.-]+) ([\d.-]+)\)', g.get('transform') or '')
            o = (off[0] + float(m.group(1)), off[1] + float(m.group(2))) if m else off
            vis = g.find(NS + 'g')
            if 'djs-connection' in cls:
                d = vis.find(NS + 'path').get('d')
                pts = [tuple(float(v) for v in p.split(',')) for p in re.findall(r'[\d.]+,[\d.]+', d)]
                flows[ident] = pts
            elif ident.endswith('_label'):
                hit = g.find(NS + 'rect[@class="djs-hit"]')
                labels[ident[:-6]] = (o, float(hit.get('width')), float(hit.get('height')), lines_of(g))
            else:
                r = vis.find(NS + 'rect')
                c = vis.find(NS + 'circle')
                poly = vis.find(NS + 'polygon')
                if ident.startswith('Participant'):
                    shapes[ident] = dict(kind='pool', x=o[0], y=o[1], w=float(r.get('width')), h=float(r.get('height')), text=lines_of(g)[:1])
                    pool = ident
                elif ident.startswith('Task'):
                    shapes[ident] = dict(kind='task', x=o[0], y=o[1], w=100, h=80, text=lines_of(g), pool=pool)
                elif ident.startswith('ExclusiveGateway'):
                    shapes[ident] = dict(kind='gateway', x=o[0], y=o[1], w=50, h=50, text=[], pool=pool)
                elif ident.startswith('StartEvent'):
                    shapes[ident] = dict(kind='start', x=o[0], y=o[1], w=36, h=36, text=[], pool=pool)
                elif ident.startswith('EndEvent'):
                    shapes[ident] = dict(kind='end', x=o[0], y=o[1], w=36, h=36, text=[], pool=pool)
            for ch in g:
                if ch.get('class') == 'djs-children':
                    walk(ch, o, pool if not ident.startswith('Participant') else ident)
        else:
            walk(g, off, pool)


walk(svg)
pool_ids = [i for i, s in shapes.items() if s['kind'] == 'pool']
f = Fig(NAME, 1231, 818, 'UBL artwork, Group A (history/group-a/build_ordering.py)')
OX, OY = 150, 75      # the SVG's viewBox: its origin is the drawing's


def slug(t):
    return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')


ids, count = {}, {}
for i, s in shapes.items():
    base = {'pool': 'pool', 'task': 'task', 'gateway': 'gateway', 'start': 'start', 'end': 'end'}[s['kind']]
    name = slug(' '.join(s['text'])) if s['kind'] in ('pool', 'task') else ''
    owner = slug(shapes[s['pool']]['text'][0]) if s.get('pool') else ''
    ident = '-'.join(x for x in (base, owner if s['kind'] not in ('pool',) else '', name) if x)
    count[ident] = count.get(ident, 0) + 1
    ids[i] = ident if count[ident] == 1 else '%s-%d' % (ident, count[ident])
# the second of a kind in one party gets its number, the first keeps the bare name: number them all then
for ident, n_ in count.items():
    if n_ > 1:
        k = 0
        for i in shapes:
            if ids[i] == ident or ids[i].startswith(ident + '-') and ids[i][len(ident) + 1:].isdigit():
                k += 1
                ids[i] = '%s-%d' % (ident, k)

TASK = 'rounded=1;whiteSpace=wrap;html=1;absoluteArcSize=1;arcSize=20;fillColor=#ffffff;' + LINE
GATE = 'shape=mxgraph.bpmn.gateway2;perimeter=rhombusPerimeter;gwType=exclusive;outlineConnect=0;html=1;fillColor=#ffffff;' + LINE
START = 'shape=mxgraph.bpmn.shape;perimeter=ellipsePerimeter;outline=standard;symbol=general;html=1;fillColor=#ffffff;' + LINE
END = 'shape=mxgraph.bpmn.shape;perimeter=ellipsePerimeter;outline=end;symbol=terminate;html=1;fillColor=#ffffff;' + LINE
POOL = 'swimlane;html=1;horizontal=0;startSize=30;whiteSpace=wrap;fillColor=none;' + LINE

for i, s in shapes.items():
    if s['kind'] == 'pool':
        f.vertex(ids[i], 'pool', s['text'][0], POOL, s['x'] - OX, s['y'] - OY, s['w'], s['h'], **{'ubl-bpmn-id': i, 'ubl-notation': 'bpmn'})
for i, s in shapes.items():
    if s['kind'] == 'pool':
        continue
    p = shapes[s['pool']]
    st = {'task': TASK, 'gateway': GATE, 'start': START, 'end': END}[s['kind']]
    f.vertex(ids[i], s['kind'] if s['kind'] in ('task', 'gateway') else 'event', '<br>'.join(s['text']), st,
             s['x'] - p['x'], s['y'] - p['y'], s['w'], s['h'], parent=ids[s['pool']],
             **{'ubl-bpmn-id': i}, **({'ubl-event': s['kind']} if s['kind'] in ('start', 'end') else {}),
             **({'ubl-gateway': 'exclusive'} if s['kind'] == 'gateway' else {}))


def attach(pt):
    """the shape a flow's end point lies on, and where on it (fractions)"""
    best = None
    for i, s in shapes.items():
        if s['kind'] == 'pool':
            continue
        fx, fy = (pt[0] - s['x']) / s['w'], (pt[1] - s['y']) / s['h']
        slack = 2.5
        if -slack / s['w'] <= fx <= 1 + slack / s['w'] and -slack / s['h'] <= fy <= 1 + slack / s['h']:
            on_edge = min(abs(fx), abs(1 - fx)) * s['w'] <= slack or min(abs(fy), abs(1 - fy)) * s['h'] <= slack
            if s['kind'] in ('gateway', 'start', 'end'):
                on_edge = True
            if on_edge:
                best = (i, min(1, max(0, fx)), min(1, max(0, fy)))
    return best


SEQ = 'html=1;rounded=0;endArrow=block;endFill=1;endSize=8;' + LINE
MSG = 'html=1;rounded=0;dashed=1;dashPattern=8 8;startArrow=oval;startFill=0;startSize=8;endArrow=block;endFill=0;endSize=8;' + LINE
for i, pts in flows.items():
    a, b = attach(pts[0]), attach(pts[-1])
    sa, sb = shapes[a[0]], shapes[b[0]]
    message = i.startswith('MessageFlow')
    extra = {'ubl-bpmn-id': i, 'ubl-flow': 'message' if message else 'sequence'}
    # a label beside it: its text
    if i in labels:
        extra['ubl-name'] = ' '.join(labels[i][3])
    parent = '1' if message or sa['pool'] != sb['pool'] else ids[sa['pool']]
    ox, oy = (OX, OY) if parent == '1' else (shapes[sa['pool']]['x'], shapes[sa['pool']]['y'])
    st = (MSG if message else SEQ) + 'edgeStyle=orthogonalEdgeStyle;' + \
        'exitX=%s;exitY=%s;exitDx=0;exitDy=0;entryX=%s;entryY=%s;entryDx=0;entryDy=0;' % (
            round(a[1], 3), round(a[2], 3), round(b[1], 3), round(b[2], 3))
    kind = 'message-flow' if message else 'flow'
    ident = '%s-%s-to-%s' % (kind, ids[a[0]], ids[b[0]])
    f.edge(ident, kind, '', st, [(x - ox, y - oy) for x, y in pts], parent=parent, source=ids[a[0]], target=ids[b[0]],
           via=[(x - ox, y - oy) for x, y in pts[1:-1]], **extra)
    flows[i] = ident
for i, (o, w, h, lines) in labels.items():
    f.vertex('text-' + flows[i], 'text', '<br>'.join(lines), 'text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;',
             o[0] - OX - 10, o[1] - OY, w + 20, h, **{'ubl-for': flows[i]})
print(f.write())
