"""UBL-2.2-Open-edi-Application: how the Open-edi reference model's two views (BOV, FSV) are realised in a user
community's configuration and in UBL (sections 2 to 5 of the specification). Drawn from the UBL repository's
art/<figure>.png (3425 x 3184, `ubl-2.5`; Ken Holman's SVG only wraps it). Black and white there too.
Scale 1/5.5: the 66 px text is draw.io's 12 px, the 6 px lines 1. The arrows are one outline each (a custom
shape, `stencil`: the original's head is longer and narrower than draw.io's)."""
from lib_b import Fig, stencil

S = 5.5
r = lambda v: round(v / S, 2)
NAME = 'UBL-2.2-Open-edi-Application'
W, H = 3425, 3184
FPX = 12 * S

f = Fig(NAME, r(W), r(H), 'UBL artwork, Group B (history/group-b/build_openedi_application.py)')
f.vertex('frame', 'frame', '', 'rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeWidth=1.8;', r(5), r(5), r(W - 10), r(H - 10),
         **{'ubl-notation': 'overview'})

DOT = 'rounded=1;absoluteArcSize=1;arcSize=%d;whiteSpace=wrap;html=1;fillColor=none;dashed=1;dashPattern=2.5 4.8;strokeWidth=1;'


def dotted(ident, x0, y0, x1, y1, arc=60):
    f.vertex(ident, 'frame', '', DOT % round(arc / S), r(x0), r(y0), r(x1 - x0), r(y1 - y0))


# the three columns and the two rows (centre lines, PNG px)
dotted('column-model', 250.5, 44.5, 971, 3131.5)
dotted('column-community', 1404, 44.5, 2351, 3131.5)
dotted('column-ubl', 2656.5, 44.5, 3337, 3131.5)
dotted('row-bov', 51, 425, 3372, 1565)
dotted('row-fsv', 51, 1805, 3372, 3098.5)

BOX = 'rounded=1;absoluteArcSize=1;arcSize=%d;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeWidth=1;'


def box(ident, x0, y0, x1, y1, arc):
    f.vertex(ident, 'box', '', BOX % round(arc / S), r(x0), r(y0), r(x1 - x0), r(y1 - y0))


box('implemented-bov', 1474, 518, 2281, 1471, 45)
box('implemented-fsv', 1474, 2065, 2281, 2865, 45)
for ident, y0, y1 in (('environment', 677, 804), ('scenarios', 859.5, 986), ('roles', 1042, 1168.5), ('information-bundles', 1224.5, 1418),
                      ('user-data', 2238, 2431.5), ('choreographies', 2488, 2615), ('transport', 2672, 2798)):
    box(ident, 1564, y0, 2191, y1, 60)
box('open-edi-implementation', 1111, 785, 1264.5, 2698, 0)
box('ubl-customization', 2444.5, 1072, 2598, 2565, 0)

# arrows: head 288 x 168, shaft 67, the head's back 53 behind its barbs (PNG px)
HL, HW, SW, JOIN = 288, 168, 67, 235


def arrow(ident, tip, tail, yc):
    length = abs(tail - tip)
    pts = [(0, HW / 2), (HL, 0), (JOIN, HW / 2 - SW / 2), (length, HW / 2 - SW / 2), (length, HW / 2 + SW / 2), (JOIN, HW / 2 + SW / 2), (HL, HW)]
    if tail < tip:                                  # tip on the right: mirror
        pts = [(length - u, v) for u, v in pts]
    w, h = r(length), r(HW)
    local = [(r(u), r(v)) for u, v in pts]
    f.vertex(ident, 'arrow', '', stencil(local, w, h) + 'fillColor=#000000;strokeColor=none;html=1;', r(min(tip, tail)), r(yc - HW / 2), w, h)


arrow('model-to-bov', 1472, 966, 995)
arrow('model-to-fsv', 1472, 966, 2465)
arrow('ubl-to-bov', 2190, 2675, 1325)
arrow('ubl-to-fsv', 2190, 2675, 2345)

f.vertex('brace', 'bracket', '', 'shape=curlyBracket;rounded=1;whiteSpace=wrap;html=1;fillColor=none;strokeWidth=2.4;flipH=1;size=0.5;',
         r(2691), r(1960.5), r(2783 - 2695), r(2727.5 - 1956.5))

BASE = 'text;html=1;verticalAlign=middle;whiteSpace=nowrap;strokeColor=none;fillColor=none;fontSize=12;spacing=0;'


def text(ident, lines, top, x, pitch=None, align='left', bold=False, asc=0.72, rot=False):
    """lines of text whose first line's ink top is at `top` (PNG px); x: the ink's left edge (align left) or centre (centre).
    rot: reading upwards, `top` is then the line's ink left, and x the start of the text (its ink's bottom)"""
    n = len(lines)
    pitch = pitch or 1.15 * FPX
    h = n * pitch
    label = '<br>'.join(lines)
    if n > 1:
        label = '<div style="line-height: %d%%">%s</div>' % (round(100 * pitch / FPX), label)
    style = BASE + ('fontStyle=1;' if bold else '') + 'align=%s;' % align
    centre = top + (asc - 0.3465) * FPX + (n - 1) * pitch / 2 + 4.5
    x += 7 if align == 'left' else 0
    if align == 'left':
        wd = min(1500, W - 20 - (x - 4))
        f.vertex(ident, 'text', label, style, r(x - 4), r(centre - h / 2), r(wd), r(h))
    else:
        wd = min(1500, 2 * (x - 20), 2 * (W - x - 20))
        f.vertex(ident, 'text', label, style, r(x - wd / 2), r(centre - h / 2), r(wd), r(h))


def vtext(ident, label, cx, cy, length):
    """one line reading upwards, its line box centred on (cx, cy); length: the ink's extent along the line"""
    wd = length + 100
    h = 1.15 * FPX
    f.vertex(ident, 'text', label, BASE + 'fontStyle=1;horizontal=0;align=center;', r(cx - h / 2), r(cy - wd / 2), r(h), r(wd))


P = 82
text('t-title-model', ['ISO/IEC 14662', 'Open-edi', 'Reference', 'Model'], 77, 391, P, bold=True, asc=0.716)
text('t-title-community', ['User', 'Community', 'Open-edi', 'Configuration'], 77, 1663, P, bold=True, asc=0.716)
text('t-title-ubl', ['Universal', 'Business', 'Language', 'Specification'], 77, 2816, P, bold=True, asc=0.716)
text('t-bov', ['Perspective of', 'business', 'transactions limited', 'to those aspects', 'regarding the', 'making of business',
               'decisions and', 'commitments', 'among Persons,', 'which are needed', 'for the description', 'of a business', 'transaction'],
     477, 326, P)
text('t-fsv', ['Perspective of', 'business', 'transactions limited', 'to those information', 'technology', 'interoperability',
               'aspects of', 'Information', 'Technology', 'Systems needed to', 'support the', 'execution of', 'transactions among',
               'Open-edi', 'Community parties.'], 1844, 316, P)
text('t-impl-bov', ['Implemented BOV'], 563, 1870, align='center', bold=True)
text('t-impl-fsv', ['Implemented FSV'], 2124, 1885, align='center', bold=True)
text('t-environment', ['Environment'], 717, 1877, align='center')
text('t-scenarios', ['Scenarios'], 899, 1877, align='center')
text('t-roles', ['Roles'], 1082, 1877, align='center')
text('t-information-bundles', ['Information', 'Bundles'], 1256, 1877, P, align='center')
text('t-user-data', ['User', 'Data'], 2270, 1877, P, align='center')
text('t-choreographies', ['Choreographies'], 2521, 1877, align='center')
text('t-transport', ['Transport'], 2705, 1877, align='center')
text('t-section-2', ['Section 2. UBL', 'Business Objects'], 1263, 2763, P)
text('t-sections', ['Section 3. UBL', 'Schemas', '', 'Section 4. Addi-', 'tional Document', 'Constraints', '', 'Section 5. UBL', 'Digital Signatures'],
     1983, 2788, P)
vtext('t-label-bov', 'BOV - Business Operational View', 144, 1004, 1052)
vtext('t-label-fsv', 'FSV - Functional Services View', 151, 2432.5, 983)
vtext('t-open-edi-implementation', 'Open-edi Implementation', 1192, 1746, 800)
vtext('t-ubl-customization', 'UBL Customization', 2528, 1838, 640)
print(f.write())
