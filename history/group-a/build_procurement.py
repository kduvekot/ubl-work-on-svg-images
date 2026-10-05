"""UBL-2.3-ProcurementProcess: the overview of the two phases, as a phase map.
Drawn from the UBL repository's UBL-2.3-ProcurementProcess.drawio (images/, 2020-05-12) and
its PNG, at 0.3 of that drawing's scale, so its 60 px text is 18 px and its 8 px lines 2."""
from lib import Fig

S = 0.3
r = lambda v: round(v * S)
NAME = 'UBL-2.3-ProcurementProcess'
LINE = 'strokeWidth=2;'
TXT = 'fontSize=18;'

f = Fig(NAME, r(2757), r(818), 'UBL artwork, Group A (history/group-a/build_procurement.py)')
f.vertex('frame', 'frame', '', 'rounded=0;whiteSpace=wrap;html=1;fillColor=none;' + LINE, 0, 0, r(2757), r(818), **{'ubl-notation': 'phase-map'})
f.vertex('title', 'title', 'Procurement Process', 'rounded=0;whiteSpace=wrap;html=1;fillColor=none;gradientColor=none;' + LINE + TXT,
         r(212), r(53), r(2348), r(106))
PENT = ('shape=singleArrow;arrowWidth=1;arrowSize=%s;whiteSpace=wrap;html=1;fillColor=#ffffff;align=left;spacingLeft=15;verticalAlign=middle;' % (
    round(243 / 882, 3)) + LINE + TXT)
f.vertex('phase-pre-award', 'phase', 'Pre-award', PENT, r(202), r(356), r(882), r(266))
f.vertex('phase-post-award', 'phase', 'Post-award', PENT, r(1625), r(372), r(882), r(266))
f.vertex('milestone-contract-signature', 'milestone', 'Contract signature',
         'rhombus;whiteSpace=wrap;html=1;fillColor=#ffffff;' + LINE + TXT, r(1147), r(292), r(404), r(425))
print(f.write())
