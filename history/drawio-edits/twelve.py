"""One text size in the drawings: draw.io's own 12 pt. Every label loses its
fontSize (12 is draw.io's default); a box its text no longer fits is widened
or heightened about its centre, to whole pixels, and every flow end on it keeps
its point on the page (its fraction recomputed).

    python3 twelve.py <diagrams dir>
"""
import glob, html, math, re, sys, collections
import xml.etree.ElementTree as ET
from PIL import ImageFont
FONT = {0: 'Regular', 1: 'Bold', 2: 'Italic', 3: 'BoldItalic'}
FONTS = {k: ImageFont.truetype('/usr/share/fonts/truetype/liberation/LiberationSans-%s.ttf' % v, 12) for k, v in FONT.items()}
PAD, LINE = 4, 12 * 1.2          # room each side; draw.io's line height
report = collections.Counter(); grown = []

def ttf(style, size):
    return ImageFont.truetype('/usr/share/fonts/truetype/liberation/LiberationSans-%s.ttf' % FONT[int(style) & 3], max(1, round(size)))

def block(lines, style, size):
    """a label's width and height at a size"""
    f = ttf(style, size)
    return max(f.getlength(l) for l in lines), len(lines) * size * 1.2

def num(v):
    return str(int(round(v)))

def st(c): return [p.split('=', 1) if '=' in p else [p, None] for p in (c.get('style') or '').split(';') if p]
def put(c, pairs): c.set('style', ''.join((k if v is None else '%s=%s' % (k, v)) + ';' for k, v in pairs))
def words(label):
    t = re.sub(r'<br\s*/?>', '\n', label or ''); return html.unescape(re.sub(r'<[^>]+>', '', t)).split('\n')

HAND = {'UBL-2.2-CRP-ChangeArticleCatalogue': 'decision-producer', 'UBL-2.2-VMI-PermanentReplenishment': 'decision-producer'}

for path in sorted(glob.glob(sys.argv[1] + '/*/*.drawio')):
    fig = path.split('/')[-2]
    tree = ET.parse(path); root = tree.getroot().find('.//root')
    cells = {}
    for el in root:
        c = el if el.tag == 'mxCell' else el.find('mxCell')
        cells[el.get('id')] = (el, c)
    # page places of the vertices, for the flows' ends
    def place(i):
        el, c = cells[i]; g = c.find('mxGeometry')
        if g is None or c.get('edge') == '1' or g.get('relative') == '1': return (0.0, 0.0)
        p = place(c.get('parent')) if c.get('parent') in cells else (0.0, 0.0)
        return (p[0] + float(g.get('x', 0)), p[1] + float(g.get('y', 0)))
    changed = {}
    before_font = {i: float(dict(st(c)).get('fontSize', 12)) for i, (el, c) in cells.items() if c is not None and c.get('edge') == '1'}
    for i, (el, c) in cells.items():
        if c is None: continue
        pairs = st(c); d = dict(pairs)
        if 'fontSize' in d:
            old = float(d['fontSize'])
            if old != 12: report['labels resized'] += 1
            pairs = [p for p in pairs if p[0] != 'fontSize']; put(c, pairs)
            kind = el.get('ubl-kind')
            label = el.get('label') if el.tag == 'object' else c.get('value')
            g = c.find('mxGeometry')
            sp = {k: float(d.get(k, 0)) for k in ('spacingLeft', 'spacingRight', 'spacingTop', 'spacingBottom')}
            outside = False
            if label and g is not None and kind in ('decision', 'initial', 'final', 'action', 'object', 'note'):
                w, h = float(g.get('width')), float(g.get('height'))
                lines0 = words(label); ow, oh = block(lines0, d.get('fontStyle', 0), old); nw_, nh_ = block(lines0, d.get('fontStyle', 0), 12)
                al = d.get('align', 'center')
                dx, dy = (sp['spacingLeft'] - sp['spacingRight']) / 2, (sp['spacingTop'] - sp['spacingBottom']) / 2
                if al == 'center':
                    outside = abs(dx) >= (w + ow) / 2 - 1 or abs(dy) >= (h + oh) / 2 - 1
                elif al == 'left':
                    outside = sp['spacingLeft'] >= w - 1 or abs(dy) >= (h + oh) / 2 - 1
                else:
                    outside = sp['spacingRight'] >= w - 1 or abs(dy) >= (h + oh) / 2 - 1
                if outside:
                    # words beside the shape (a decision's question, "From Order"):
                    # the shape keeps its size, the words their gap to it
                    horiz = abs(dx) - (w + ow) / 2 >= abs(dy) - (h + oh) / 2 if al == 'center' else abs(dy) < (h + oh) / 2 - 1
                    if horiz and al == 'center':
                        k = 'spacingLeft' if dx > 0 else 'spacingRight'
                        sp[k] += nw_ - ow
                    elif not horiz:
                        k = 'spacingTop' if dy > 0 else 'spacingBottom'
                        sp[k] += nh_ - oh
                    for k, v in sp.items():
                        if v or k in d:
                            d[k] = num(v)
                    pairs = [[k, d[k] if k in d else v] for k, v in pairs] + [[k, d[k]] for k in sp if k in d and k not in dict(pairs)]
                    put(c, pairs)
                    report['labels beside a shape kept their gap'] += 1
            if kind in ('action', 'object', 'note', 'decision') and label and g is not None and not outside:
                w, h = float(g.get('width')), float(g.get('height'))
                font = FONTS[int(d.get('fontStyle', 0)) & 3]
                lines = words(label)
                tw = max(font.getlength(l) for l in lines); th = len(lines) * LINE
                if kind == 'decision':
                    # a diamond holds its words in its middle half: grow in step
                    oldf = ImageFont.truetype('/usr/share/fonts/truetype/liberation/LiberationSans-%s.ttf' % FONT[int(d.get('fontStyle', 0)) & 3], max(1, round(old)))
                    otw = max(oldf.getlength(l) for l in lines)
                    k = tw / otw if otw and tw > otw else 1.0
                    nw, nh = w * k, h * k
                else:
                    nw, nh = max(w, tw + 2 * PAD), max(h, th + 2 * PAD)
                    # the room it has: its lane (a document on a divider: the frame)
                    x0 = place(i)[0]
                    par = cells.get(c.get('parent'))
                    if kind == 'object' or par is None or par[0].get('ubl-kind') != 'lane':
                        fg = cells['frame'][1].find('mxGeometry'); lo, hi = float(fg.get('x')), float(fg.get('x')) + float(fg.get('width'))
                    else:
                        lo = place(c.get('parent'))[0]; hi = lo + float(par[1].find('mxGeometry').get('width'))
                    room = max(w, 2 * min(x0 + w / 2 - lo, hi - x0 - w / 2) - 2 * PAD)
                    if nw > room:
                        # too wide for its place: its longest lines break at the space
                        # nearest their middle, and the box grows in height instead
                        out = []
                        for l in lines:
                            if font.getlength(l) + 2 * PAD > max(w, room) and ' ' in l:
                                sp = [k for k, ch in enumerate(l) if ch == ' ']
                                k = min(sp, key=lambda k: abs(font.getlength(l[:k]) - font.getlength(l[k + 1:])))
                                out += [l[:k], l[k + 1:]]
                            else:
                                out.append(l)
                        if out != lines:
                            lines = out
                            if el.tag == 'object':
                                el.set('label', '<br>'.join(html.escape(l, quote=False) for l in lines))
                            report['labels broken over more lines'] += 1
                            tw = max(font.getlength(l) for l in lines); th = len(lines) * LINE
                            nw, nh = max(w, tw + 2 * PAD), max(h, th + 2 * PAD)
                        if nw > room:
                            report['still wider than its place'] += 1
                            print('  still too wide:', fig, i, round(nw - room))
                # about the centre, by an even number of whole pixels
                gw = math.ceil((nw - w) / 2) * 2 if nw > w + 1e-6 else 0
                gh = math.ceil((nh - h) / 2) * 2 if nh > h + 1e-6 else 0
                if gw or gh:
                    changed[i] = (gw, gh, place(i), w, h)
                    g.set('x', str(int(round(float(g.get('x')))) - gw // 2)); g.set('y', str(int(round(float(g.get('y')))) - gh // 2))
                    g.set('width', str(int(w) + gw)); g.set('height', str(int(h) + gh))
                    grown.append((fig, i, gw, gh))
    # a guard keeps its gap to its line: its box grew about its centre
    for i, (el, c) in cells.items():
        if c is None or c.get('edge') != '1': continue
        label = el.get('label') if el.tag == 'object' else c.get('value')
        o = before_font.get(i)
        if not label or o is None or o == 12: continue
        off = c.find('mxGeometry').find('mxPoint[@as="offset"]')
        if off is None: continue
        d = dict(st(c)); lines0 = words(label)
        ow, oh = block(lines0, d.get('fontStyle', 0), o); nw_, nh_ = block(lines0, d.get('fontStyle', 0), 12)
        ox, oy = float(off.get('x', 0)), float(off.get('y', 0))
        if abs(ox) >= ow / 2 and d.get('align', 'center') == 'center':
            off.set('x', num(ox + math.copysign((nw_ - ow) / 2, ox))); report['guards kept their gap'] += 1
        elif abs(oy) >= oh / 2:
            off.set('y', num(oy + math.copysign((nh_ - oh) / 2, oy))); report['guards kept their gap'] += 1
    # the flows' ends on a grown box keep their page point
    for i, (el, c) in cells.items():
        if c is None or c.get('edge') != '1': continue
        pairs = st(c); d = dict(pairs); upd = False
        for end, key in ((c.get('source'), 'exit'), (c.get('target'), 'entry')):
            if end in changed and key + 'X' in d:
                gw, gh, (x0, y0), w, h = changed[end]
                fx, fy = float(d[key + 'X']), float(d[key + 'Y'])
                px, py = x0 + fx * w, y0 + fy * h            # the old page point
                nx0, ny0, nw, nh = x0 - gw / 2, y0 - gh / 2, w + gw, h + gh
                fx2 = fx if fx in (0.0, 1.0) else (px - nx0) / nw
                fy2 = fy if fy in (0.0, 1.0) else (py - ny0) / nh
                d[key + 'X'] = ('%.6f' % fx2).rstrip('0').rstrip('.'); d[key + 'Y'] = ('%.6f' % fy2).rstrip('0').rstrip('.')
                upd = True
        if upd:
            put(c, [[k, d[k] if k in d else v] for k, v in pairs])
    # an element's own connection points follow (points=), for the grown ones
    for i in changed:
        el, c = cells[i]; pairs = st(c); d = dict(pairs)
        if d.get('points') and d['points'] != '[]':
            gw, gh, _, w, h = changed[i]
            pts = [tuple(float(v) for v in p.split(',')) for p in d['points'][2:-2].split('],[')]
            new = [((x if x in (0, 1) else (x * w + gw / 2) / (w + gw)), (y if y in (0, 1) else (y * h + gh / 2) / (h + gh))) for x, y in pts]
            d['points'] = '[%s]' % ','.join('[%s,%s]' % (('%.6f' % x).rstrip('0').rstrip('.'), ('%.6f' % y).rstrip('0').rstrip('.')) for x, y in new)
            put(c, [[k, d[k] if k in d else v] for k, v in pairs])
    # by eye, after the run: two questions of two lines sat too low beside
    # their diamond; they move up 6 px
    if fig in HAND:
        el, c = cells[HAND[fig]]; pairs = st(c)
        put(c, pairs + [['spacingBottom', '12']])
    tree.write(path, encoding='unicode')
print(dict(report), 'boxes grown:', len(grown))
for g in grown: print('  ', g)
