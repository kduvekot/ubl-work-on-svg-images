"""UBL-2.2-UDT-QDT: which schemas and stylesheets make up UBL's data types: the BBIE schemas (UBL 2.0 and 2.x), the
qualified data type (QDT) schemas and data type qualification (DTQ) stylesheets / code value assertions (CVA) in
between, the UN/CEFACT unqualified data type (UDT) schemas below them, with the arrows of what imports what, each box
marked with a circled letter (A..N) and bracketed on the left (BBIE, QDT DTQ, UDT) and on the right (Other
Qualifications, Code Lists, XML Types) by braces, and divided by dashed and dotted rules. Drawn from the UBL
repository's art/<figure>.png (3425 x 2200, grey 230 fill in the boxes, black and white otherwise).
Scale 1/5.9: the 71 px text (capital height 51) is draw.io's 12 px, the circled letters (cap 40) 9.5 px, the 3 px box
lines and 2.6 px arrows 0.5 px, the 7 px braces 1.2, the 10 px frame 1.7."""
from lib_c import Figure, n

S = 5.9
NAME = 'UBL-2.2-UDT-QDT'
f = Figure(NAME, 3425, 2200, S, __file__, grey=True)
f.frame(10)
r = f.r
BS = 2.8                      # box stroke, PNG px


def rule(ident, x0, x1, y, dash, gap, stroke=3):
    """a dashed or dotted horizontal rule (a line, not a flow); draw.io scales dashPattern by the stroke width"""
    st = ('html=1;rounded=0;endArrow=none;startArrow=none;strokeWidth=%s;dashed=1;dashPattern=%s %s;'
          % (n(stroke / S), n(round(dash / stroke, 3)), n(round(gap / stroke, 3))))
    f.edge(ident, 'line', '', st, [(r(x0), r(y)), (r(x1), r(y))])


def brace(ident, x0, y0, x1, y1, right=False, stroke=7, size=0.5):
    st = 'shape=curlyBracket;rounded=1;whiteSpace=wrap;html=1;fillColor=none;strokeWidth=%s;size=%s;' % (n(stroke / S), n(size))
    if right:
        st += 'flipH=1;'
    f.vertex(ident, 'brace', '', st, r(x0), r(y0), r(x1 - x0), r(y1 - y0))


# dashed (16 / 5.65) and dotted (5 / 5) rules
D, G = 16.2, 5.45
rule('rule-1', 339, 2416, 48, D, G)
rule('rule-2a', 339, 1218, 424, D, G)
rule('rule-2b', 1224, 2811, 424, 5, 5)
rule('rule-3', 1006, 2137, 674, 5, 5)
rule('rule-4', 339, 2448, 1285, D, G)
rule('rule-5', 1003, 2810, 1504, 5, 5)
rule('rule-6a', 355, 1234, 2159, D, G)
rule('rule-6b', 2040, 2816, 2159, 5, 5)

# braces
brace('brace-bbie', 204, 48, 296, 426, size=0.457)
brace('brace-qdt', 212, 424, 312, 1285)
brace('brace-udt', 218, 1285, 306, 2159)
brace('brace-other', 2820, 424, 2920, 674, right=True)
brace('brace-codelists', 2820, 674, 2920, 1504, right=True)
brace('brace-xml', 2820, 1504, 2920, 2159, right=True)

# boxes (outer edge, PNG px)
BOX = dict(stroke=BS, fill='grey')
f.box('A', 308, 107, 905, 363, **BOX)
f.box('B', 1338, 110, 1794, 363, **BOX)
f.box('C', 339, 721, 670, 974, **BOX)
f.box('D', 754, 721, 1085, 974, **BOX)
f.box('E', 1270, 721, 1602, 974, **BOX)
f.box('F', 1681, 721, 2013, 974, **BOX)
f.box('G', 1681, 1002, 2013, 1255, **BOX)
f.box('H', 2134, 439, 2465, 989, **BOX)
f.box('J', 2493, 439, 2825, 989, **BOX)
f.box('K', 308, 1347, 905, 1603, **BOX)
f.box('M', 1338, 1560, 1794, 1813, **BOX)
f.box('N', 1213, 1890, 1919, 2147, **BOX)

# arrows: the shaft 2.6 px, the head 38 px long and wide
HEAD = dict(head='block', size=5.4, stroke=2.6)
f.flow('f-A-C', 'A', 'C', (507, 363), (504, 721), via=[(507, 541), (504, 543)], **HEAD)
f.flow('f-A-K', 'A', 'K', (705, 363), (705, 1347), **HEAD)
f.flow('f-C-K', 'C', 'K', (504, 974), (506.5, 1347), **HEAD)
f.flow('f-B-E', 'B', 'E', (1490, 363), (1490, 721), **HEAD)
f.flow('f-B-M', 'B', 'M', (1641, 363), (1641, 1560), **HEAD)
f.flow('f-E-M', 'E', 'M', (1490, 974), (1490, 1560), **HEAD)
f.flow('f-M-N', 'M', 'N', (1565, 1813), (1565, 1890), **HEAD)

# circled letters: ring 68 px, white; the letter 40 px high
# (ring centre x, y), then the letter's capital top and centre x as measured
CIR = {'A': (854.5, 234.5, 212, 855.5), 'B': (1741.5, 245.5, 226, 1743.5), 'C': (624, 858, 834, 624),
       'D': (1042, 844, 824, 1045), 'E': (1558, 850, 829, 1560.5), 'F': (1970, 849, 829, 1973),
       'G': (1970, 1125, 1103, 1969.5), 'H': (2416.5, 930, 907, 2417.5), 'J': (2776.5, 930, 909, 2776.5),
       'K': (855, 1549, 1528, 858), 'M': (1743, 1684, 1663, 1743), 'N': (1869, 2089, 2069, 1867.5)}
for k, v in CIR.items():
    f.box('c-' + k, v[0] - 34, v[1] - 34, v[0] + 34, v[1] + 34, stroke=3, fill='white', shape='ellipse')
for k, v in CIR.items():
    f.label('l-' + k, [k], v[2], cx=v[3], font=9.5, shift=3)

# text, 71 px
P = 83
kw = dict(pitch=P)
f.label('t-A', ['UBL 2.0', 'BBIE', 'XSD'], 123, cx=606, **kw)
f.label('t-B', ['UBL 2.x', 'BBIE', 'XSD'], 124, cx=1565, **kw)
for k, x, y2, x2, y3, x3 in (('C', 381, 'QDT', 434, 'XSD', 433), ('D', 796, 'DTQ', 851, 'XSLT', 833),
                              ('E', 1312, 'QDT', 1366, 'XSD', 1365), ('F', 1724, 'DTQ', 1779, 'CVA', 1780)):
    f.label('t-%s-1' % k, ['UBL 2.0' if k in 'CD' else 'UBL 2.x'], 735, left=x)
    f.label('t-%s-2' % k, [y2], 818, left=x2)
    f.label('t-%s-3' % k, [y3], 901, left=x3)
f.label('t-G-1', ['UBL 2.x'], 1016, left=1724)
f.label('t-G-2', ['DTQ'], 1099, left=1779)
f.label('t-G-3', ['XSLT'], 1183, left=1761)
f.label('t-H', ['Custom', 'DTQ', 'CVA'], 601, cx=2299, **kw)
f.label('t-J', ['Custom', 'DTQ', 'XSLT'], 601, cx=2658, **kw)
f.label('t-K', ['UN/CEFACT UDT', 'XSD 1.1 Rev A'], 1362, cx=605, **kw)
f.label('t-K-3', ['16 Feb 2005'], 1528, left=414)
f.label('t-M', ['UBL 2.x', 'UDT', 'XSD'], 1575, cx=1566, **kw)
f.label('t-N', ['UN/CEFACT', 'CCTS CCT Schema'], 1906, cx=1565, **kw)
f.label('t-N-3', ['XSD 1.1 050114'], 2072, left=1323)
f.label('t-bbie', ['BBIE'], 208, left=43)
f.label('t-qdt', ['QDT', 'DTQ'], 784, left=82, **kw)
f.label('t-udt', ['UDT'], 1693, left=82)
f.label('t-other', ['Other', 'Qualifications'], 478, left=2933, pitch=84)
f.label('t-codelists', ['Code Lists'], 1061, left=2911)
f.label('t-xml', ['XML Types'], 1803, left=2932)
print(f.write())
