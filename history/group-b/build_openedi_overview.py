"""UBL-2.2-Open-edi-Overview: the Open-edi reference model (ISO/IEC 14662): business transactions viewed as
a Business Operational View and a Functional Service View, each covered by standards. Drawn from the UBL
repository's art/<figure>.png (3425 x 2667, `ubl-2.5`; Ken Holman's SVG only wraps it). Black and white
there too. Scale 1/6.6: the 80 px text is draw.io's 12 px, the 6 px lines 1, the 10 px frame and dashes 1.5.
The arrows are one outline each (a custom shape, `stencil`): the original's head is longer and narrower
than any of draw.io's arrowheads."""
from lib_b import Fig, stencil

S = 6.6
r = lambda v: round(v / S, 2)
NAME = 'UBL-2.2-Open-edi-Overview'
W, H = 3425, 2667
F = 12 * S                      # the text, in PNG px

f = Fig(NAME, r(W), r(H), 'UBL artwork, Group B (history/group-b/build_openedi_overview.py)')
f.vertex('frame', 'frame', '', 'rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeWidth=1.5;', r(5), r(5), r(W - 10), r(H - 10),
         **{'ubl-notation': 'overview'})

BOX = 'rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeWidth=1;'


def box(ident, x0, y0, x1, y1, outer_stroke=6.6):
    d = outer_stroke / 2
    f.vertex(ident, 'box', '', BOX, r(x0 + d), r(y0 + d), r(x1 - x0 - 2 * d), r(y1 - y0 - 2 * d))


box('transactions', 194, 101, 342, 2566)
box('bov', 896, 460, 1970, 952)
box('bov-standards', 2512, 534, 3230, 916)
box('fsv', 896, 1897, 1970, 2399)
box('fsv-standards', 2512, 1935, 3230, 2317)
f.vertex('reference-model', 'box', '', 'rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeWidth=1.5;dashed=1;dashPattern=3.1 3.1;',
         r(827), r(293.5), r(2019.5 - 827), r(2509.5 - 293.5))

# arrows: head 187 x 95, shaft 20 (PNG px), along the axis from the tip
HL, HW, SW, JOIN = 187, 95, 20, 138


def arrow(ident, tip, tail, across, kind='lr', both=False):
    """tip, tail: the ends along the axis (PNG px); across: the axis' other coordinate; kind 'lr' horizontal, 'ud' vertical"""
    length = abs(tail - tip)
    sgn = 1 if tail > tip else -1               # direction from tip to tail
    pts = [(0, HW / 2), (HL, 0), (JOIN, HW / 2 - SW / 2)]
    if both:
        pts += [(length - JOIN, HW / 2 - SW / 2), (length - HL, 0), (length, HW / 2), (length - HL, HW), (length - JOIN, HW / 2 + SW / 2)]
    else:
        pts += [(length, HW / 2 - SW / 2), (length, HW / 2 + SW / 2)]
    pts += [(JOIN, HW / 2 + SW / 2), (HL, HW)]
    lo = min(tip, tail)
    if sgn < 0:                                  # tip at the far end: mirror along the axis
        pts = [(length - u, v) for u, v in pts]
    if kind == 'lr':
        w, h, x, y = r(length), r(HW), r(lo), r(across - HW / 2)
        local = [(r(u), r(v)) for u, v in pts]
    else:
        w, h, x, y = r(HW), r(length), r(across - HW / 2), r(lo)
        local = [(r(v), r(u)) for u, v in pts]
    f.vertex(ident, 'arrow', '', stencil(local, w, h) + 'fillColor=#000000;strokeColor=none;html=1;', x, y, w, h)


arrow('comply-bov', 1975, 2508, 616.5)               # points left
arrow('covered-bov', 2506, 1975, 832.5)              # points right
arrow('comply-fsv', 1975, 2503, 2030)
arrow('covered-fsv', 2503, 1974, 2245.5)
arrow('viewed-as', 833, 362, 1399.5)
arrow('bov-to-fsv', 1749, 972, 1103.5, 'ud')         # points down
arrow('fsv-to-bov', 974, 1751, 1703.5, 'ud')         # points up
arrow('interrelated', 938, 1916, 2813.5, 'ud', both=True)

TEXT = 'text;html=1;align=center;verticalAlign=middle;whiteSpace=nowrap;strokeColor=none;fillColor=none;fontSize=12;spacing=0;'


def text(ident, lines, top, cx, pitch=None, font=12, asc=0.72, white=None):
    """lines of text whose first line's ink top is at `top` (PNG px) and whose ink is centred on `cx`;
    `pitch` the distance between lines (px) where it is not the single-line height"""
    fpx = font * S
    n = len(lines)
    pitch = pitch or 1.15 * fpx
    centre = top + (asc - 0.3465) * fpx + (n - 1) * pitch / 2 + 3      # +3: where the export lies (align.py)
    h = n * pitch
    label = '<br>'.join(lines)
    if n > 1:
        label = '<div style="line-height: %d%%">%s</div>' % (round(100 * pitch / fpx), label)
    style = TEXT.replace('fontSize=12', 'fontSize=%d' % font)
    if white:
        style = style.replace('fillColor=none', 'fillColor=#ffffff')
    w = white or min(1500, 2 * (cx - 20), 2 * (W - cx - 20))
    f.vertex(ident, 'text', label, style, r(cx - w / 2), r(centre - h / 2), r(w), r(h))


text('t-model', ['Open-edi Reference Model'], 152, 1432.5)
text('t-bov', ['Business Operational View'], 345, 1432)
text('t-bov-box', ['Business aspects', 'of', 'business transactions'], 561, 1433, 120)
text('t-fsv', ['Functional Service View'], 1809, 1432)
text('t-fsv-box', ['Information technology', 'aspects of', 'business transactions'], 2002, 1432, 120)
text('t-bov-std', ['BOV RELATED', 'STANDARDS'], 632, 2866, 120)
text('t-fsv-std', ['FSV RELATED', 'STANDARDS'], 2039, 2867, 120)
text('t-comply-bov', ['Comply with'], 499, 2270)
text('t-covered-bov', ['Covered by'], 710, 2270)
text('t-comply-fsv', ['Comply with'], 1912, 2270)
text('t-covered-fsv', ['Covered by'], 2123, 2270)
text('t-viewed', ['Viewed as'], 1260, 567)
text('t-interrelated', ['Inter-related'], 1393, 2842.5, white=600)
text('t-transactions', list('BUSINESS') + [''] + list('TRANSACTIONS'), 228, 272, 106.6, font=16, asc=0.688)
print(f.write())
