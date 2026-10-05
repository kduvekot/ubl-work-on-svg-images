"""UBL-2.2-CPFR-Steps1-2 as a draw.io illustration (cpfr.py): shapes measured on art/UBL-2.2-CPFR-Steps1-2.png
(1712 x 2323, frame 4.5 px; its source, iSURF's figure, 647 px wide), in the PNG's px."""
from cpfr import Drawing, FONT
d = Drawing('UBL-2.2-CPFR-Steps1-2', (1712, 2323), 4.5, 647)
# the steps
d.panel((41.5, 88, 744.5, 2266.5))
d.panel((958.5, 102, 1670.5, 1873.5))
d.panel((958.5, 1903.5, 1671.5, 2045.5), dashed=True, label='CPFR Step 3')
d.title('CPFR Step 1', (470, 108, 704, 142))
d.title('CPFR Step 2', (1410, 122, 1646, 156))
# the documents passed between the parties
L, R = (84, 704), (1003, 1622)
XC = 388
d.arrow('Purchase Conditions', L[0], L[1], 952, 1071, 40, 61, 'west', cx=XC)
d.arrow('Exception Criteria', L[0], L[1], 1243, 1362, 40.5, 61, 'east', cx=XC)
d.arrow('Exception Criteria Revision', L[0], L[1], 1547, 1666, 40.5, 61, 'west', cx=XC)
d.arrow('Exception Criteria Revision', L[0], L[1], 1842, 1961, 40.5, 61, 'east', cx=XC)
d.arrow('Retail Event', R[0], R[1], 252, 372, 40.5, 61, 'west', cx=1313.5)
d.arrow('Retail Event Revision', R[0], R[1], 538, 657, 41.5, 61, 'east', cx=1313.5)
d.arrow('Trade Item Location Profile', R[0], R[1], 1142, 1261, 40.5, 61, 'east', cx=1313.5)
d.arrow('Trade Item Location Profile Revision', R[0], R[1], 1448, 1567, 40.5, 61, 'west', cx=1313.5, size=12.8)
# the manual steps: the meeting and the collaboration agreement, each marked Manual
d.picture('cpfr-meeting', 'meeting')
d.picture('cpfr-agreement', 'agreement')
M = 'rounded=1;arcSize=50;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#000000;strokeWidth=1;fontStyle=1;fontSize=11.5;' + FONT
d.vertex(M, (472, 209, 686.5, 282), 'Manual')
d.vertex(M, (472, 594, 686.5, 668), 'Manual')
d.text('Meeting', (300, 383, 410, 419), 13)
d.text('Collaboration Agreement', (230, 721, 545, 757), 13)
for k in ('doc1', 'doc2', 'doc3', 'doc4', 'doc5', 'doc6', 'doc7', 'doc8'):
    d.picture('cpfr-document', k)
# the flows (a document's top and bottom slope: they meet the flow 16 and 113 px below its top-left corner)
x1, x2 = 388, 1313.5
d.edge([(355.5, 409), (355.5, 532)])
d.edge([(x1, 724), (x1, 866)])
for t0, t1 in ((850, 1135), (1135, 1440), (1440, 1735)):
    d.edge([(x1, t0 + 110), (x1, t1 + 15)])
d.edge([(x1, 1735 + 110), (x1, 2009)])
d.edge([(508, 2079), (711, 2079), (711, 1519), (424, 1519)])
d.edge([(x1, 2151), (x1, 2197.5), (859.5, 2197.5), (859.5, 56), (x2, 56), (x2, 101)])
d.edge([(x2, 147 + 110), (x2, 435 + 15)])
d.edge([(x2, 435 + 110), (x2, 754)])
d.edge([(1433, 826), (1643.5, 826), (1643.5, 207), (1349, 207)])
d.edge([(x2, 898), (x2, 1035 + 15)])
d.edge([(x2, 1035 + 110), (x2, 1341 + 15)])
d.edge([(x2, 1341 + 110), (x2, 1622)])
d.edge([(1433, 1694.5), (1643.5, 1694.5), (1643.5, 1104.5), (1349, 1104.5)])
d.edge([(x2, 1765), (x2, 1900)])
# the decisions, the guards
d.decision('EC Accepted?', (272, 2010, 506, 2151), lift=0)
d.decision('RE Accepted?', (1196, 754, 1432, 898), lift=0)
d.decision('TILP<br>Accepted?', (1197, 1622, 1432, 1765))
for lab, cx, cy in (('No', 710, 1749), ('Yes', 857, 1131), ('No', 1641, 468), ('Yes', 1313.5, 973), ('No', 1641, 1351), ('Yes', 1313.5, 1833)):
    d.guard(lab, cx, cy)
d.write()
