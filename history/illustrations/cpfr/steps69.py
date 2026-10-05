"""UBL-2.2-CPFR-Steps6-9 as a draw.io illustration (cpfr.py): shapes measured on art/UBL-2.2-CPFR-Steps6-9.png
(1712 x 1369, frame 5 px; its source, iSURF's figure, 950 px wide), in the PNG's px."""
from cpfr import Drawing, FONT
d = Drawing('UBL-2.2-CPFR-Steps6-9', (1712, 1369), 5, 950)
# the steps
d.panel((41.5, 60, 522, 1257.5))
d.panel((616.5, 63, 1097, 807.5))
d.panel((1190.5, 64, 1671, 1078.5))
d.panel((618.5, 843.5, 1098.5, 940.5), dashed=True, label='CPFR Step 9<br>-- ORDER GENERATION --')
d.panel((1189.5, 1103.5, 1671.5, 1199.5), dashed=True, label='CPFR Step 2')
d.title('CPFR Step 6', (300, 66, 506, 104))
d.title('CPFR Step 7-8', (850, 70, 1088, 108))
d.text('Exception<br>Monitor During<br>Execution', (1490, 66, 1679, 150), 12.7, '#505050', 'center')
# the documents passed between the parties
X = 280
d.arrow('Inventory Status', 70, 493, 174, 256, 27.5, 43, 'west', cx=X)
d.arrow('Product Activity (POS Data)', 70, 493, 347, 429, 28, 43, 'west', cx=X)
d.arrow('Retail Event', 70, 493, 520, 602, 28, 43, 'west', cx=X)
d.arrow('Order Forecast', 70, 493, 703, 785, 27.5, 42, 'east', cx=X)
d.arrow('Order Forecast Revision', 66, 488, 884, 966, 26.5, 43, 'west', cx=X)
d.arrow('Order Forecast Revision', 62, 485, 1054, 1136, 27.5, 42, 'east', cx=X)
d.arrow('Wait for Exception Notification', 642, 1063, 204, 294, 31, 45, None, cx=854, fill='#eaeaea')
d.arrow('Wait for Exception Notification', 1218, 1640, 204, 294, 31, 45, None, cx=1429, fill='#eaeaea')
d.arrow('Termination Message', 1218, 1640, 822, 904, 28, 42, 'east', cx=1428)
# the documents, the exceptions, the people resolving them
for k in ('doc1', 'doc2', 'doc3', 'doc4', 'doc5', 'doc6', 'doc7'):
    d.picture('cpfr-document', k)
d.picture('cpfr-exception', 'clipboard1')
d.picture('cpfr-exception', 'clipboard2')
for k in ('desk1', 'desk2'):
    d.picture('cpfr-person-at-desk', k + '-left')
    d.picture('cpfr-person-at-desk', k + '-right', flip=True)
d.resolve((716, 550, 990, 648))
d.resolve((1293, 553, 1566, 651))
# the end
d.vertex('ellipse;html=1;shape=endState;fillColor=#000000;strokeColor=#000000;strokeWidth=1;', (1414, 1261, 1456, 1303))
d.text('<b>Finalize CPFR Process</b>', (1330, 1308, 1540, 1336), 9.8)
# the flows (a document's top and bottom slope: they meet the flow 0.12 and 0.85 of its height below its top)
tops = [d.fit['doc%d' % i][1] for i in range(1, 8)]; h = d.fit['doc1'][3]
for a, b in zip(tops[:5], tops[1:6]):
    d.edge([(X, a + 0.85 * h), (X, b + 0.12 * h)])
d.edge([(X, tops[5] + 0.85 * h), (X, 1139)])
d.edge([(361, 1187), (495, 1187), (495, 852), (303, 852)])
d.edge([(X, 1257), (X, 1295), (552, 1295), (552, 38), (857, 38), (857, 63)])
d.edge([(854, 230), (854, 321)])
d.edge([(854, 422), (854, 550)])
d.edge([(775, 373), (632, 373), (632, 767), (858, 767), (858, 843)])
d.edge([(1098.5, 890), (1130, 890), (1130, 35), (1429.5, 35), (1429.5, 64)])
d.edge([(1428, 230), (1428, 319)])
d.edge([(1428, 437), (1428, 553)])
d.edge([(1332, 377), (1205, 377), (1205, 693), (1430, 693), (1430, tops[6] + 0.12 * h)])
d.edge([(1428, tops[6] + 0.85 * h), (1428, 903)])
d.edge([(1428, 1027), (1428, 1103)])
d.edge([(1332, 965), (1158, 965), (1158, 1222), (1436, 1222), (1436, 1261)])
# the decisions, the guards
d.decision('Order Forecast<br>Accepted?', (200, 1139, 361, 1236), size=9.5, lift=4)
d.decision('Exception<br>Received?', (775, 321, 936, 422), size=9.5, lift=4)
d.decision('Exception<br>Received During a<br>Defined Period?', (1332, 319, 1525, 436), size=9.5, lift=4)
d.decision('Termination<br>Message<br>Received within a<br>Defined Period?', (1332, 903, 1526, 1027), size=9.5, lift=4)
for lab, cx, cy in (('No', 495, 988), ('Yes', 550, 653), ('Yes', 852, 484), ('No', 631, 649), ('Yes', 1428, 493),
                    ('No', 1205, 523), ('No', 1429, 1061), ('Yes', 1153, 1117)):
    d.guard(lab, cx, cy, size=9.5)
d.write()
