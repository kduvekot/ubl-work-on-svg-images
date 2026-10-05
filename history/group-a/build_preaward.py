"""UBL-2.3-Pre-awardProcess: the pre-award phase as a map of steps per party, with the documents
exchanged at each step. Drawn from the UBL repository's UBL-2.3-Pre-awardProcess.drawio (images/,
2020-05-13) and its PNG, at 0.3 of that drawing's scale: its 70, 60 and 40 px text is 21, 18 and
12 px (draw.io's own size), its 8 px lines 2. The drawing's frame is at (1595, 122) there; the
coordinates below are from that frame's top left, as the PNG has them (frame at 1, 7)."""
import json
from lib import Fig

S = 0.3
r = lambda v: round(v * S)
NAME = 'UBL-2.3-Pre-awardProcess'
LINE = 'strokeWidth=2;'
BIG = 'fontSize=21;'      # step labels, 70 px
MID = 'fontSize=18;'      # title and parties, 60 px
W, H = 3425, 2397

f = Fig(NAME, r(W), r(H), 'UBL artwork, Group A (history/group-a/build_preaward.py)')
f.vertex('frame', 'frame', '', 'rounded=0;whiteSpace=wrap;html=1;fillColor=none;' + LINE, 0, 0, r(W), r(H), **{'ubl-notation': 'phase-map'})
f.vertex('title', 'title', 'Pre-award Process', 'rounded=0;whiteSpace=wrap;html=1;fillColor=none;gradientColor=none;' + LINE + MID,
         r(440), r(48), r(2906), r(109))

PARTY = {'authority': 'Contracting Authority', 'publisher': 'Publication Body', 'operator': 'Economic Operator'}
for pid, label, x, y in (('authority', 'Contracting<br>Authority', 169, 473), ('publisher', 'Publication<br>Body', 167, 1138),
                         ('operator', 'Economic<br>Operator', 155, 1741)):
    f.vertex('party-' + pid, 'party', label,
             'shape=umlActor;verticalLabelPosition=bottom;labelBackgroundColor=#ffffff;verticalAlign=top;html=1;outlineConnect=0;'
             'fillColor=none;gradientColor=none;' + LINE + MID, r(x), r(y), r(104), r(218), **{'ubl-party': PARTY[pid]})

STEP = 'shape=step;perimeter=stepPerimeter;whiteSpace=wrap;html=1;fixedSize=1;size=%d;fillColor=#ffffff;gradientColor=none;align=left;spacingLeft=18;' % r(50)
PENT = 'shape=singleArrow;arrowWidth=1;arrowSize=%s;whiteSpace=wrap;html=1;fillColor=#ffffff;align=left;spacingLeft=18;verticalAlign=middle;'
# id, label (lines), x, y, width, party, shape
steps = [
    ('prepare', ['Prepare'], 432, 445, 625, 'authority', 'first'),
    ('notify', ['Notify'], 923, 445, 721, 'authority', 'step'),
    ('receive', ['Receive'], 1397, 445, 511, 'authority', 'step'),
    ('evaluate', ['Evaluate'], 1768, 445, 656, 'authority', 'step'),
    ('award', ['Award'], 2316, 445, 586, 'authority', 'step'),
    ('contract', ['Contract'], 2801, 445, 586, 'authority', 'step'),
    ('publish-notices', ['Publish Notices'], 432, 1105, 943, 'publisher', 'pent'),
    ('publish-notice', ['Publish Notice'], 2759, 1105, 597, 'publisher', 'pent'),
    ('register', ['Register'], 432, 1686, 467, 'operator', 'first'),
    ('receive-call-for-tenders', ['Receive', 'Call for', 'Tenders'], 793, 1686, 503, 'operator', 'step'),
    ('create-tender', ['Create', 'Tender'], 1172, 1686, 441, 'operator', 'step'),
    ('submit-tender', ['Submit', 'Tender'], 1493, 1686, 508, 'operator', 'step'),
    ('operator-contract', ['Contract'], 2758, 1697, 597, 'operator', 'pent'),
]
for ident, lines, x, y, w, party, shape in steps:
    head = {'step': 0, 'first': 50, 'pent': 165}[shape]       # the first step of a row has a flat left side
    style = (STEP if shape == 'step' else PENT % round(head / w, 3)) + LINE + BIG
    f.vertex('step-' + ident, 'step', '<br>'.join(lines), style, r(x), r(y), r(w), r(272), **{'ubl-party': PARTY[party]})

# the documents exchanged at a step: [id, step(s), [documents, each as its lines], text box x, y, w, h,
#                                    the dashed line from its free end round the corner to the step]
docs = [
    ('d-authority-prepare-above', ['prepare'], 'above', [['Tender Status'], ['Unsubscribe from Procedure Response'], ['Enquiry'], ['Enquiry Response']],
     485, 248, 710, 172, [(788, 235), (466, 235), (466, 432)]),
    ('d-authority-prepare', ['prepare'], 'below', [['Prior Information Notice']],
     471, 735, 430, 52, [(793, 850), (450, 850), (450, 719)]),
    ('d-authority-notify', ['notify'], 'below',
     [['Contract Notice'], ['Call for Tenders'], ['Expression of Interest', '  Response'], ['Qualification Application', '  Request']],
     949, 689, 435, 372, [(1265, 1066), (923, 1066), (923, 719)]),
    ('d-authority-receive', ['receive'], 'below', [['Tender Receipt']],
     1449, 743, 279, 52, [(1768, 845), (1426, 845), (1426, 719)]),
    ('d-authority-evaluate', ['evaluate'], 'below', [['Tenderer Qualification', '  Response']],
     1832, 698, 399, 180, [(2157, 887), (1815, 887), (1815, 719)]),
    ('d-authority-award', ['award'], 'below', [['Contract Award Notice'], ['Awarded Notification'], ['Unawarded Notification']],
     2368, 697, 424, 228, [(2692, 960), (2349, 960), (2349, 719)]),
    ('d-authority-contract', ['contract'], 'below', [['Tender Contract']],
     2903, 732, 295, 52, [(3232, 836), (2889, 836), (2889, 719)]),
    ('d-publisher-publish-notices', ['publish-notices'], 'below', [['Prior Information Notice'], ['Contract  Notice']],
     452, 1395, 430, 100, [(770, 1515), (432, 1515), (432, 1378)]),
    ('d-publisher-publish-notice', ['publish-notice'], 'below', [['Contract Award Notice']],
     2811, 1399, 407, 52, [(3128, 1479), (2785, 1479), (2785, 1378)]),
    ('d-operator-register-above', ['register'], 'above', [['Expression of Interest  Request']],
     474, 1582, 568, 132, [(793, 1610), (450, 1610), (450, 1686)]),
    ('d-operator-submit-tender-above', ['submit-tender'], 'above',
     [['Tender'], ['Tenderer Qualification'], ['Qualification Application', '  Response']],
     1569, 1434, 435, 276, [(1881, 1441), (1538, 1441), (1538, 1686)]),
    ('d-operator-contract-above', ['operator-contract'], 'above', [['Guarantee Certificate']],
     2793, 1619, 390, 52, [(3123, 1596), (2781, 1596), (2781, 1697)]),
    ('d-operator-register', ['register', 'receive-call-for-tenders'], 'below',
     [['Tender Status Request'], ['Unsubscribe From Procedure Request'], ['Enquiry'], ['Enquiry Response']],
     460, 1972, 693, 276, [(860, 2217), (450, 2217), (450, 1959)]),
    ('d-operator-submit-tender', ['submit-tender'], 'below', [['Tender Withdrawal']],
     1527, 1961, 341, 180, [(1931, 2071), (1521, 2071), (1521, 1959)]),
    ('d-operator-contract', ['operator-contract'], 'below', [['Tender Contract']],
     2802, 1985, 295, 52, [(3130, 2090), (2788, 2090), (2788, 1970)]),
]
TEXT = 'text;html=1;align=left;verticalAlign=middle;resizable=0;points=[];autosize=0;spacing=0;spacingLeft=2;'
for ident, steps_, placement, items, x, y, w, h, line in docs:
    label = '<br>'.join('<br>'.join(lines) for lines in items)
    f.vertex(ident, 'documents', label, TEXT, r(x), r(y), r(w), r(h),
             **{'ubl-steps': json.dumps(['step-' + s for s in steps_]), 'ubl-placement': placement,
                'ubl-documents': json.dumps([lines[0] if len(lines) == 1 else ' '.join(t.strip('  ') for t in lines) for lines in items])})
    f.edge(ident + '-line', 'bracket', '', 'endArrow=none;dashed=1;html=1;' + LINE, [(r(a), r(b)) for a, b in line],
           **{'ubl-for': ident})
print(f.write())
