# Fits a Fulfilment drawing to its UBL PNG: the slide gives the parts, texts
# and styles; the PNG where each is. Each shape is rendered on its own at the
# figure's scale and found in the PNG near where the slide puts it (template
# matching (a pallet by the photo, as the PNGs have it), sizes 50-140% for pictures
# with their aspect 80-125%, 85-115% for texts, 60-160% for the title, 70-130% for arrows); a picture not found is one the figure does not
# show (the slides are animated). Writes the drawing, diagrams/<fig>/<fig>.drawio
# (its origin at the frame's outer corner, so that a PNG px is a drawing px
# times ubl-png-scale), and <WORK>/fit/<fig>.json (what was found where, in the
# slide's px: PNG px = slide px * scale + dx, dy).
#
#   python3 fit.py <slide 2..5>
import sys, os, json, subprocess, math
import numpy as np, cv2
from build import build, shapes_of, U, PIC
from register import register, node_env
from paths import ART, FIGURES, HERE, ROOT, work

n = int(sys.argv[1]); fig = FIGURES[n]
png = cv2.imread(os.path.join(ART, fig + '.png'), 0)
PH, PW = png.shape
reg = register(n)
doc = reg['found']['document']
S = doc['scale']                                          # slide px -> PNG px
DX, DY = doc['png'][0] - S * doc['slide'][0], doc['png'][1] - S * doc['slide'][1]
M = 24                                                    # margin round each render, PNG px

shapes = shapes_of(n)
def box(k):
    s = shapes[k]; t, l, r, b = s['anchor']
    return l * U, t * U, (r - l) * U, (b - t) * U

jobs = []
for k, s in enumerate(shapes):
    x, y, w, h = box(k)
    pad = 12 if s.get('type') == 20 else 0                # a line's arrowhead reaches out
    jobs.append(dict(xml=build(n, only={k}, photo=True), out=work('el', fig, '%02d.png' % k),
                     w=(w + 2 * pad) * S + 2 * M, h=(h + 2 * pad) * S + 2 * M, s=S,
                     dx=M - (x - pad) * S, dy=M - (y - pad) * S))
json.dump(jobs, open(work('el', fig, 'jobs.json'), 'w'))
env = node_env()
subprocess.run(['node', os.path.join(HERE, 'render_many.js'), work('el', fig, 'jobs.json')], check=True, env=env)

R0 = 260                                                  # search radius, PNG px
res = {}
for k, (s, j) in enumerate(zip(shapes, jobs)):
    t = cv2.imread(j['out'], 0)
    if t is None or (t < 200).sum() < 20:
        continue
    # the template: the render cropped to its ink (so a wide text box does not
    # make it wider than its words), cx, cy its corner in the render
    ys, xs = np.nonzero(t < 200)
    cx, cy = max(0, xs.min() - 4), max(0, ys.min() - 4)
    t = t[cy:ys.max() + 5, cx:xs.max() + 5]
    kind = {75: 'picture', 20: 'line'}.get(s.get('type'), 'text')
    ex, ey = -j['dx'] + DX + cx, -j['dy'] + DY + cy        # the template's corner in PNG px, as predicted
    best = None
    title = s.get('type') == 1
    rng = (np.arange(0.5, 1.401, 0.025) if kind == 'picture' else np.arange(0.6, 1.601, 0.02) if title
           else np.arange(0.85, 1.151, 0.025) if kind == 'text' else np.arange(0.7, 1.301, 0.05))
    for R in ((R0,) if kind != 'text' else (R0, 3 * R0)):
        if R > R0 and best and best[0] >= 0.5: break      # a text not found near: look wider
        for sc in rng:
            tt = cv2.resize(t, (max(4, round(t.shape[1] * sc)), max(4, round(t.shape[0] * sc))), interpolation=cv2.INTER_AREA)
            x0, y0 = int(max(0, ex - R)), int(max(0, ey - R))
            x1, y1 = int(min(PW, ex + R + tt.shape[1])), int(min(PH, ey + R + tt.shape[0]))
            win = png[y0:y1, x0:x1]
            if win.shape[0] < tt.shape[0] or win.shape[1] < tt.shape[1]: continue
            m = cv2.matchTemplate(win, tt, cv2.TM_CCOEFF_NORMED)
            _, v, _, loc = cv2.minMaxLoc(m)
            if best is None or v > best[0]:
                best = (float(v), float(sc), x0 + loc[0], y0 + loc[1])
    if best is None: continue
    v, sc, lx, ly = best
    asp = 1.0
    if kind == 'picture':   # then its aspect: a picture may have been stretched
        for a in np.arange(0.8, 1.251, 0.025):
            sx, sy = sc * a ** 0.5, sc / a ** 0.5
            tt = cv2.resize(t, (max(4, round(t.shape[1] * sx)), max(4, round(t.shape[0] * sy))), interpolation=cv2.INTER_AREA)
            x0, y0 = int(max(0, lx - 60)), int(max(0, ly - 60))
            win = png[y0:y0 + tt.shape[0] + 120, x0:x0 + tt.shape[1] + 120]
            if win.shape[0] < tt.shape[0] or win.shape[1] < tt.shape[1]: continue
            m = cv2.matchTemplate(win, tt, cv2.TM_CCOEFF_NORMED)
            _, vv, _, loc = cv2.minMaxLoc(m)
            if vv > v: v, asp, lx, ly = float(vv), float(a), x0 + loc[0], y0 + loc[1]
    # the shape's own corner in the PNG, and so in the drawing's units
    x, y, w, h = box(k)
    pad = 12 if kind == 'line' else 0
    sx, sy = sc * asp ** 0.5, sc / asp ** 0.5
    px, py = lx + (M + pad * S - cx) * sx, ly + (M + pad * S - cy) * sy
    res[k] = dict(kind=kind, part=PIC.get(s['props'].get(0x104)) if kind == 'picture' else None,
                  text=s['text'], score=round(v, 3), scale=round(sc, 3),
                  moved=[round((px - DX) / S - x, 1), round((py - DY) / S - y, 1)],
                  aspect=round(asp, 3), geom=[(px - DX) / S, (py - DY) / S, w * sx, h * sy])

# a box (a text with a border): its geometry from the border lines in the PNG
def border(k):
    s = shapes[k]
    gx, gy, gw, gh = res[k]['geom']
    from build import text_width, PT
    paras, chars = __import__('build').text_style(s.get('style', b''), s['text'])
    pt = next((c[1] for c in chars if c[1]), None); bold = any(c[2] for c in chars)
    lines = s['text'].split('\r')
    w = max(text_width(l, pt * PT, bold) for l in lines) + 2 * 9.6
    h = len(lines) * 1.2 * pt * PT + 2 * 4.8
    X0, Y0, X1, Y1 = gx * S + DX, gy * S + DY, (gx + w) * S + DX, (gy + h) * S + DY
    pad, pr_ = 30, 120        # a box may be wider than its text: on the right, look further
    win = png[int(Y0 - pad):int(Y1 + pad), int(X0 - pad):int(X1 + pr_)] < 128
    inner = win[:, pad + 20:-(pr_ + 20)]; rows = inner.mean(1)
    innv = win[pad + 10:-(pad + 10), :]; cols = innv.mean(0)
    def edge(prof, lo, hi):
        idx = [i for i in range(lo, hi) if prof[i] > 0.35]
        if not idx: return None
        runs, cur = [], [idx[0]]
        for i in idx[1:]:
            if i == cur[-1] + 1: cur.append(i)
            else: runs.append(cur); cur = [i]
        runs.append(cur)
        return runs
    top = edge(rows, 0, 2 * pad); bot = edge(rows, len(rows) - 2 * pad, len(rows))
    lef = edge(cols, 0, 2 * pad); rig = edge(cols, len(cols) - pad - pr_, len(cols))
    if not (top and bot and lef and rig): return None
    mid = lambda r: (r[0] + r[-1]) / 2
    t, b = mid(top[0]), mid(bot[-1]); l, r = mid(lef[0]), mid(rig[0])   # the right edge: the first line out from the text
    ox, oy = X0 - pad, Y0 - pad
    return [(ox + l - DX) / S, (oy + t - DY) / S, (r - l) / S, (b - t) / S]
# and where its text is in it: the text, drawn with Arial's metrics (Liberation
# Sans), found inside the box; its left from the box's left, in the drawing's px
from PIL import Image, ImageDraw, ImageFont
def text_in_box(k):
    s = shapes[k]
    from build import PT, _FONT
    paras, chars = __import__('build').text_style(s.get('style', b''), s['text'])
    pt = next((c[1] for c in chars if c[1]), None); bold = any(c[2] for c in chars)
    line = s['text'].split('\r')[0]
    gx, gy, gw, gh = res[k]['geom']
    X0, Y0 = int(gx * S + DX + 4), int(gy * S + DY + 4)
    win = png[Y0:int(Y0 + gh * S - 8), X0:int(X0 + gw * S - 8)]
    best = None
    for f_ in np.arange(0.9, 1.41, 0.02):           # and its size
        font = ImageFont.truetype(_FONT % ('Bold' if bold else 'Regular'), round(pt * PT * S * f_))
        l, t, r, b = font.getbbox(line)
        im = Image.new('L', (r + 20, b + 20), 255); ImageDraw.Draw(im).text((10, 10), line, font=font, fill=0)
        tpl = np.array(im)[10 + t - 2:10 + b + 2, 10 + l - 2:10 + r + 2]
        if win.shape[0] < tpl.shape[0] or win.shape[1] < tpl.shape[1]: break
        m = cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED)
        _, v, _, loc = cv2.minMaxLoc(m)
        if best is None or v > best[0]: best = (v, f_, loc, l)
    if best is None or best[0] < 0.5: return None
    v, f_, loc, l = best
    res[k]['text_size'] = float(f_)
    ink_left = X0 + loc[0] + 2                       # the text's ink, its left, PNG px
    return (ink_left - (gx * S + DX)) / S - l / S    # less the first letter's bearing
for k in list(res):
    s = shapes[k]
    if res[k]['kind'] == 'text' and s['props'].get(0x1ff, 0) & 0x8 and s.get('type') != 1:
        g = border(k)
        if g:
            res[k]['geom'] = g; res[k]['border'] = True
            tx = text_in_box(k)
            if tx is not None: res[k]['text_left'] = tx

# a solid arrow: its tip from the PNG. Along the line as fitted, the band of
# its width; its ink from where it starts to where it stops (a dotted line's
# gaps bridged), the arrowhead's tip at PowerPoint's start
def ends(k):
    s = shapes[k]; pr = s['props']; fl = s['flags']
    t_, l_, r_, b_ = s['anchor']
    sx, ex = (r_, l_) if fl & 0x40 else (l_, r_)
    sy, ey = (b_, t_) if fl & 0x80 else (t_, b_)
    ox, oy = res[k]['moved']
    P0 = np.array([sx * U + ox, sy * U + oy]) * S + [DX, DY]      # the tip, PNG px
    P1 = np.array([ex * U + ox, ey * U + oy]) * S + [DX, DY]      # the tail
    d = P1 - P0; L = np.linalg.norm(d); d = d / L; nrm = np.array([-d[1], d[0]])
    wpx = pr.get(0x1cb, 9525) / 12700 * 96 / 72 * S
    dotted = pr.get(0x1ce, 0) == 2
    def inkline(off, ts, half):
        out = []
        for t in ts:
            c = P0 + d * t + nrm * off
            pts = [c + nrm * o for o in np.linspace(-half, half, 5)]
            v = [png[int(round(p[1])), int(round(p[0]))] < 128 if 0 <= round(p[0]) < PW and 0 <= round(p[1]) < PH else False for p in pts]
            out.append(sum(v) >= 4)
        return np.array(out)
    # its direction: a straight line through the middles of its ink across it
    cen = []
    for t in np.arange(0.1 * L, 0.9 * L, max(4.0, L / 40)):
        c = P0 + d * t
        prof = []
        for o in range(-40, 41):
            p = c + nrm * o
            prof.append(0 <= round(p[0]) < PW and 0 <= round(p[1]) < PH and png[int(round(p[1])), int(round(p[0]))] < 128)
        runs_, st_ = [], None
        for i, v in enumerate(prof + [False]):
            if v and st_ is None: st_ = i
            if not v and st_ is not None: runs_.append((st_, i - 1)); st_ = None
        runs_ = [r for r in runs_ if 0.8 * wpx <= r[1] - r[0] + 1 <= 1.3 * wpx and abs((r[0] + r[1]) / 2 - 40) <= 20]
        if runs_:
            r = min(runs_, key=lambda r: abs((r[0] + r[1]) / 2 - 40))
            cen.append(c + nrm * ((r[0] + r[1]) / 2 - 40))
    if len(cen) >= 5:
        C = np.array(cen); m0 = C.mean(0)
        _, sv, vt = np.linalg.svd(C - m0); u = vt[0]
        spread = sv[1] / len(C) ** 0.5                 # how far the middles lie off the line
        if np.dot(u, d) < 0: u = -u
        if np.dot(u, d) > 0.98 and spread < 2.5:   # a small correction, and a straight line only
            P0 = m0 + u * np.dot(P0 - m0, u); P1 = m0 + u * np.dot(P1 - m0, u)
            d = u; nrm = np.array([-d[1], d[0]]); L = np.linalg.norm(P1 - P0)
    # the line's exact offset sideways: where the most ink is along it
    inner = np.arange(0.15 * L, 0.85 * L, 2)
    off = max(np.arange(-24, 25, 2), key=lambda o: inkline(o, inner, wpx * 0.3).sum())
    P0 = P0 + nrm * off
    ts = np.arange(-0.15 * L, 1.15 * L)
    ink = inkline(0, ts, wpx * 0.3)
    gap = int(2.2 * 2 * wpx) if dotted else int(0.6 * wpx)
    # the runs of ink, gaps up to `gap` bridged; the one overlapping the line most
    runs, start, last = [], None, None
    for i, v in enumerate(ink):
        if v:
            if start is None: start = i
            elif i - last > gap + 1: runs.append((start, last)); start = i
            last = i
    if start is not None: runs.append((start, last))
    if not runs: return None
    i0, i1 = np.searchsorted(ts, 0), np.searchsorted(ts, L)
    # the tip: the tip-side end of the run nearest the predicted tip (the
    # line's middle may be hidden, under a box); the tail stays as fitted
    near = [r for r in runs if r[1] - r[0] >= 2 * wpx and abs(r[0] - i0) < 0.4 * (i1 - i0)]
    if not near: return None
    lo, hi = min(near, key=lambda r: abs(r[0] - i0))
    tip, tail = P0 + d * ts[lo], P1 + nrm * off
    if hi - lo >= 0.6 * (i1 - i0):                 # most of it shows: its tail too
        tail = P0 + d * ts[hi]
    return [((tip - [DX, DY]) / S).tolist(), ((tail - [DX, DY]) / S).tolist()]
for k in list(res):
    # a solid arrow: its ends from the PNG. A dotted one keeps its fit: its dots
    # count from PowerPoint's end point, which its arrowhead's tip is beyond
    if res[k]['kind'] == 'line' and shapes[k]['props'].get(0x1ce, 0) != 2:
        e = ends(k)
        if e: res[k]['ends'] = e

# what the figure has that the slide has not: a second SHIPMENT box, its dotted
# arrow and its document, between the forwarders (Consolidated). Each a copy of
# the slide's own shape, placed where the PNG has it
import copy
extra = []
def add(src, geom):
    s = copy.deepcopy(shapes[src]); k = len(shapes)
    shapes.append(s); extra.append(s)
    res[k] = dict(res[src]); res[k]['geom'] = geom; res[k]['extra_of'] = src
    return k
def found_elsewhere(src, scales, known, min_score):
    j = jobs[src]
    t = cv2.imread(j['out'], 0)
    ys, xs = np.nonzero(t < 200); cx, cy = max(0, xs.min() - 4), max(0, ys.min() - 4)
    t = t[cy:ys.max() + 5, cx:xs.max() + 5]
    x, y, w, h = box(src)
    best = None
    for sc in scales:
        tt = cv2.resize(t, (round(t.shape[1] * sc), round(t.shape[0] * sc)), interpolation=cv2.INTER_AREA)
        m = cv2.matchTemplate(png, tt, cv2.TM_CCOEFF_NORMED)
        for kk in known:                       # not where a known one is
            kx, ky = res[kk]['geom'][0] * S + DX, res[kk]['geom'][1] * S + DY
            m[max(0, int(ky - M - 150)):int(ky + 150), max(0, int(kx - M - 150)):int(kx + 150)] = -1
        _, v, _, loc = cv2.minMaxLoc(m)
        if best is None or v > best[0]: best = (v, sc, loc)
    v, sc, (lx, ly) = best
    if v < min_score: return None
    px, py = lx + (M - cx) * sc, ly + (M - cy) * sc
    return [(px - DX) / S, (py - DY) / S, w * sc, h * sc], v
if n == 5:
    ship = [k for k in res if res[k]['kind'] == 'text' and (shapes[k]['text'] or '') == 'SHIPMENT']
    docs = [k for k in res if res[k].get('part') == 'document']
    dots = [k for k in res if res[k]['kind'] == 'line' and shapes[k]['props'].get(0x1ce, 0) == 2]
    # (its text is larger than the others', so its box matches less well)
    g = found_elsewhere(ship[0], np.arange(0.9, 1.11, 0.02), ship, 0.45)
    if g:
        kl = add(dots[0], None)                  # the arrow first: the box covers it
        k = add(ship[0], g[0])
        b = border(k)
        if b: res[k]['geom'] = b
        tx = text_in_box(k)
        if tx is not None: res[k]['text_left'] = tx
        print('added: a SHIPMENT box (score %.2f)' % g[1])
        # its dotted arrow: along the box's middle row, the dots out of it both ways
        bx, by, bw, bh = res[k]['geom']
        wpx = shapes[dots[0]]['props'].get(0x1cb, 9525) / 12700 * 96 / 72 * S
        # the row of its dots: where most ink is just right of the box
        xr = int((bx + bw) * S + DX)
        rows = range(int(by * S + DY), int((by + bh) * S + DY) + int(wpx))
        row = max(rows, key=lambda r: (png[r, xr + 10:xr + 300] < 128).sum())
        prof = (png[row - int(wpx * 0.3):row + int(wpx * 0.3) + 1] < 128).mean(0) > 0.8
        gap = int(1.5 * wpx)                     # the dots are a line's width apart
        def walk(x, step):
            last = x
            while 0 <= x < PW and abs(x - last) <= gap:
                if prof[x]: last = x
                x += step
            return last
        left = walk(int(bx * S + DX) - 6, -1); right = walk(int((bx + bw) * S + DX) + 6, 1)
        res[kl]['geom'] = None
        res[kl]['ends'] = [[(right - DX) / S, (row - DY) / S], [(left - DX) / S, (row - DY) / S]]
        print('added: its dotted arrow, from x %d to %d px' % (left, right))
    g = found_elsewhere(docs[0], np.arange(0.6, 1.01, 0.025), docs, 0.6)
    if g:
        add(docs[0], g[0]); print('added: a document (score %.2f, size %.0f%%)' % (g[1], 100 * g[0][2] / box(docs[0])[2]))

# which pictures the figure shows: found well, and not where a better match of
# the same part already is
shown = set(range(len(shapes) - len(extra), len(shapes))) if extra else set()
for k in sorted(res, key=lambda k: -res[k]['score']):
    r = res[k]
    if r['kind'] != 'picture':
        shown.add(k)   # every text and arrow is in the figure
        continue
    if r['score'] < (0.6 if r['part'] == 'pallet' else 0.5): continue
    gx, gy, gw, gh = r['geom']
    # the same part found where another already is: the same picture twice
    clash = any(res[j]['kind'] == 'picture' and res[j]['part'] == r['part'] and
                abs(res[j]['geom'][0] - gx) < gw / 5 and abs(res[j]['geom'][1] - gy) < gh / 5 for j in shown)
    if not clash: shown.add(k)
for k in sorted(res):
    r = res[k]
    print('%2d %-8s %-15s %-26s score %.2f size %3.0f%% moved %6.1f,%6.1f px %s' % (
        k, r['kind'], r['part'] or '', repr((r['text'] or '')[:24]), r['score'], 100 * r['scale'], *r['moved'],
        '' if k in shown else '  -- not in the figure'))

# an arrow whose ends were not taken from the PNG: slid to where it overlaps the
# PNG's ink best (rendered alone on the PNG's canvas, shifted up to 80 px)
pngink = (png < 128).astype(np.float32)
for k in sorted(shown):
    if res[k]['kind'] != 'line' or 'ends' in res[k] or k >= len(shapes) - len(extra): continue
    open(work('fit', 'one.drawio'), 'w').write(build(n, only={k}, geom={k: tuple(res[k]['moved'])}))
    subprocess.run(['node', os.path.join(HERE, 'render.js'), work('fit', 'one.drawio'), work('fit', 'one.png'),
                    str(PW), str(PH), str(S), str(DX), str(DY)], check=True, env=env)
    a = (cv2.imread(work('fit', 'one.png'), 0) < 128).astype(np.float32)
    ys, xs = np.nonzero(a)
    if not len(xs): continue
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    Rs = 80
    win = pngink[max(0, y0 - Rs):y1 + Rs, max(0, x0 - Rs):x1 + Rs]
    m = cv2.matchTemplate(win, a[y0:y1, x0:x1], cv2.TM_CCORR_NORMED)
    _, v, _, loc = cv2.minMaxLoc(m)
    sx, sy = loc[0] - (x0 - max(0, x0 - Rs)), loc[1] - (y0 - max(0, y0 - Rs))
    res[k]['moved'] = [res[k]['moved'][0] + sx / S, res[k]['moved'][1] + sy / S]
    res[k]['slid_png'] = [int(sx), int(sy)]
    print('slid arrow %d by %d, %d px' % (k, sx, sy))

geom = {k: (tuple(res[k]['geom']) if res[k]['kind'] != 'line' else
            ('ends', *res[k]['ends']) if 'ends' in res[k] else tuple(res[k]['moved'])) for k in shown}
sizes = {}
for k in shown:
    if res[k]['kind'] == 'text':
        from build import text_style
        s = shapes[k]
        paras, chars = text_style(s.get('style', b''), s['text']) if s.get('style') else ([], [])
        pt = next((c[1] for c in chars if c[1]), None) or 32
        sizes[k] = pt * res[k].get('text_size', res[k]['scale'])
hide = set(range(len(shapes))) - shown
fw = 11 / S                                               # the frame: the PNG's border, 11 px
frame = [(5.5 - DX) / S, (5.5 - DY) / S, (PW - 5.5 - DX) / S, (PH - 5.5 - DY) / S, fw]
text_left = {k: res[k]['text_left'] for k in shown if 'text_left' in res[k]}
out = os.path.join(ROOT, 'diagrams', fig, fig + '.drawio')
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, 'w').write(build(n, frame=frame, hide=hide, geom=geom, sizes=sizes, text_left=text_left, extra=extra,
                           origin=(DX / S, DY / S), name=fig, page=(math.ceil(PW / S), math.ceil(PH / S)), scale=S))
json.dump(dict(scale=S, dx=DX, dy=DY, png=[PW, PH], shapes=res, shown=sorted(shown)),
          open(work('fit', fig + '.json'), 'w'), indent=1)
print(fig, 'scale %.4f, shift %.1f, %.1f; %d of %d shapes shown' % (S, DX, DY, len(shown), len(shapes)))
