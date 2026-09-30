# Finds where the slide lands in the UBL PNG (slide px at 96/in -> PNG px: a
# scale and a shift) from landmarks: the Supplier, the Buyer and the first
# document picture, each found in the PNG by template matching over scales.
#
#   python3 register.py          prints each slide's scale and shift
import os, subprocess
import numpy as np, cv2, json, sys
from build import build, shapes_of, U, PIC
from paths import ART, FIGURES, HERE, work

def node_env():
    g = subprocess.run(['npm', 'root', '-g'], capture_output=True, text=True).stdout.strip()
    return dict(os.environ, NODE_PATH=os.pathsep.join(p for p in (os.environ.get('NODE_PATH'), g) if p))

def slide_png(n):
    """the slide as it is, rendered at 96/in (960 x 720 px)"""
    d, out = work('slides', 's%d.drawio' % n), work('slides', 's%d.png' % n)
    open(d, 'w').write(build(n))
    subprocess.run(['node', os.path.join(HERE, 'render.js'), d, out, '960', '720', '1', '0', '0'], check=True, env=node_env())
    return out

def landmarks(n):
    out = {}
    for s in shapes_of(n):
        if s.get('type') == 75 and PIC[s['props'][0x104]] in ('supplier', 'buyer', 'document'):
            name = PIC[s['props'][0x104]]
            if name not in out:
                t, l, r, b = s['anchor']; out[name] = (l * U, t * U, r * U, b * U)
    return out

def register(n):
    png = cv2.imread(os.path.join(ART, FIGURES[n] + '.png'), 0)
    R = cv2.imread(slide_png(n), 0)
    q = 3
    Pq = cv2.resize(png, (png.shape[1] // q, png.shape[0] // q), interpolation=cv2.INTER_AREA)
    found = {}
    for name, (x0, y0, x1, y1) in landmarks(n).items():
        tpl = R[int(y0):int(y1), int(x0):int(x1)]
        best = None
        def at(s):
            t = cv2.resize(tpl, (max(8, int(tpl.shape[1] * s)), max(8, int(tpl.shape[0] * s))), interpolation=cv2.INTER_AREA)
            if t.shape[0] >= Pq.shape[0] or t.shape[1] >= Pq.shape[1]: return None
            m = cv2.matchTemplate(Pq, t, cv2.TM_CCOEFF_NORMED)
            _, v, _, loc = cv2.minMaxLoc(m)
            return (v, s * q, loc[0] * q, loc[1] * q)
        for s in np.arange(2.6, 4.6, 0.05) / q:
            t = cv2.resize(tpl, (max(8, int(tpl.shape[1] * s)), max(8, int(tpl.shape[0] * s))), interpolation=cv2.INTER_AREA)
            if t.shape[0] >= Pq.shape[0] or t.shape[1] >= Pq.shape[1]: continue
            m = cv2.matchTemplate(Pq, t, cv2.TM_CCOEFF_NORMED)
            _, v, _, loc = cv2.minMaxLoc(m)
            if best is None or v > best[0]: best = (v, s * q, loc[0] * q, loc[1] * q)
        # then finer, at full resolution, round the best
        s0 = best[1]
        tplf = tpl
        bestf = None
        for s in np.arange(s0 - 0.06, s0 + 0.061, 0.005):
            t = cv2.resize(tplf, (int(tplf.shape[1] * s), int(tplf.shape[0] * s)), interpolation=cv2.INTER_AREA)
            wx, wy = max(0, best[2] - 60), max(0, best[3] - 60)
            win = png[wy:wy + t.shape[0] + 120, wx:wx + t.shape[1] + 120]
            if win.shape[0] < t.shape[0] or win.shape[1] < t.shape[1]: continue
            m = cv2.matchTemplate(win, t, cv2.TM_CCOEFF_NORMED)
            _, v, _, loc = cv2.minMaxLoc(m)
            if bestf is None or v > bestf[0]: bestf = (v, s, wx + loc[0], wy + loc[1])
        v, s, px, py = bestf
        found[name] = dict(score=round(float(v), 3), scale=round(float(s), 4), slide=(x0, y0), png=(px, py))
    # scale and shift from supplier and buyer, checked on the document
    a, b = found['supplier'], found['buyer']
    s = (b['png'][0] - a['png'][0]) / (b['slide'][0] - a['slide'][0])
    dx = a['png'][0] - s * a['slide'][0]; dy = a['png'][1] - s * a['slide'][1]
    c = found['document']
    check = (c['png'][0] - (s * c['slide'][0] + dx), c['png'][1] - (s * c['slide'][1] + dy))
    return dict(scale=float(s), dx=float(dx), dy=float(dy), check_px=[round(float(v), 1) for v in check], found=found,
                png=[png.shape[1], png.shape[0]])

if __name__ == '__main__':
    res = {}
    for n in (2, 3, 4, 5):
        res[n] = register(n)
        r = res[n]
        print(n, 'scale %.4f  shift %.1f, %.1f  document off by %s px' % (r['scale'], r['dx'], r['dy'], r['check_px']),
              {k: (v['score'], v['scale']) for k, v in r['found'].items()})

