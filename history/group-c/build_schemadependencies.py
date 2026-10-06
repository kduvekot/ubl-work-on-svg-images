"""UBL-2.2-SchemaDependencies: the dependency of UBL's schemas on one another. Boxes for the document schema (the
apex construct, e.g. Invoice) and the common library's aggregate, basic and data type schemas, for the signature
and the customization extension schemas, and for the foreign ones (W3C XML Digital Signature, XAdES), with
include (dashed arrow), import (solid arrow) and replace (hollow dotted block arrow) between them; the row
titles at the left (italic) say the kind of construct, the legend at the bottom says the arrows. The grey boxes
(qdt, udt, ccts-cct) and the dashed "Core Component Parameters" box are the data type constructs and the
documentation namespace; the two dashed outlines at the right and bottom hold the customization replacement schemas.
Drawn from the UBL repository's art/<figure>.png (3425 x 1957, RGBA: grey 230 in the grey boxes, otherwise black
and white). Scale S = 3425 / 778 = 1/4.4023 (the page is then a whole 778 px wide, which keeps the export's page rounding off
the picture): the 53 px text (capital height 38) is draw.io's 12 px, the 6.5 px box lines 1.5, the 3 px arrows 0.7,
the 10 px frame 2.3, the legend's words (42 px) 9.6 px. draw.io multiplies a dash pattern by the stroke width, so
the patterns are given in stroke widths (D() and the outline's). Where draw.io has no shape the PNG's own is built here from
draw.io's: the replace arrows are open dotted polylines round the block arrow's outline (draw.io's flexArrow closes its tail), the dashed L-shaped outline a closed dashed polyline, the
legend's samples sit between invisible 1 px anchors (kind 'anchor'), and the plain lines between a box and the
next (no arrowhead) are edges of kind 'line'."""
from lib_c import Figure, n

S = 3425 / 778          # 4.4023 PNG px per drawing px
NAME = 'UBL-2.2-SchemaDependencies'
f = Figure(NAME, 3425, 1957, S, __file__, grey=True)
f.frame(10)
r = f.r

# ---- boxes: outer edges in PNG px (stroke 6.5)
BS = 6.5
boxes = dict(
    doc=(743, 51, 1459, 264), cac=(487, 386, 879, 682), ext=(1339, 386, 1749, 682), ecd1=(1925, 386, 2334, 682),
    sac=(2455, 386, 2865, 682), sig=(2446, 46, 2856, 341), xxx=(2959, 49, 3369, 344), xac=(2968, 390, 3378, 685),
    cbc=(697, 748, 1101, 1044), sbc=(2464, 748, 2873, 1044), xbc=(2977, 752, 3386, 1047),
    ds=(2343, 1210, 2922, 1361), xades=(2252, 1380, 2831, 1532), ecd2=(1925, 1597, 2334, 1892))
greys = dict(qdt=(505, 1181, 892, 1474), udt=(1006, 1343, 1393, 1573), ccts=(1019, 1672, 1403, 1896))
for k, b in boxes.items():
    f.box(k, *b, stroke=BS)
for k, b in greys.items():
    f.box(k, *b, stroke=BS, fill='grey')
f.box('core', 517, 1632, 901, 1903, stroke=7, fill='grey', dashed=(37 * S / 7, 13 * S / 7))

# ---- the dashed outline round the customization replacement schemas (right) and the extension content
# datatype (bottom): one L-shaped polygon, 6.5 px, dashes 13 and 20.5
OL = 6.5
pts = [(2941, 1574), (2941, 33), (3398, 33), (3398, 1917), (1904, 1917), (1904, 1574), (2941, 1574)]
f.vertex('a-outline-0', 'anchor', '', 'strokeColor=none;fillColor=none;', r(pts[0][0]), r(pts[0][1]), 0.01, 0.01)
f.edge('outline', 'line', '', 'html=1;rounded=0;endArrow=none;startArrow=none;dashed=1;dashPattern=%s %s;strokeWidth=%s;'
       % (n(13 / OL), n(20.5 / OL), n(OL / S)), [(r(x), r(y)) for x, y in pts], source='a-outline-0', target='a-outline-0',
       via=[(r(x), r(y)) for x, y in pts[1:-1]])

# ---- arrows
AS = 3          # the arrows' stroke in PNG px
HEADSIZE = 5.5     # draw.io's block head grows with the stroke: this one is 30 x 28 px in the PNG
HEAD = dict(head='block', size=HEADSIZE, stroke=AS)


def D(dash, gap):
    """a dash pattern in PNG px for f.flow, which divides by S: draw.io multiplies it by the stroke width"""
    return (dash * S / AS, gap * S / AS)


def flow(i, s, t, p0, p1, **kw):
    a = dict(HEAD)
    a.update(kw)
    f.flow(i, s, t, p0, p1, **a)


def line(i, s, t, p0, p1):
    f.flow(i, s, t, p0, p1, head='none', stroke=AS, kind='line')


flow('f-doc-cac', 'doc', 'cac', (826, 264), (689, 386))
flow('f-doc-cbc', 'doc', 'cbc', (1096, 264), (974, 748))
flow('f-doc-ext', 'doc', 'ext', (1368, 264), (1539, 386))
flow('f-cac-cbc', 'cac', 'cbc', (729, 682), (830, 748))
flow('f-ext-cbc', 'ext', 'cbc', (1456, 682), (1101, 781))
flow('f-ext-udt', 'ext', 'udt', (1541, 682), (1260, 1343))
flow('f-cbc-qdt', 'cbc', 'qdt', (876, 1044), (712, 1181))
flow('f-cbc-udt', 'cbc', 'udt', (1003, 1044), (1134, 1343))
flow('f-qdt-udt', 'qdt', 'udt', (892, 1324), (1006, 1457))
flow('f-udt-ccts', 'udt', 'ccts', (1208, 1573), (1208, 1672))
flow("f-ext-ecd1", "ext", "ecd1", (1749, 541), (1925, 541), dash=D(11, 7))
flow('f-ecd1-sig', 'ecd1', 'sig', (2126, 386), (2446, 223))
flow('f-sac-cbc', 'sac', 'cbc', (2487, 682), (1101, 957))
flow('f-sbc-qdt', 'sbc', 'qdt', (2464, 831), (892, 1203))
flow('f-sbc-udt', 'sbc', 'udt', (2464, 906), (1338, 1343))
flow('f-sig-sac', 'sig', 'sac', (2681, 341), (2683, 386))
line('l-sig-sac-1', 'sig', 'sac', (2605, 341), (2605, 386))
line('l-sig-sac-2', 'sig', 'sac', (2742, 341), (2742, 386))
line('l-sac-sbc', 'sac', 'sbc', (2605, 682), (2605, 748))
flow('f-sac-sbc', 'sac', 'sbc', (2742, 682), (2742, 748))
flow('f-sbc-ds', 'sbc', 'ds', (2605, 1044), (2605, 1210))
flow('f-ecd1-xades-1', 'ecd1', 'xades', (2275, 682), (2275, 1380))
flow('f-ecd1-xades-2', 'ecd1', 'xades', (2313, 682), (2313, 1380))
flow('f-xxx-xac', 'xxx', 'xac', (3127, 344), (3130, 390))
line('l-xxx-xac', 'xxx', 'xac', (3189, 344), (3189, 390))
flow('f-xac-xbc', 'xac', 'xbc', (3188, 685), (3188, 752))

# ---- legend samples and replace arrows. A replace arrow is a hollow dotted block arrow: draw.io's flexArrow closes
# its tail, the PNG's does not, so it is an open dotted polyline from one tail end round the head to the other, between
# two invisible 1 px anchors (kind 'anchor') at the tail ends; the legend's samples sit between anchors too.
def anchor(i, x, y):
    f.geo[i] = (x, y, x + 1, y + 1)
    f.turn[i] = False
    f.vertex(i, 'anchor', '', 'strokeColor=none;fillColor=none;', r(x), r(y), r(1), r(1))


def replace(i, p0, p1, via):
    anchor(i + '-a', *p0)
    anchor(i + '-b', *p1)
    f.flow(i, i + '-a', i + '-b', p0, p1, via=via, head='none', stroke=AS, dash=D(6, 9))


replace('f-replace', (2081, 1577), (2177, 1577), [(2081, 736), (2019, 736), (2128, 683), (2237, 736), (2177, 736)])
anchor('lg-a1', 1454, 1699); anchor('lg-b1', 1851, 1699)
anchor('lg-a2', 1454, 1772); anchor('lg-b2', 1851, 1772)
flow('f-legend-include', 'lg-a1', 'lg-b1', (1454, 1699), (1851, 1699), dash=D(6, 6))
flow('f-legend-import', 'lg-a2', 'lg-b2', (1454, 1772), (1851, 1772))
replace('f-legend-replace', (1843, 1818), (1843, 1884), [(1491, 1818), (1490, 1791), (1459, 1852), (1490, 1913), (1491, 1884)])

# ---- text
P = 64
CAP = dict(pitch=P, bold=True)
f.label('t-doc', ['Document Schema', 'e.g. Invoice, Order, etc.', '(document namespace)'], 73.4, cx=1098.5, **CAP)
f.label('t-sig', ['Common', 'Signature', 'Components', '(sig:)'], 76.5, cx=2652.5, **CAP)
f.label('t-xxx', ['Extension', 'Signature', 'Components', '(xxx:)'], 79.5, cx=3164.4, **CAP)
f.label('t-cac', ['Common', 'Aggregate', 'Components', '(cac:)'], 415, cx=683, **CAP)
f.label('t-ext', ['Common', 'Extension', 'Components', '(ext:)'], 415, cx=1544, **CAP)
f.label('t-ecd1', ['Extension', 'Content', 'Datatype', '(ext:)'], 415.5, cx=2128.8, **CAP)
f.label('t-sac', ['Signature', 'Aggregate', 'Components', '(sac:)'], 414.4, cx=2652.4, **CAP)
f.label('t-xac', ['Extension', 'Aggregate', 'Components', '(xac:)'], 420, cx=3164.5, **CAP)
f.label('t-cbc', ['Common', 'Basic', 'Components', '(cbc:)'], 775, cx=900, **CAP)
f.label('t-sbc', ['Signature', 'Basic', 'Components', '(sbc:)'], 773, cx=2665.5, **CAP)
f.label('t-xbc', ['Extension', 'Basic', 'Components', '(xbc:)'], 778, cx=3181.4, **CAP)
f.label('t-qdt', ['Qualified/', 'Specialized', 'Datatypes', '(qdt:)'], 1204.4, cx=707.3, **CAP)
f.label('t-udt', ['Unqualified', 'Datatypes', '(udt:)'], 1371.4, cx=1197.8, **CAP)
f.label('t-ds', ['W3C Digital Signature', 'Schema (ds:)'], 1229, cx=2632.7, **CAP)
f.label('t-xades', ['XAdES Schemas', 'v2.3.1 and v1.4.1'], 1403, cx=2540.2, **CAP)
f.label('t-ccts', ['CCTS CCT', 'Schema', '(ccts-cct:)'], 1692, cx=1207.8, **CAP)
f.label('t-ecd2', ['Extension', 'Content', 'Datatype', '(ext:)'], 1623.8, cx=2132, **CAP)
f.label('t-core', ['Core', 'Component', 'Parameters', '(ccts:)'], 1650, cx=709, **CAP)
f.label('t-custom', ['Customization', 'Extension', 'Replacement', 'Schemas'], 1625.8, cx=3182.5, **CAP)
IT = dict(pitch=66.5, bold=True, italic=True)
f.label('r-apex', ['Apex', 'Constructs'], 108.5, cx=228.9, **IT)
f.label('r-aggregate', ['Aggregate', 'Constructs'], 483, cx=242.6, **IT)
f.label('r-basic', ['Basic', 'Constructs'], 842.5, cx=242.6, **IT)
f.label('r-datatype', ['Data Type', 'Constructs'], 1274.5, cx=242.6, **IT)
f.label('r-foreign', ['Foreign', 'Constructs'], 1271, cx=1892.4, **IT)
f.label('r-documentation', ['Documentation', 'Namespace'], 1520.5, cx=715, **IT)
f.label('r-legend', ['Legend'], 1607, cx=1651, **IT)
LG = dict(font=9.6, bold=True)
f.label('lg-include', ['include'], 1681, cx=1647, white=170, **LG)
f.label('lg-import', ['import'], 1752, cx=1647, white=165, **LG)
f.label('lg-replace', ['replace'], 1828, cx=1651, white=175, **LG)
print(f.write())
