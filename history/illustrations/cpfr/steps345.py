"""UBL-2.2-CPFR-Steps3-4-5 as a draw.io illustration (cpfr.py): shapes measured on art/UBL-2.2-CPFR-Steps3-4-5.png
(1712 x 1976, frame 6 px; its source, iSURF's figure, 613 px wide), in the PNG's px."""
from cpfr import Drawing
d = Drawing('UBL-2.2-CPFR-Steps3-4-5', (1712, 1976), 6, 613)
# the steps
d.panel((41.5, 93, 778, 1927.5))
d.panel((920.5, 97.5, 1665, 1247.5))
d.panel((925.5, 1311, 1669.5, 1458), dashed=True, label='CPFR Step 6')
d.title('CPFR Step 3', (520, 112, 755, 150))
d.title('CPFR Step 4-5', (1380, 126, 1652, 164))
# the documents passed between the parties
d.arrow('Product Activity (POS Data)', 74, 726.5, 265, 392.5, 42, 64, 'west')
d.arrow('Product Activity (DC Data)', 74, 726.5, 566, 693.5, 42, 64, 'west')
d.arrow('Sales Forecast', 74, 726.5, 882, 1009.5, 42, 64, 'east')
d.arrow('Sales Forecast Revision', 74, 726.5, 1213, 1340.5, 42, 64, 'west')
d.arrow('Sales Forecast Revision', 74, 726.5, 1505, 1632.5, 42, 64, 'east')
d.arrow('Wait for Exception Notification', 964, 1615, 325, 465, 48, 70, None, size=12.8, fill='#eaeaea')
# the documents, the exception, the people resolving it
for k in ('doc1', 'doc2', 'doc3', 'doc4', 'doc5'):
    d.picture('cpfr-document', k)
d.picture('cpfr-exception', 'clipboard')
d.picture('cpfr-person-at-desk', 'desk-left')
d.picture('cpfr-person-at-desk', 'desk-right', flip=True)
d.resolve((1082.5, 860, 1504.5, 1012))
# the flows, over the arrows and the documents (a document's top and bottom slope: they meet the flow at x 410
# 16 and 113 px below its top-left corner)
for y0, y1 in ((255, 455), (552, 775), (872, 1102), (1199, 1394), (1491, 1664)):
    d.edge([(410, y0), (410, y1)])
d.edge([(532, 1741.5), (678.5, 1741.5), (678.5, 1160), (443, 1160)])
d.edge([(410, 1816), (410, 1863), (872.5, 1863), (872.5, 48), (1293, 48), (1293, 96.5)])
d.edge([(1293, 360), (1293, 508)])
d.edge([(1293, 660), (1293, 858)])
d.edge([(1168, 585), (946, 585), (946, 1190.5), (1298, 1190.5), (1298, 1309.5)])
# the decisions, the guards
d.decision('Sales Forecast<br>Accepted?', (287.5, 1665, 532, 1816))
d.decision('Exception<br>Received?', (1168.5, 509.5, 1417.5, 660))
for lab, cx, cy in (('No', 678, 1401), ('Yes', 871.5, 976), ('Yes', 1293, 757), ('No', 945.5, 1011.5)):
    d.guard(lab, cx, cy)
d.write()
