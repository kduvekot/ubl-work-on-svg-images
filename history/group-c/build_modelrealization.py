"""UBL-2.3-ModelRealization: how UBL's model is realised as validation artefacts. Left of the thick vertical rule
the Modeling Artefacts (the CCTS document models and the common library model, with its aggregates and basics, the
context value association file, the Genericode files and the core component types); right of it the Validation
Artefacts: the document schema, the common aggregate / extension / basic components, the qualified and unqualified
datatypes, the CCTS CCT schema, the data type qualifications (XSLT), the extension content datatype, the common
signature components, the W3C digital signature schema and the XAdES schemas; a dashed box for the Core Component
Parameters (the documentation namespace), a dotted frame for the Customization (the replacement extension schemas),
and two legends (dotted 'referenced', long dashes 'generated', short dashes 'related'; short dashes 'include',
solid 'import', the hollow block arrow 'replace'). Stacked pages (Genericode Files, Common Signature Components,
Extension Datatype Definition) are boxes with offset copies behind. Drawn from the UBL repository's
art/<figure>.png (3425 x 2013, RGBA, `ubl-2.5`; black, white and the grey 230 of the qdt / udt / ccts boxes and the
Core Component Parameters box: the print PNG is greyscale on purpose).
Scale 1/4.5: the 54 px text (cap height 38.6) is draw.io's 12 px, the abbreviations 9, the legend labels 10 and the
italic notes as the PNG; box lines (6.3 px) 1.4, arrows and dotted / dashed lines (3 px) 0.67, the thick rule (11 px)
2.4, the 10 px frame 2.2. All numbers are PNG px, measured (rows and columns of the PNG, line fits for the diagonals)."""
from lib_c import Figure, n

S = 4.5
NAME = 'UBL-2.3-ModelRealization'
f = Figure(NAME, 3425, 2013, S, __file__, grey=True)
f.frame(10)
r = f.r
P = 64.3          # the text's line pitch

# ---- the thick rule (drawn as a line with round ends)
f.edge('rule', 'line', '', 'endArrow=none;html=1;rounded=0;strokeWidth=%s;strokeCap=round;' % n(11 / S),
       [(r(1262.5), r(30.5)), (r(1262.5), r(1968.5))])

BW = 6.3
HEAD = dict(head='block', stroke=3, size=5.6)
DOT, LONG, SHORT = (5.5, 7), (26.5, 21.5), (12.5, 4.2)


def box(i, x0, y0, x1, y1, stroke=BW, **kw):
    f.box(i, x0, y0, x1, y1, stroke=stroke, **kw)
    f.geo[i] = (x0 + stroke / 2, y0 + stroke / 2, x1 - stroke / 2, y1 - stroke / 2)   # exits / entries are given on the outer edge


# ---- boxes, left column
box('doc-models', 216, 108, 931, 306)
box('library', 543, 367, 1207, 1243)
box('aggregates', 728, 541, 1142, 835)
box('basics', 728, 925, 1149, 1219)
box('context', 41, 1192, 431, 1486)
box('cc-types', 664, 1316, 1176, 1505)
# the Genericode stack: pages behind (up and to the right)
box('genericode-p3', 60, 821, 371, 1013)
box('genericode-p2', 43, 846, 351, 1038)
box('genericode', 25, 868, 335, 1060)

# ---- boxes, right column
box('doc-schema', 1564, 108, 2279, 320)
box('cac', 1329, 443, 1719, 737)
box('ext', 2160, 443, 2569, 738)
box('cbc', 1522, 845, 1925, 1139)
box('qdt', 1329, 1238, 1716, 1529, fill='grey')
box('udt', 1827, 1399, 2214, 1628, fill='grey')
box('ccts-cct', 1841, 1728, 2223, 1951, fill='grey')
box('dtq', 1326, 1754, 1712, 1977)
box('ext-content', 2366, 891, 2775, 1185)
box('xades', 2277, 1828, 2855, 1978)
# the double arrows Extension Content to XAdES run behind the signature stack and the W3C box (z-order: first)
for i, x in (('f-ext-xades-1', 2667), ('f-ext-xades-2', 2705)):
    f.flow(i, 'ext-content', 'xades', (x, 1185), (x, 1828), **HEAD)
box('w3c', 2280, 1628, 2859, 1778)
# the signature stack: pages behind, down and to the right
box('sig-p3', 2388, 1289, 2796, 1583)
box('sig-p2', 2375, 1273, 2784, 1567)
box('sig', 2363, 1257, 2772, 1551)
# the customization frame (dotted) and what is in it
box('custom-frame', 2866, 606, 3394, 1581, stroke=3, fill=None, dashed=(3.5 * S / 3, 4.2 * S / 3), kind='frame')
box('ext-content-r', 2960, 891, 3368, 1185)
box('def-p3', 2918, 1243, 3326, 1553)
box('def-p2', 2905, 1227 + 16, 3314, 1537)
box('definition', 2893, 1227, 3302, 1521)
box('parameters', 2888, 239, 3273, 509, stroke=7, fill='grey', dashed=(36 * S / 7, 14 * S / 7))

# ---- arrows
def thin(i, s, t, p0, p1, via=(), dash=None, **kw):
    a = dict(HEAD); a.update(kw)
    f.flow(i, s, t, p0, p1, via=via, dash=dash and (dash[0] * S / 3, dash[1] * S / 3), **a)   # draw.io's dash pattern is in stroke widths

thin('f-models-schema', 'doc-models', 'doc-schema', (931, 206), (1564, 206), dash=SHORT)
thin('f-models-context', 'doc-models', 'context', (381, 306), (393, 1192), dash=LONG)
thin('f-models-aggregates', 'doc-models', 'aggregates', (416, 306), (728, 663), dash=DOT)
thin('f-models-basics', 'doc-models', 'basics', (459, 306), (730, 926), dash=DOT)
thin('f-aggregates-loop', 'aggregates', 'aggregates', (884, 835), (791, 835), via=[(884, 894), (791, 894)], dash=DOT)
thin('f-aggregates-basics', 'aggregates', 'basics', (947, 835), (947, 925), dash=DOT)
thin('f-aggregates-cac', 'aggregates', 'cac', (1142, 615), (1329, 579), dash=SHORT)
thin('f-basics-cbc', 'basics', 'cbc', (1149, 1034), (1522, 1000), dash=SHORT)
thin('f-basics-context', 'basics', 'context', (728, 1153), (431, 1344), dash=LONG)
thin('f-basics-types', 'basics', 'cc-types', (919, 1219), (919, 1316), dash=DOT)
thin('f-context-genericode', 'context', 'genericode', (197, 1192), (197, 1060), dash=DOT)
thin('f-types-cct', 'cc-types', 'ccts-cct', (1049, 1505), (1841, 1757), dash=SHORT,
     via=[(1127, 1522), (1213, 1545), (1300, 1584), (1337, 1592), (1423, 1624), (1510, 1656), (1597, 1682), (1683, 1706), (1770, 1744)])
thin('f-context-dtq', 'context', 'dtq', (431, 1463), (1326, 1792), dash=LONG)
thin('f-schema-cac', 'doc-schema', 'cac', (1650, 320), (1507, 443))
thin('f-schema-cbc', 'doc-schema', 'cbc', (1916, 320), (1724, 845))
thin('f-schema-ext', 'doc-schema', 'ext', (2187, 320), (2362, 443))
thin('f-cac-ext', 'cac', 'ext', (1719, 509), (2160, 574))
thin('f-cac-cbc', 'cac', 'cbc', (1543, 737), (1653, 845))
thin('f-ext-cbc', 'ext', 'cbc', (2297, 738), (1793, 845))
thin('f-ext-udt', 'ext', 'udt', (2364, 738), (2082, 1399))
thin('f-ext-content', 'ext', 'ext-content', (2452, 738), (2571, 891), dash=SHORT)
thin('f-cbc-qdt', 'cbc', 'qdt', (1714, 1139), (1542, 1238))
thin('f-cbc-udt', 'cbc', 'udt', (1844, 1139), (1956, 1399))
thin('f-qdt-udt', 'qdt', 'udt', (1716, 1381), (1827, 1513))
thin('f-udt-cct', 'udt', 'ccts-cct', (2030, 1628), (2030, 1728))
thin('f-content-sig', 'ext-content', 'sig', (2512, 1185), (2512, 1257))
thin('f-sig-cbc', 'sig', 'cbc', (2363, 1309), (1925, 975))
thin('f-sig-qdt', 'sig', 'qdt', (2363, 1357), (1716, 1299))
thin('f-sig-udt', 'sig', 'udt', (2363, 1422), (2214, 1511))
thin('f-sig-w3c', 'sig-p3', 'w3c', (2438, 1583), (2438, 1628))
thin('f-w3c-xades-1', 'w3c', 'xades', (2667, 1778), (2667, 1828))
thin('f-w3c-xades-2', 'w3c', 'xades', (2705, 1778), (2705, 1828))
thin('f-content-def', 'ext-content-r', 'definition', (3163, 1185), (3104, 1227))

# ---- 'replace': a hollow block arrow, open at the tail
def hollow(i, tip, head_x, head_y0, head_y1, y0, y1, tail):
    pts = [(tail, y0), (head_x, y0), (head_x, head_y0), tip, (head_x, head_y1), (head_x, y1), (tail, y1)]
    f.edge(i, 'line', '', 'endArrow=none;html=1;rounded=0;strokeWidth=%s;' % n(3 / S), [(r(x), r(y)) for x, y in pts])
hollow('replace', (2796, 1035), 2843, 942, 1133, 990, 1085, 2940)
hollow('legend-replace', (2939, 1873), 2972, 1807, 1938, 1840, 1906, 3323)

# ---- legend samples (lines with a head, not attached: kind 'line')
def sample(i, x0, x1, y, dash=None):
    st = 'html=1;rounded=0;endArrow=block;endFill=1;endSize=5.6;strokeWidth=%s;' % n(3 / S)
    if dash:
        st += 'dashed=1;dashPattern=%s %s;' % (n(dash[0] / 3), n(dash[1] / 3))
    f.edge(i, 'line', '', st, [(r(x0), r(y)), (r(x1), r(y))])
sample('legend-referenced', 57, 586, 1610, DOT)
sample('legend-generated', 57, 586, 1682, LONG)
sample('legend-related', 57, 586, 1743, SHORT)
sample('legend-include', 2875, 3386, 1722, SHORT)
sample('legend-import', 2875, 3390, 1795)

# ---- texts
def t(i, lines, top, **kw):
    kw.setdefault('font', 11.85)
    kw.setdefault('shift', -2)
    f.label(i, lines, top, pitch=P, **kw)
kw = dict(bold=True)
t('t-modeling', ['Modeling Artefacts'], 35, cx=573)
t('t-validation', ['Validation Artefacts'], 35, cx=2395.5)
t('t-doc-models', ['Document Models (CCTS)', 'e.g. Invoice, Order, etc.'], 124, cx=573.5)
t('t-doc-models-i', ['(Document ABIEs)'], 253, cx=575, italic=True)
t('t-library', ['Common Library Model', '(CCTS)'], 392, cx=865)
t('t-aggregates', ['Model', 'Aggregates'], 568, cx=935)
t('t-aggregates-i', ['(Library ABIEs', 'and ASBIEs)'], 695, cx=935, italic=True)
t('t-basics', ['Model', 'Basics'], 951, cx=935)
t('t-basics-i', ['(Document and', 'Library BBIEs)'], 1078, cx=935, italic=True)
t('t-context', ['Context', 'Value', 'Association', 'File'], 1220, cx=236)
t('t-cc-types', ['Core Component', 'Types (CCTS)'], 1354, cx=919)
t('t-genericode', ['Genericode', 'Files'], 911, cx=178)
t('t-doc-schema', ['Document Schema', 'e.g. Invoice, Order, etc.', '(document namespace)'], 128, cx=1921)
t('t-cac', ['Common', 'Aggregate', 'Components', '(cac:)'], 469, cx=1523)
t('t-ext', ['Common', 'Extension', 'Components', '(ext:)'], 472, cx=2364)
t('t-cbc', ['Common', 'Basic', 'Components', '(cbc:)'], 874, cx=1723)
t('t-qdt', ['Qualified/', 'Specialized', 'Datatypes', '(qdt:)'], 1261, cx=1522)
t('t-udt', ['Unqualified', 'Datatypes', '(udt:)'], 1430, cx=2019)
t('t-ccts-cct', ['CCTS CCT', 'Schema', '(ccts-cct:)'], 1748, cx=2029)
t('t-dtq', ['Data Type', 'Qualifications', 'XSLT'], 1778, cx=1522)
t('t-ext-content', ['Extension', 'Content', 'Datatype', '(ext:)'], 921, cx=2570)
t('t-ext-content-r', ['Extension', 'Content', 'Datatype', '(ext:)'], 921, cx=3164.5)
t('t-sig', ['Common', 'Signature', 'Components', '(sig: sac: sbc:)'], 1286, cx=2570)
t('t-definition', ['Extension', 'Datatype', 'Definition', '(xxx: xac: xbc:)'], 1257, cx=3096)
t('t-w3c', ['W3C Digital Signature', 'Schema (ds:)'], 1645, cx=2569)
t('t-xades', ['XAdES Schemas', 'v2.3.1 and v1.4.1'], 1851, cx=2566)
t('t-custom', ['Customization', 'Extension', 'Replacement', 'Schemas'], 627, cx=3130)
t('t-doc-namespace', ['Documentation', 'Namespace'], 127, cx=3083, italic=True)
t('t-parameters', ['Core', 'Component', 'Parameters', '(ccts:)'], 256, cx=3080)
t('t-legend-left', ['Legend'], 1527, cx=324, italic=True)
t('t-legend-right', ['Legend'], 1630, cx=3131, italic=True)
ab = dict(font=9.45, pitch=53.5, left=51, shift=-2)
f.label('t-abbr-1', ['CCTS: Core Component Technical Specification V2.01'], 1787, **ab)
f.label('t-abbr-2', ['ABIE: Aggregate Business Information Enttiy'], 1840, **ab)
f.label('t-abbr-3', ['ASBIE: Association Business Information Entity'], 1894, **ab)
f.label('t-abbr-4', ['BBIE: Basic Business Information Entity'], 1947, **ab)
print(f.write())
