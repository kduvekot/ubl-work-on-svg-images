"""UBL-2.2-DefaultValidation: the two phases of UBL's default validation of a document instance: a generic schema
validator (the UBL schema), then a generic XSLT processor (the Data Type Qualifications), each with its error
report. Drawn from the UBL repository's art/<figure>.png (3425 x 2248, `ubl-2.5`; Ken Holman's SVG only wraps it).
Black and white there too. Scale 1/5.9: the 71 px text is draw.io's 12 px, the 8 px arrows 1.3, the 5 px lines 1,
the 9 px frame 1.5; the notes beside the shapes (italic, 61 px) 10.3 px, the "error" labels 11, the last circle's 10.5."""
from lib_c import Figure

S = 5.9
NAME = 'UBL-2.2-DefaultValidation'
f = Figure(NAME, 3425, 2248, S, __file__)
f.frame(9)

R = 90
f.box('instance', 1403, 74, 1970, 548, shape='triangle-w')
f.box('schema', 632, 637, 1199, 1110, shape='triangle-w')
f.box('qualifications', 632, 1239, 1199, 1711, shape='triangle-w')
f.box('validator', 1473, 731, 2029, 1014, arc=R)
f.box('xslt', 1473, 1333, 2029, 1617, arc=R)
f.box('error-1', 2300, 729, 2587, 1017, shape='ellipse')
f.box('error-2', 2300, 1331, 2587, 1618, shape='ellipse')
f.box('downstream', 1608, 1887, 1893, 2172, shape='ellipse')

HEAD = dict(head="block", size=7.7, stroke=8)
f.flow('f-instance', 'instance', 'validator', (1751, 456), (1751, 731), **HEAD)
f.flow('f-schema', 'schema', 'validator', (1199, 873), (1473, 873), **HEAD)
f.flow('f-validator-xslt', 'validator', 'xslt', (1751, 1014), (1751, 1333), **HEAD)
f.flow('f-qualifications', 'qualifications', 'xslt', (1199, 1475), (1473, 1475), **HEAD)
f.flow('f-error-1', 'validator', 'error-1', (2029, 873), (2300, 873), **HEAD)
f.flow('f-error-2', 'xslt', 'error-2', (2029, 1475), (2300, 1475), **HEAD)
f.flow('f-downstream', 'xslt', 'downstream', (1751, 1617), (1751, 1887), **HEAD)

CAP = 71 * 0.716
def xcap(top):        # a first line with no capital or ascender: the ink top of its x-height, as a capital top
    return top - (CAP - 0.519 * 71)

kw = dict(bold=False)
f.label('t-instance', ['UBL', 'document', 'instance', '.xml file'], 161, right=1941, pitch=69.5, **kw)
f.label('t-schema', ['UBL', 'document', 'schema', '.xsd file'], 722, right=1166, pitch=69.5, **kw)
f.label('t-qualifications', ['UBL', 'Data Type', 'Qualifications', '.xsl file'], 1329, right=1166, pitch=69.5, **kw)
f.label('t-validator', ['Generic', 'schema', 'validator'], 773, cx=1751.5, pitch=69.5, **kw)
f.label('t-xslt', ['Generic', 'XSLT', 'processor'], 1375, cx=1751.5, pitch=69.5, **kw)
f.label('t-error-1', ['Error', 'report'], 809, cx=2447, pitch=69.5, **kw)
f.label('t-error-2', ['Error', 'report'], 1410, cx=2447, pitch=69.5, **kw)
f.label('t-downstream', ['Down-', 'stream', 'process'], 1932, cx=1752.5, font=10.5, pitch=62.5, **kw)
f.label('t-error-label-1', ['error'], xcap(814) - 0, left=2064, font=11, **kw)
f.label('t-error-label-2', ['error'], xcap(1415), left=2064, font=11, **kw)
it = dict(bold=False, italic=True, font=10.3, pitch=69.5)
f.label('n-first', ['First phase checks standard UBL structure,', 'vocabulary, and data typing against the', 'appropriate UBL schema'], 1064, left=2084, **it)
f.label('n-second', ['Second phase checks code list values against', 'the default values provided in the UBL release', 'package'], 1658, left=2080, **it)
f.label('n-default', ['The default .xsl file can easily be', 'replaced with a customized version to', 'manage code lists or add more data checking'], 1665, left=82, **it)
print(f.write())
