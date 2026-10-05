"""What the CPFR step drawings share: a drawing measured on its UBL 2.2 PNG, written as a draw.io illustration.

Every shape is given in the PNG's px and divided by S, the PNG's px per the drawing's: the drawing is the
figure at the size of its source (the iSURF D6.1.1 figure, framed), the PNG that times S with a frame of F px
round it. The pictures are the parts in illustrations/parts/ (cpfr-*), where parts_fit.py found them.
"""
import base64, html, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PARTS = os.path.join(ROOT, 'illustrations', 'parts')
FONT = 'fontFamily=Helvetica;'
GREY_TEXT = '#505050'


class Drawing:
    def __init__(self, name, png_size, frame, source_width):
        self.name, (self.PW, self.PH), self.F = name, png_size, frame
        self.S = (self.PW - 2 * frame) / source_width
        self.cells, self.n = [], 0
        self.fit = json.load(open(os.path.join(HERE, 'parts_fit.json')))[name]
        t = frame / self.S
        self.cells.append('<object id="frame" label="" ubl-kind="illustration" ubl-png-scale="%.4f"><mxCell style="rounded=0;'
                          'whiteSpace=wrap;html=1;fillColor=none;strokeColor=#000000;strokeWidth=%.2f;" vertex="1" parent="1">'
                          '<mxGeometry x="%.2f" y="%.2f" width="%.2f" height="%.2f" as="geometry"/></mxCell></object>'
                          % (self.S, t, t / 2, t / 2, self.PW / self.S - t, self.PH / self.S - t))

    def f(self, v):
        return '%.2f' % (v / self.S)

    def nid(self):
        self.n += 1
        return 'c%d' % self.n

    def geo(self, x0, y0, x1, y1):
        return '<mxGeometry x="%s" y="%s" width="%s" height="%s" as="geometry"/>' % (self.f(x0), self.f(y0), self.f(x1 - x0), self.f(y1 - y0))

    def vertex(self, style, box, label='', obj=None):
        i, lab = self.nid(), html.escape(label, quote=True)
        if obj:
            attrs = ' '.join('%s="%s"' % (k, html.escape(v, quote=True)) for k, v in obj.items())
            self.cells.append('<object id="%s" label="%s" %s><mxCell style="%s" vertex="1" parent="1">%s</mxCell></object>' % (i, lab, attrs, style, self.geo(*box)))
        else:
            self.cells.append('<mxCell id="%s" value="%s" style="%s" vertex="1" parent="1">%s</mxCell>' % (i, lab, style, self.geo(*box)))
        return i

    def edge(self, pts, style='endArrow=block;endFill=1;endSize=4;html=1;rounded=0;strokeWidth=1;'):
        i, f = self.nid(), self.f
        p = ''.join('<mxPoint x="%s" y="%s"/>' % (f(x), f(y)) for x, y in pts[1:-1])
        self.cells.append('<mxCell id="%s" value="" style="%s" edge="1" parent="1"><mxGeometry relative="1" as="geometry">'
                          '<mxPoint x="%s" y="%s" as="sourcePoint"/><mxPoint x="%s" y="%s" as="targetPoint"/>%s</mxGeometry></mxCell>'
                          % (i, style, f(pts[0][0]), f(pts[0][1]), f(pts[-1][0]), f(pts[-1][1]), ('<Array as="points">%s</Array>' % p) if p else ''))

    def picture(self, part, key, flip=False):
        x, y, w, h = self.fit[key]
        b64 = base64.b64encode(open(os.path.join(PARTS, part + '.svg'), 'rb').read()).decode()
        self.vertex('shape=image;imageAspect=0;verticalLabelPosition=bottom;%simage=data:image/svg+xml,%s;' % ('flipH=1;' if flip else '', b64),
                    (x, y, x + w, y + h), obj={'ubl-part': part})

    def text(self, label, box, size, color='#000000', align='center', extra=''):
        self.vertex('text;html=1;whiteSpace=nowrap;overflow=visible;align=%s;verticalAlign=middle;spacing=0;fontSize=%s;fontColor=%s;%s%s'
                    % (align, size, color, FONT, extra), box, label)

    # the figures' own shapes
    def panel(self, box, dashed=False, label='', size=15.3):
        st = 'rounded=1;absoluteArcSize=1;arcSize=22;whiteSpace=wrap;html=1;fillColor=#e0e0e0;strokeColor=#000000;strokeWidth=1;'
        if dashed:
            st += 'dashed=1;dashPattern=7 4;fontSize=%s;fontColor=%s;%s' % (size, GREY_TEXT, FONT)
        self.vertex(st, box, label)

    def title(self, label, box, size=12.7):
        self.text(label, box, size, GREY_TEXT, 'right')

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
        self.vertex(st, (x0, y0, x1, y1), label)

    def decision(self, label, box, size=10.2, lift=10):
        self.vertex('rhombus;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#000000;strokeWidth=1;fontSize=%s;spacingBottom=%.1f;%s'
                    % (size, lift / self.S, FONT), box, label)

    def resolve(self, box, size=15.25):
        """the Resolve Exception box: over the people at their desks, see-through, as the PNG has it"""
        self.vertex('rounded=0;whiteSpace=wrap;html=1;fillColor=#7f7f7f;fillOpacity=55;strokeColor=#000000;strokeWidth=1;dashed=1;'
                    'dashPattern=8 3.5 1.5 3.5;fontSize=%s;%s' % (size, FONT), box, 'Resolve Exception')

    def guard(self, label, cx, cy, size=10):
        self.text(label, (cx - 30, cy - 18, cx + 30, cy + 18), size, '#000000', 'center', 'labelBackgroundColor=#ffffff;')

    def write(self):
        W, H = self.PW / self.S, self.PH / self.S
        xml = ('<mxfile host="UBL-TC" agent="UBL artwork pipeline, the CPFR step illustrations (history/illustrations/cpfr)" type="device">'
               '<diagram id="%s" name="%s"><mxGraphModel grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" '
               'page="1" pageScale="1" pageWidth="%d" pageHeight="%d" math="0" shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
               '%s</root></mxGraphModel></diagram></mxfile>' % (self.name, self.name, round(W), round(H), ''.join(self.cells)))
        d = os.path.join(ROOT, 'diagrams', self.name)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, self.name + '.drawio'), 'w', encoding='utf-8').write(xml)
        print(self.name, '%.1f x %.1f' % (W, H), len(self.cells), 'cells')
