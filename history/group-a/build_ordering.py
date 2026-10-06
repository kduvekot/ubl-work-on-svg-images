"""UBL-2.3-OrderingProcess as a BPMN diagram in draw.io: the figure's source since 2026-10-06.

The figure was made in bpmn.io; its BPMN 2.0 XML (UBL-2.3-OrderingProcess.bpmn) is lost, and the UBL
repository has only the SVG bpmn-js exported (sources/). That SVG keeps every element's BPMN id and
kind, its place and size, and every bend of every flow, but not which elements a flow joins. This
reads the SVG and draws the same collaboration with draw.io's BPMN shapes, styled as draw.io's BPMN
palette makes them (Sidebar-BPMN.js of the pinned release, 32.0.2), and links it as a BPMN model does:

- every element has its BPMN id as its id, and its BPMN type (ubl-bpmn-type);
- every task, gateway and event is in its pool, the participant whose process it belongs to;
- every flow is attached to the element it leaves and the one it enters (BPMN's sourceRef and
  targetRef): each end is where the SVG's line meets an element's outline, and exactly one element
  must be there, or the script stops; a sequence flow stays in its pool, a message flow joins two;
- a flow's name is its own label, where the SVG has it.

Places, sizes and bends are the SVG's (its viewBox origin is the drawing's), and so are the line weights
(2 px; a message flow 1.5 px, dashed 10 12) and the text sizes (12 px; a flow's name 11 px), so the
drawing looks as the figure. Where the palette differs it is said below. Prints the links it made.

It writes the figure's source, diagrams/UBL-2.3-OrderingProcess/UBL-2.3-OrderingProcess.drawio, as the
Group B and C scripts write theirs. Since then the drawing is the source and is edited in draw.io: this
is how it was made, and need not be run again (it would overwrite an edit)."""
import math, os, re, sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(HERE, 'redrawn'))
from lib import Fig as _Fig  # noqa: E402
import drawio_format  # noqa: E402


class Fig(_Fig):
    def write(self):
        d = os.path.join(ROOT, 'diagrams', self.name)
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, self.name + '.drawio')
        open(path, 'w', encoding='utf-8').write(drawio_format.format_text(self.text()))
        return path


NS = '{http://www.w3.org/2000/svg}'
NAME = 'UBL-2.3-OrderingProcess'
svg = ET.parse(os.path.join(HERE, 'sources', 'UBL-2.3-OrderingProcess.svg')).getroot()
OX, OY = 150, 75      # the SVG's viewBox: its origin is the drawing's

shapes, flows, labels = {}, {}, {}


def lines_of(g):
    return [''.join(t.itertext()).strip() for t in g.iter(NS + 'tspan')]


def walk(e, off=(0, 0)):
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
                flows[ident] = [tuple(float(v) for v in p.split(',')) for p in re.findall(r'[\d.]+,[\d.]+', d)]
            elif ident.endswith('_label'):
                hit = g.find(NS + 'rect[@class="djs-hit"]')
                labels[ident[:-6]] = (o, float(hit.get('width')), float(hit.get('height')), lines_of(g))
            else:
                r = vis.find(NS + 'rect')
                kind = ident.split('_')[0]
                if kind == 'Participant':
                    shapes[ident] = dict(kind=kind, x=o[0], y=o[1], w=float(r.get('width')), h=float(r.get('height')), text=lines_of(vis))
                else:
                    size = {'Task': (100, 80), 'ExclusiveGateway': (50, 50), 'StartEvent': (36, 36), 'EndEvent': (36, 36)}
                    if kind not in size:
                        raise SystemExit('%s: a BPMN element this script does not draw' % ident)
                    w, h = size[kind]
                    shapes[ident] = dict(kind=kind, x=o[0], y=o[1], w=w, h=h, text=lines_of(vis))
                    # an end event here is a terminate end event: bpmn-js draws a filled circle inside the thick one
                    if kind == 'EndEvent' and not any(c.get('r') == '10' and 'fill: black' in (c.get('style') or '')
                                                      for c in vis.iter(NS + 'circle')):
                        raise SystemExit('%s: not a terminate end event' % ident)
            for ch in g:
                if ch.get('class') == 'djs-children':
                    walk(ch, o)
        else:
            walk(g, off)


walk(svg)

# The SVG does not nest an element in its pool (all are siblings): its pool is the one it lies in,
# exactly one, and the last pool before it in the SVG (as bpmn-js writes a pool and then its contents).
last = None
for i, s in shapes.items():
    if s['kind'] == 'Participant':
        last = i
        continue
    pools = [p for p, q in shapes.items() if q['kind'] == 'Participant' and q['x'] <= s['x'] and s['x'] + s['w'] <= q['x'] + q['w']
             and q['y'] <= s['y'] and s['y'] + s['h'] <= q['y'] + q['h']]
    if pools != [last]:
        raise SystemExit('%s: lies in %s, follows %s in the SVG' % (i, pools, last))
    s['pool'] = last

# draw.io's BPMN palette (Sidebar-BPMN.js, v32.0.2), with the figure's line weights added. The pool is
# the palette's plain swimlane (its pools are made for lanes, which this figure has none of), with
# bpmn-js's 30 px title band and its name not bold, as in the figure.
TASK_PTS = 'points=[[0.25,0,0],[0.5,0,0],[0.75,0,0],[1,0.25,0],[1,0.5,0],[1,0.75,0],[0.75,1,0],[0.5,1,0],[0.25,1,0],[0,0.75,0],[0,0.5,0],[0,0.25,0]];'
EVENT_PTS = 'points=[[0.145,0.145,0],[0.5,0,0],[0.855,0.145,0],[1,0.5,0],[0.855,0.855,0],[0.5,1,0],[0.145,0.855,0],[0,0.5,0]];'
GATE_PTS = 'points=[[0.25,0.25,0],[0.5,0,0],[0.75,0.25,0],[1,0.5,0],[0.75,0.75,0],[0.5,1,0],[0.25,0.75,0],[0,0.5,0]];'
STYLE = {
    'Participant': 'swimlane;startSize=30;horizontal=0;html=1;whiteSpace=wrap;fontStyle=0;strokeWidth=2;',
    'Task': TASK_PTS + 'shape=mxgraph.bpmn.task2;whiteSpace=wrap;rectStyle=rounded;size=10;html=1;container=1;expand=0;'
            'collapsible=0;taskMarker=abstract;strokeWidth=2;',
    'ExclusiveGateway': GATE_PTS + 'shape=mxgraph.bpmn.gateway2;html=1;verticalLabelPosition=bottom;labelBackgroundColor=#ffffff;'
                        'verticalAlign=top;align=center;perimeter=rhombusPerimeter;outlineConnect=0;outline=none;symbol=none;'
                        'gwType=exclusive;strokeWidth=2;',
    'StartEvent': EVENT_PTS + 'shape=mxgraph.bpmn.event;html=1;verticalLabelPosition=bottom;labelBackgroundColor=#ffffff;'
                  'verticalAlign=top;align=center;perimeter=ellipsePerimeter;outlineConnect=0;aspect=fixed;outline=standard;'
                  'symbol=general;strokeWidth=2;',
    'EndEvent': EVENT_PTS + 'shape=mxgraph.bpmn.event;html=1;verticalLabelPosition=bottom;labelBackgroundColor=#ffffff;'
                'verticalAlign=top;align=center;perimeter=ellipsePerimeter;outlineConnect=0;aspect=fixed;outline=end;'
                'symbol=terminate;strokeWidth=2;',
}
# Flows: the palette's, but orthogonal (its elbow style keeps one bend only, the figure's flows have
# up to four), and a message flow's head open, as BPMN and the figure have it (the palette fills it).
SEQUENCE = 'edgeStyle=orthogonalEdgeStyle;fontSize=11;html=1;endArrow=blockThin;endFill=1;rounded=0;strokeWidth=2;'
MESSAGE = 'edgeStyle=orthogonalEdgeStyle;fontSize=11;html=1;dashed=1;dashPattern=10 12;fixDash=1;endArrow=blockThin;endFill=0;' \
          'startArrow=oval;startFill=0;endSize=6;startSize=4;rounded=0;strokeWidth=1.5;'
BPMN_TYPE = {'Participant': 'participant', 'Task': 'task', 'ExclusiveGateway': 'exclusiveGateway', 'StartEvent': 'startEvent',
             'EndEvent': 'endEvent', 'SequenceFlow': 'sequenceFlow', 'MessageFlow': 'messageFlow'}
KIND = {'Participant': 'pool', 'Task': 'task', 'ExclusiveGateway': 'gateway', 'StartEvent': 'event', 'EndEvent': 'event',
        'SequenceFlow': 'flow', 'MessageFlow': 'message-flow'}

f = Fig(NAME, 1231, 818, 'UBL artwork, Group A (history/group-a/build_ordering.py)')
for i, s in shapes.items():
    if s['kind'] == 'Participant':
        f.vertex(i, KIND['Participant'], ' '.join(s['text']), STYLE['Participant'], s['x'] - OX, s['y'] - OY, s['w'], s['h'],
                 **{'ubl-bpmn-type': 'participant', 'ubl-notation': 'bpmn'})
for i, s in shapes.items():
    if s['kind'] == 'Participant':
        continue
    p = shapes[s['pool']]
    extra = {'ubl-bpmn-type': BPMN_TYPE[s['kind']]}
    if s['kind'] == 'EndEvent':
        extra['ubl-bpmn-event-definition'] = 'terminateEventDefinition'
    f.vertex(i, KIND[s['kind']], '<br>'.join(s['text']), STYLE[s['kind']], s['x'] - p['x'], s['y'] - p['y'], s['w'], s['h'],
             parent=s['pool'], **extra)


def on_outline(pt, s, slack=2.5):
    """does the point lie on the element's outline?"""
    cx, cy, rx, ry = s['x'] + s['w'] / 2, s['y'] + s['h'] / 2, s['w'] / 2, s['h'] / 2
    dx, dy = pt[0] - cx, pt[1] - cy
    if s['kind'] in ('StartEvent', 'EndEvent'):
        return abs(math.hypot(dx, dy) - rx) <= slack
    if s['kind'] == 'ExclusiveGateway':
        return abs(abs(dx) + abs(dy) - rx) <= slack * math.sqrt(2)
    inside = abs(dx) <= rx + slack and abs(dy) <= ry + slack
    return inside and min(rx - abs(dx), ry - abs(dy)) <= slack


def attach(flow, pt):
    """the one element the flow's end lies on, and where on it (fractions of its box)"""
    hits = [i for i, s in shapes.items() if s['kind'] != 'Participant' and on_outline(pt, s)]
    if len(hits) != 1:
        raise SystemExit('%s: its end at %s lies on %s, not on exactly one element' % (flow, pt, hits or 'none'))
    s = shapes[hits[0]]
    return hits[0], min(1, max(0, (pt[0] - s['x']) / s['w'])), min(1, max(0, (pt[1] - s['y']) / s['h']))


def middle(pts):
    """the point half-way along the line, where draw.io puts a flow's label before its offset"""
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    left = sum(seg) / 2
    for (a, b), l in zip(zip(pts, pts[1:]), seg):
        if left <= l:
            t = left / l if l else 0
            return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        left -= l
    return pts[-1]


links = []
for i, pts in flows.items():
    kind = i.split('_')[0]
    (a, ax, ay), (b, bx, by) = attach(i, pts[0]), attach(i, pts[-1])
    pa, pb = shapes[a]['pool'], shapes[b]['pool']
    if kind == 'SequenceFlow' and pa != pb or kind == 'MessageFlow' and pa == pb:
        raise SystemExit('%s: a %s from %s (%s) to %s (%s) breaks BPMN' % (i, kind, a, pa, b, pb))
    parent = pa if kind == 'SequenceFlow' else '1'
    ox, oy = (shapes[pa]['x'], shapes[pa]['y']) if parent != '1' else (OX, OY)
    style = (SEQUENCE if kind == 'SequenceFlow' else MESSAGE) + \
        'exitX=%s;exitY=%s;exitDx=0;exitDy=0;entryX=%s;entryY=%s;entryDx=0;entryDy=0;' % (
            round(ax, 3), round(ay, 3), round(bx, 3), round(by, 3))
    name, offset = '', None
    if i in labels:
        (lx, ly), lw, lh, lines = labels[i]
        name = '<br>'.join(lines)
        mx, my = middle(pts)
        offset = (lx + lw / 2 - mx, ly + lh / 2 - my)
    f.edge(i, KIND[kind], name, style, [(x - ox, y - oy) for x, y in pts], parent=parent, source=a, target=b,
           via=[(x - ox, y - oy) for x, y in pts[1:-1]], offset=offset, **{'ubl-bpmn-type': BPMN_TYPE[kind]})
    links.append((i, a, b, ' '.join(labels[i][3]) if i in labels else ''))


def said(e):
    s = shapes[e]
    return '%s "%s"' % (e, ' '.join(s['text'])) if s['text'] else e


for i, a, b, name in links:
    print('%-26s %s -> %s%s' % (i, said(a), said(b), '  [%s]' % name if name else ''))
print('%d elements, %d flows: %s' % (len(shapes), len(links), f.write()))
