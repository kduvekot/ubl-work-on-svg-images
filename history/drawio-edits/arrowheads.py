"""One arrowhead everywhere: every flow's head (and a start head, where a flow
has one) becomes UML's open arrowhead at 10 px (endArrow=open;endFill=0;
endSize=10), in place of the sizes measured from the artwork.

    python3 arrowheads.py <diagrams dir>
"""
import collections, glob, re, sys

c = collections.Counter()
for f in sorted(glob.glob(sys.argv[1] + '/*/*.drawio')):
    s = open(f).read()

    def fix(m):
        st = m.group(1)
        if 'edge="1"' not in m.group(0):
            return m.group(0)
        d = dict(p.split('=', 1) if '=' in p else (p, None) for p in st.split(';') if p)
        changed = False
        if d.get('endArrow') not in (None, 'none'):
            d['endArrow'] = 'open'; d['endFill'] = '0'; d['endSize'] = '10'; changed = True
        if d.get('startArrow') not in (None, 'none'):
            d['startArrow'] = 'open'; d['startFill'] = '0'; d['startSize'] = '10'; changed = True
        if changed:
            c['flows'] += 1
        new = ''.join((k if v is None else f'{k}={v}') + ';' for k, v in d.items())
        return m.group(0).replace(st, new, 1)
    s2 = re.sub(r'<mxCell style="([^"]*)"[^>]*>', fix, s)
    if s2 != s:
        c['files'] += 1
    open(f, 'w').write(s2)
print(dict(c))
