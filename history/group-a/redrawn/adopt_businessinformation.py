"""UBL-2.4-BusinessInformation: the UBL repository's own draw.io drawing (images/, 2023-02-06, sources/),
adopted as it is drawn: the same pools, lanes, tasks, events and flows at the same places and sizes
(they already are draw.io's own BPMN parts), written uncompressed in the editor's form, each element
with the model's id and kind (`ubl-kind`), and the one change below.

  - the grey (#C0C0C0) bar at the foot of each task is white: the drawings are black and white only
    (an export's print PNG is 1 bit, where a light grey is lost); the rules above and below the task's
    words, which make the bars, stay.
"""
import base64, html, re, urllib.parse, zlib
import xml.etree.ElementTree as ET
from lib import Fig, ROOT, drawio_format, q
import os

NAME = 'UBL-2.4-BusinessInformation'
src = open(os.path.join(os.path.dirname(__file__), '..', 'sources', NAME + '.drawio'), encoding='utf-8').read()
data = re.search(r'<diagram[^>]*>(.*?)</diagram>', src, re.S).group(1)
model = ET.fromstring(urllib.parse.unquote(zlib.decompress(base64.b64decode(data), -15).decode()))
root = model.find('root')

cells = {}                  # id -> (element holding the attributes, mxCell)
order = []
for el in root:
    c = el if el.tag == 'mxCell' else el.find('mxCell')
    cells[el.get('id')] = (el, c)
    order.append(el.get('id'))


def label(i):
    el, c = cells[i]
    t = el.get('label') if el.tag != 'mxCell' else el.get('value')
    t = html.unescape(re.sub(r'<br\s*/?>', ' ', t or ''))
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', t)).strip()


def slug(t):
    return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')


kind, new = {}, {}
children = {}
for i in order:
    children.setdefault(cells[i][1].get('parent'), []).append(i)
for i in order:
    if i in ('0', '1'):
        continue
    c = cells[i][1]
    st = c.get('style') or ''
    p = c.get('parent')
    if c.get('edge') == '1':
        kind[i] = 'flow'
    elif st.startswith('swimlane'):
        kind[i] = 'pool' if p == '1' else 'lane'
    elif 'part=1' in st:
        kind[i] = 'part'
    elif 'stackLayout' in st and 'rounded=1' in st:
        kind[i] = 'task'
    elif st.startswith('ellipse'):
        kind[i] = 'start'
    elif 'shape=mxgraph.bpmn.event' in st:
        kind[i] = 'end'
    elif st.startswith('shape=message'):
        kind[i] = 'message'
    elif st.startswith('text'):
        kind[i] = 'title' if 'fontSize=24' in st else 'text'
    else:
        raise SystemExit('unknown element %s: %s' % (i, st))


def name_of(i):
    k = kind[i]
    if k == 'task':
        return label([j for j in children[i] if 'bpmn.task' in (cells[j][1].get('style') or '')][0])
    return label(i)


def owner(i):
    """the pool and lane a shape stands in"""
    while i in cells and kind.get(i) != 'lane':
        i = cells[i][1].get('parent')
    return i


pools = [i for i in order if kind.get(i) == 'pool']
for i in pools:
    new[i] = 'pool-' + slug(label(i))
    for j in children.get(i, []):
        if kind[j] == 'lane':
            new[j] = 'lane-%s-%s' % (slug(label(i)), slug(label(j)))
    # a pool's "System" lane: the pool's own name makes it unique
for i in order:
    k = kind.get(i)
    if k == 'task':
        new[i] = 'task-' + slug(name_of(i))
    elif k == 'part':
        new[i] = new[cells[i][1].get('parent')] + '-part-' + str(sum(1 for j in order[:order.index(i)] if cells[j][1].get('parent') == cells[i][1].get('parent')) + 1)
    elif k in ('start', 'end'):
        lane = owner(i)
        new[i] = '%s-%s' % (k, new[lane][len('lane-'):])
    elif k == 'title':
        new[i] = 'title'
n_msg = 0
for i in order:
    if kind.get(i) == 'message':
        n_msg += 1
        new[i] = 'message-%d' % n_msg
msg_names = {}
for i in order:       # a text beside a message flow names it: the envelope nearest to it
    pass

used = set(new.values())
for i in order:
    if kind.get(i) in ('text',):
        new[i] = 'text-' + slug(label(i))
for i in order:
    if kind.get(i) == 'flow':
        c = cells[i][1]
        a, b = new.get(c.get('source'), '?'), new.get(c.get('target'), '?')
        msg = kind.get(c.get('source')) == 'message' or kind.get(c.get('target')) == 'message' or \
            kind.get(c.get('source')) == 'message'
        new[i] = '%s-%s-to-%s' % ('message-flow' if msg else 'flow', a, b)
vals = list(new.values())
dupes = {v for v in vals if vals.count(v) > 1}
if dupes:
    raise SystemExit('ids not unique: %s' % dupes)


def geometry_xml(c):
    return ET.tostring(c.find('mxGeometry'), encoding='unicode')


f = Fig(NAME, 827, 1169, 'UBL artwork, Group A (history/group-a/adopt_businessinformation.py)')
out = []
for i in order:
    if i in ('0', '1'):
        continue
    el, c = cells[i]
    k = kind[i]
    st = (c.get('style') or '').replace('fillColor=#C0C0C0;', '')
    parent = new.get(c.get('parent'), '1')
    ident = new[i]
    extra = {}
    if k == 'task':
        extra['ubl-label'] = name_of(i)
    if k == 'title':
        extra['ubl-notation'] = 'bpmn'
    if k == 'flow':
        msg = 'message' in ident.split('-to-')[0] or ident.startswith('message-flow')
        k = 'message-flow' if msg else 'flow'
        extra['ubl-flow'] = 'message' if msg else 'sequence'
    value = (el.get('label') if el.tag != 'mxCell' else el.get('value')) or ''
    if k == 'part':
        value = value
    attrs = ' '.join('%s="%s"' % (a, q(b)) for a, b in [('label', value)] + ([('ubl-kind', k)] if k != 'part' else []) + list(extra.items()))
    mc = ET.Element('mxCell', {'parent': parent, 'style': st})
    for a in ('vertex', 'edge', 'source', 'target'):
        if c.get(a):
            mc.set(a, new.get(c.get(a), c.get(a)) if a in ('source', 'target') else c.get(a))
    mc.append(c.find('mxGeometry'))
    f.cells.append('<object %s id="%s">%s</object>' % (attrs, q(ident), ET.tostring(mc, encoding='unicode')))
print(f.write())
