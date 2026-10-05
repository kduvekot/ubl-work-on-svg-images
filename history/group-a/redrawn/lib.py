"""A small writer for the Group A drawings (BPMN and phase-map figures): cells with the
model's id and kind, written as draw.io's editor writes them (tools/drawio_format.py)."""
import os, sys
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import drawio_format  # noqa: E402


def q(v):
    return escape(str(v), {'"': '&quot;'})


def n(v):
    """a number, whole where it is whole"""
    v = round(float(v), 2)
    return str(int(v)) if v == int(v) else str(v)


class Fig:
    def __init__(self, name, width, height, agent):
        self.name, self.w, self.h, self.agent = name, width, height, agent
        self.cells = []

    def _obj(self, ident, kind, label, extra, inner):
        attrs = ' '.join('%s="%s"' % (k, q(v)) for k, v in [('label', label), ('ubl-kind', kind)] + list(extra.items()))
        self.cells.append('<object %s id="%s">%s</object>' % (attrs, q(ident), inner))

    def vertex(self, ident, kind, label, style, x, y, w, h, parent='1', **extra):
        self._obj(ident, kind, label, extra,
                  '<mxCell parent="%s" style="%s" vertex="1"><mxGeometry x="%s" y="%s" width="%s" height="%s" as="geometry"/></mxCell>'
                  % (q(parent), q(style), n(x), n(y), n(w), n(h)))

    def edge(self, ident, kind, label, style, points, parent='1', source=None, target=None, via=(), **extra):
        """points: [(x, y), ...] first = sourcePoint, last = targetPoint, the others the waypoints
        (ignored where an end is attached: then `via` are the waypoints)"""
        ends = ''
        if source or target:
            pts = ''.join('<mxPoint x="%s" y="%s"/>' % (n(x), n(y)) for x, y in via)
            geo = '<Array as="points">%s</Array>' % pts if pts else ''
            if not source:
                geo += '<mxPoint x="%s" y="%s" as="sourcePoint"/>' % (n(points[0][0]), n(points[0][1]))
            if not target:
                geo += '<mxPoint x="%s" y="%s" as="targetPoint"/>' % (n(points[-1][0]), n(points[-1][1]))
            ends = (' source="%s"' % q(source) if source else '') + (' target="%s"' % q(target) if target else '')
        else:
            a, b = points[0], points[-1]
            geo = '<mxPoint x="%s" y="%s" as="sourcePoint"/><mxPoint x="%s" y="%s" as="targetPoint"/>' % (n(a[0]), n(a[1]), n(b[0]), n(b[1]))
            mid = points[1:-1]
            if mid:
                geo += '<Array as="points">%s</Array>' % ''.join('<mxPoint x="%s" y="%s"/>' % (n(x), n(y)) for x, y in mid)
        self._obj(ident, kind, label, extra,
                  '<mxCell parent="%s" style="%s" edge="1"%s><mxGeometry relative="1" as="geometry">%s</mxGeometry></mxCell>'
                  % (q(parent), q(style), ends, geo))

    def text(self):
        body = ''.join(self.cells)
        return ('<mxfile host="UBL-TC" agent="%s"><diagram id="%s" name="%s"><mxGraphModel grid="0" gridSize="10" guides="1" '
                'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="%s" pageHeight="%s" math="0" shadow="0">'
                '<root><mxCell id="0"/><mxCell id="1" parent="0"/>%s</root></mxGraphModel></diagram></mxfile>'
                % (q(self.agent), q(self.name), q(self.name), n(self.w), n(self.h), body))

    def write(self):
        # beside the scripts: these drawings are not the figures' sources (history/group-a/README.md)
        path = os.path.join(HERE, self.name + '.drawio')
        open(path, 'w', encoding='utf-8').write(drawio_format.format_text(self.text()))
        return path
