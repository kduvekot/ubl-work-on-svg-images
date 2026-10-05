"""UBL-2.2-IMFM-GenericIntermodalFreightProcess: the three phases of an intermodal freight process as
chevrons, with what is done in each. Drawn from the UBL repository's art/<figure>.png (3425 x 798,
`ubl-2.5`), not from Ken Holman's SVG, which is not this figure. Scale 1/6.6: the captions' 80 px
text is draw.io's 12 px, the titles' 100 px 15, the lines 7 px 1. Tuned against the PNG with
history/group-a/compare_png.py (notch depth 94 px: 2.8 % of the PNG's ink missing, 0.9 % extra)."""
from lib_b import Fig

S = 6.6
r = lambda v: round(v / S, 2)
NAME = 'UBL-2.2-IMFM-GenericIntermodalFreightProcess'
W, H = 3425, 798

f = Fig(NAME, r(W), r(H), 'UBL artwork, Group B (history/group-b/build_imfm.py)')
f.vertex('frame', 'frame', '', 'rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeWidth=1.5;', 0, 0, r(W), r(H),
         **{'ubl-notation': 'phase-map'})

STEP = 'shape=step;perimeter=stepPerimeter;whiteSpace=wrap;html=1;fixedSize=1;size=%s;fillColor=#ffffff;gradientColor=none;'
# id, title, title ink x centre, chevron x (centreline), caption ink x, caption lines
phases = [
    ('plan', 'Plan', 599.5, 85, 96, ['Select transport chain', 'Organize transport']),
    ('execute', 'Execute', 1688.5, 1157, 1206, ['Issue transport instructions', 'Monitor (detect deviations)']),
    ('complete', 'Complete', 2780.5, 2230, 2250, ['Issue proof of delivery', 'Handle invoices and payments', 'Handle claims']),
]
for pid, title, tx, cx, kx, lines in phases:
    f.vertex('phase-' + pid, 'phase', '', STEP % r(94), r(cx), r(85.5), r(1112), r(342))
    f.vertex('title-' + pid, 'text', title, 'text;html=1;align=center;verticalAlign=middle;whiteSpace=nowrap;fontSize=15;strokeColor=none;fillColor=none;',
             r(tx - 300), r(250 - 60), r(600), r(120))
    f.vertex('lines-' + pid, 'text', '<br>'.join(lines), 'text;html=1;align=left;verticalAlign=top;whiteSpace=nowrap;fontSize=12;strokeColor=none;fillColor=none;spacing=0;spacingLeft=0;',
             r(kx - 6), r(450), r(1000), r(len(lines) * 93.5 + 14))
print(f.write())
