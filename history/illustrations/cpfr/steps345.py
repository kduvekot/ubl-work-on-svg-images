"""UBL-2.2-CPFR-Steps3-4-5 as a draw.io illustration: the pilot of the three CPFR step figures.

    python3 history/illustrations/cpfr/steps345.py        writes diagrams/UBL-2.2-CPFR-Steps3-4-5/

Every shape measured on the UBL 2.2 PNG (art/UBL-2.2-CPFR-Steps3-4-5.png, 1712 x 1976), given here in
its px and divided by the PNG's px per the drawing's (S): the drawing is the figure at the size of its
source (the iSURF D6.1.1 figure, 613 x 708, framed), the PNG that times 2.7733 with a 6 px frame round it.
The pictures are the parts in illustrations/parts/ (cpfr-*), placed where they match the PNG best
(parts_fit.py).
"""
import base64, html, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PARTS = os.path.join(ROOT, 'illustrations', 'parts')
N = 'UBL-2.2-CPFR-Steps3-4-5'
PW, PH = 1712, 1976
S = 1700 / 613                     # the PNG's px per the drawing's (its frame aside, 6 px)
W, H = PW / S, PH / S
FONT = 'fontFamily=Helvetica;'
cells = []; n = [0]
def nid():
    n[0] += 1; return 'c%d' % n[0]
f = lambda v: '%.2f' % (v / S)
def geo(x0, y0, x1, y1):
    return '<mxGeometry x="%s" y="%s" width="%s" height="%s" as="geometry"/>' % (f(x0), f(y0), f(x1 - x0), f(y1 - y0))
def vertex(style, box, label='', obj=None):
    i = nid(); lab = html.escape(label, quote=True)
    if obj:
        attrs = ' '.join('%s="%s"' % (k, html.escape(v, quote=True)) for k, v in obj.items())
        cells.append('<object id="%s" label="%s" %s><mxCell style="%s" vertex="1" parent="1">%s</mxCell></object>' % (i, lab, attrs, style, geo(*box)))
    else:
        cells.append('<mxCell id="%s" value="%s" style="%s" vertex="1" parent="1">%s</mxCell>' % (i, lab, style, geo(*box)))
    return i
def edge(pts, style='endArrow=block;endFill=1;endSize=4;html=1;rounded=0;strokeWidth=1;'):
    i = nid(); p = ''.join('<mxPoint x="%s" y="%s"/>' % (f(x), f(y)) for x, y in pts[1:-1])
    cells.append('<mxCell id="%s" value="" style="%s" edge="1" parent="1"><mxGeometry relative="1" as="geometry">'
                 '<mxPoint x="%s" y="%s" as="sourcePoint"/><mxPoint x="%s" y="%s" as="targetPoint"/>%s</mxGeometry></mxCell>'
                 % (i, style, f(pts[0][0]), f(pts[0][1]), f(pts[-1][0]), f(pts[-1][1]), ('<Array as="points">%s</Array>' % p) if p else ''))
def picture(part, box, flip=False):
    b64 = base64.b64encode(open(os.path.join(PARTS, part + '.svg'), 'rb').read()).decode()
    vertex('shape=image;imageAspect=0;verticalLabelPosition=bottom;%simage=data:image/svg+xml,%s;' % ('flipH=1;' if flip else '', b64),
           box, obj={'ubl-part': part})
def text(label, box, size, color='#000000', align='center', extra=''):
    vertex('text;html=1;whiteSpace=nowrap;overflow=visible;align=%s;verticalAlign=middle;spacing=0;fontSize=%s;fontColor=%s;%s%s'
           % (align, size, color, FONT, extra), box, label)

# the frame: the drawing's origin is its outer corner (6 px of the PNG)
t = 6 / S
cells.append('<object id="frame" label="" ubl-kind="illustration" ubl-png-scale="%.4f"><mxCell style="rounded=0;whiteSpace=wrap;html=1;'
             'fillColor=none;strokeColor=#000000;strokeWidth=%.2f;" vertex="1" parent="1"><mxGeometry x="%.2f" y="%.2f" width="%.2f" '
             'height="%.2f" as="geometry"/></mxCell></object>' % (S, t, t / 2, t / 2, W - t, H - t))
# the steps: grey panels, rounded; step 6 dashed
panel = 'rounded=1;absoluteArcSize=1;arcSize=22;whiteSpace=wrap;html=1;fillColor=#e0e0e0;strokeColor=#000000;strokeWidth=1;'
vertex(panel, (41.5, 93, 778, 1927.5))
vertex(panel, (920.5, 97.5, 1665, 1247.5))
vertex(panel + 'dashed=1;dashPattern=7 4;', (925.5, 1311, 1669.5, 1458), 'CPFR Step 6', )
cells[-1] = cells[-1].replace('strokeWidth=1;', 'strokeWidth=1;fontSize=15.3;fontColor=#505050;' + FONT)
text('CPFR Step 3', (520, 112, 755, 150), 12.7, '#505050', 'right')
text('CPFR Step 4-5', (1380, 126, 1652, 164), 12.7, '#505050', 'right')
# the big arrows: the documents passed, between the parties (left, right, both)
A = 'html=1;whiteSpace=wrap;fillColor=#e4e4e4;strokeColor=#000000;strokeWidth=1;fontSize=13;fontColor=#404040;spacingLeft=%.1f;' % (17 / S) + FONT
def arrow(label, x0, x1, y0, y1, body, head, direction):
    w = x1 - x0
    st = A + ('shape=singleArrow;direction=%s;arrowWidth=%.3f;arrowSize=%.3f;' % (direction, body / (y1 - y0), head / w)
              if direction else 'shape=doubleArrow;arrowWidth=%.3f;arrowSize=%.3f;' % (body / (y1 - y0), head / w))
    vertex(st, (x0, y0, x1, y1), label)
arrow('Product Activity (POS Data)', 74, 726.5, 265, 392.5, 42, 64, 'west')
arrow('Product Activity (DC Data)', 74, 726.5, 566, 693.5, 42, 64, 'west')
arrow('Sales Forecast', 74, 726.5, 882, 1009.5, 42, 64, 'east')
arrow('Sales Forecast Revision', 74, 726.5, 1213, 1340.5, 42, 64, 'west')
arrow('Sales Forecast Revision', 74, 726.5, 1505, 1632.5, 42, 64, 'east')
arrow('Wait for Exception Notification', 964, 1615, 325, 465, 48, 70, None)
cells[-1] = cells[-1].replace('fillColor=#e4e4e4', 'fillColor=#eaeaea').replace('fontSize=13', 'fontSize=12.8').replace('spacingLeft', 'spacingRight')
# the documents, the exception, the people resolving it
fit = json.load(open(os.path.join(HERE, 'parts_fit.json')))
for k in ('doc1', 'doc2', 'doc3', 'doc4', 'doc5'):
    x, y, w, h = fit[k]; picture('cpfr-document', (x, y, x + w, y + h))
x, y, w, h = fit['clipboard']; picture('cpfr-exception', (x, y, x + w, y + h))
vertex('rounded=0;whiteSpace=wrap;html=1;fillColor=#acacac;strokeColor=#000000;strokeWidth=1;dashed=1;dashPattern=8 3.5 1.5 3.5;'
       'fontSize=15.25;' + FONT, (1082.5, 860, 1504.5, 1012), 'Resolve Exception')
x, y, w, h = fit['desk-left']; picture('cpfr-person-at-desk', (x, y, x + w, y + h))
x, y, w, h = fit['desk-right']; picture('cpfr-person-at-desk', (x, y, x + w, y + h), flip=True)
# the flows, over the arrows and the documents
# (a document's top and bottom slope: they meet the flow at x 410 16 and 113 px below its top-left corner)
for y0, y1 in ((255, 455), (552, 775), (872, 1102), (1199, 1394), (1491, 1664)):
    edge([(410, y0), (410, y1)])
edge([(532, 1741.5), (678.5, 1741.5), (678.5, 1160), (443, 1160)])
edge([(410, 1816), (410, 1863), (872.5, 1863), (872.5, 48), (1293, 48), (1293, 96.5)])
edge([(1293, 360), (1293, 508)])
edge([(1293, 660), (1293, 858)])
edge([(1168, 585), (946, 585), (946, 1190.5), (1298, 1190.5), (1298, 1309.5)])
# the decisions
D = 'rhombus;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#000000;strokeWidth=1;fontSize=10.2;spacingBottom=%.1f;' % (10 / S) + FONT
vertex(D, (287.5, 1665, 532, 1816), 'Sales Forecast<br>Accepted?')
vertex(D, (1168.5, 509.5, 1417.5, 660), 'Exception<br>Received?')
# the guards
G = 'labelBackgroundColor=#ffffff;'
for lab, cx, cy in (('No', 678, 1401), ('Yes', 871.5, 976), ('Yes', 1293, 757), ('No', 945.5, 1011.5)):
    text(lab, (cx - 30, cy - 18, cx + 30, cy + 18), 10, '#000000', 'center', G)
body = ''.join(cells)
xml = ('<mxfile host="UBL-TC" agent="UBL artwork pipeline, the CPFR step illustrations (history/illustrations/cpfr)" type="device">'
       '<diagram id="%s" name="%s"><mxGraphModel grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" '
       'page="1" pageScale="1" pageWidth="%d" pageHeight="%d" math="0" shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
       '%s</root></mxGraphModel></diagram></mxfile>' % (N, N, round(W), round(H), body))
os.makedirs(os.path.join(ROOT, 'diagrams', N), exist_ok=True)
open(os.path.join(ROOT, 'diagrams', N, N + '.drawio'), 'w', encoding='utf-8').write(xml)
print(N, '%.1f x %.1f' % (W, H), len(cells), 'cells')
