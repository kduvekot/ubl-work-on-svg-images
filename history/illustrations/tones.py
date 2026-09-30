# The UBL PNGs' own greys for the clip art's colours: each colour picture is
# rendered where the fit found it in the PNG, and each of its colours gets the
# median grey of the PNG pixels it covers (inside the colour's areas, away from
# their edges), over all placements in the four figures. Writes the parts in
# those greys to illustrations/parts/ (a colour it did not see: its luminance),
# and the greys to <WORK>/tones.json.
#
#   python3 tones.py          after fit.py has run for the four
import json, os, re, subprocess, collections
import numpy as np, cv2
from scipy import ndimage

from paths import ART, FIGURES, PARTS, WORK, work
from register import node_env
SRC = {'supplier': 'pic04', 'buyer': 'pic05', 'forwarder': 'pic08', 'supplier-b': 'pic09',
       'buyer-b': 'pic10', 'parcel-box': 'pic06', 'parcel-wrapped': 'pic07'}
FIGS = list(FIGURES.values())
env = node_env()

# the jobs: every placed clip art picture, rendered in colour at its size in the PNG
jobs, where = [], []
for f in FIGS:
    fit = json.load(open(os.path.join(WORK, 'fit', f + '.json')))
    S, DX, DY = fit['scale'], fit['dx'], fit['dy']
    for k in fit['shown']:
        r = fit['shapes'][str(k)]
        if r['kind'] != 'picture' or r['part'] not in SRC: continue
        x, y, w, h = r['geom']
        X, Y, W, H = x * S + DX, y * S + DY, w * S, h * S
        svg = open(os.path.join(WORK, 'svg', SRC[r['part']] + '.svg')).read()
        out = work('tones', '%s-%s.png' % (f, k))
        page = ('<html><body style="margin:0;background:#fff"><img src="data:image/svg+xml;base64,%s" '
                'style="display:block;width:%dpx;height:%dpx" draggable=false></body></html>')
        import base64
        jobs.append(dict(html=page % (base64.b64encode(svg.encode()).decode(), round(W), round(H)), out=out, w=round(W), h=round(H)))
        where.append((f, r['part'], round(X), round(Y), out))
json.dump(jobs, open(work('tones', 'jobs.json'), 'w'))
js = """const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch();const p=await b.newPage();
for(const j of JSON.parse(fs.readFileSync(process.argv[2]))){await p.setViewportSize({width:j.w,height:j.h});
await p.setContent(j.html);await p.waitForTimeout(50);await p.screenshot({path:j.out});}await b.close();})();"""
open(work('tones', 'r.js'), 'w').write(js)
subprocess.run(['node', work('tones', 'r.js'), work('tones', 'jobs.json')], check=True, env=env)

# per part and colour: the PNG's greys under that colour
samples = collections.defaultdict(list)
pngs = {f: cv2.imread(os.path.join(ART, f + '.png'), 0) for f in FIGS}
for f, part, X, Y, out in where:
    col = cv2.imread(out)[:, :, ::-1]
    P = pngs[f]
    h, w = col.shape[:2]
    y0, x0 = max(0, Y), max(0, X); y1, x1 = min(P.shape[0], Y + h), min(P.shape[1], X + w)
    col = col[y0 - Y:y1 - Y, x0 - X:x1 - X]; g = P[y0:y1, x0:x1]
    colours = {}
    for c in re.findall(r'#[0-9a-f]{6}', open(os.path.join(WORK, 'svg', SRC[part] + '.svg')).read()):
        colours[c] = tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    for c, rgb in colours.items():
        m = np.all(col == np.array(rgb, np.uint8), axis=2)
        m = ndimage.binary_erosion(m, iterations=3)          # away from edges and outlines
        if m.sum() >= 30:
            samples[(part, c)].append(g[m])
tones = {}
for (part, c), v in samples.items():
    v = np.concatenate(v)
    tones.setdefault(part, {})[c] = dict(grey=int(np.median(v)), n=int(v.size))
json.dump(tones, open(work('tones.json'), 'w'), indent=1)

# the parts in the PNGs' greys (a colour not seen: the luminance, as before)
os.makedirs(PARTS, exist_ok=True)
def lum(c):
    r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    return round(0.299 * r + 0.587 * g + 0.114 * b)
for part, pic in SRC.items():
    svg = open(os.path.join(WORK, 'svg', pic + '.svg')).read()
    t = tones.get(part, {})
    def sub(m):
        c = m.group(0).lower()
        y = t[c]['grey'] if c in t else lum(c)
        return '#%02x%02x%02x' % (y, y, y)
    open(os.path.join(PARTS, part + '.svg'), 'w').write(re.sub(r'#[0-9a-fA-F]{6}', sub, svg))
    seen = sorted(((c, v['grey'], lum(c), v['n']) for c, v in t.items()), key=lambda q: -q[3])
    print(part, ' '.join('%s:%d(lum %d)' % (c, gv, l) for c, gv, l, n in seen[:8]))
