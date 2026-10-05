"""Where each picture of the CPFR step figures is in its UBL 2.2 PNG: each part rendered and matched (grey,
normalised correlation) over its size and aspect, near where the PNG has it. The documents of a figure are
one picture: they get one size (the median of their fits), each placed again at that size. Writes
parts_fit.json: {figure: {instance: [x, y, width, height]}} in the PNG's px.

    UBL=<clone of oasis-tcs/ubl, branch ubl-2.5> python3 history/illustrations/cpfr/parts_fit.py [<figure> ...]
"""
import io, json, os, statistics, sys
import cairosvg, cv2, numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
UBL = os.environ.get('UBL') or os.path.join(os.path.dirname(ROOT), 'ubl')
PARTS = os.path.join(ROOT, 'illustrations', 'parts')
ASPECT = {'cpfr-document': 169 / 327, 'cpfr-exception': 159 / 342, 'cpfr-person-at-desk': 350 / 327,
          'cpfr-meeting': 561 / 595, 'cpfr-agreement': 403 / 477}
# per figure: instance -> (part, rough box in the PNG, mirrored)
D = 'cpfr-document'
FIGURES = {
 'UBL-2.2-CPFR-Steps1-2': dict(
    meeting=('cpfr-meeting', (245, 124, 466, 357), False), agreement=('cpfr-agreement', (286, 534, 443, 717), False),
    **{'doc%d' % (i + 1): (D, b, False) for i, b in enumerate(
        [(358, t, 421, t + 125) for t in (854, 1138, 1444, 1737)] + [(1282, t, 1345, t + 125) for t in (149, 437, 1036, 1344)])}),
 'UBL-2.2-CPFR-Steps3-4-5': dict(
    clipboard=('cpfr-exception', (1254, 159, 1331, 331), False),
    **{'desk-left': ('cpfr-person-at-desk', (969, 850, 1146, 1030), False), 'desk-right': ('cpfr-person-at-desk', (1451, 850, 1629, 1030), True)},
    **{'doc%d' % (i + 1): (D, (378, t + 1, 443, t + 133), False) for i, t in enumerate((141, 438, 758, 1085, 1377))}),
 'UBL-2.2-CPFR-Steps6-9': dict(
    clipboard1=('cpfr-exception', (831, 97, 881, 210), False), clipboard2=('cpfr-exception', (1405, 97, 1455, 210), False),
    **{'desk1-left': ('cpfr-person-at-desk', (643, 545, 760, 660), False), 'desk1-right': ('cpfr-person-at-desk', (955, 545, 1070, 660), True),
       'desk2-left': ('cpfr-person-at-desk', (1222, 547, 1336, 663), False), 'desk2-right': ('cpfr-person-at-desk', (1532, 547, 1646, 663), True)},
    **{'doc%d' % (i + 1): (D, b, False) for i, b in enumerate(
        [(259, t, 302, t + 85) for t in (93, 265, 441, 622, 804, 972)] + [(1408, 740, 1451, 825)])}),
}

def render(part, w, h, flip=False):
    im = Image.open(io.BytesIO(cairosvg.svg2png(url=os.path.join(PARTS, part + '.svg'), output_width=max(4, int(w)), output_height=max(4, int(h))))).convert('RGBA')
    bg = Image.new('RGBA', im.size, 'white'); bg.alpha_composite(im)
    a = np.asarray(bg.convert('L')).astype(np.float32); al = np.asarray(im)[..., 3] > 40
    return (a[:, ::-1], al[:, ::-1]) if flip else (a, al)

def fit(png, part, box, flip=False, size=None):
    x0, y0, x1, y1 = box; best = None; m = 25
    sizes = [size] if size else [(h * a, h) for h in np.arange((y1 - y0) * 0.85, (y1 - y0) * 1.25, 1.0)
                                 for a in [ASPECT[part] * k for k in (0.94, 0.97, 1, 1.03, 1.06)]]
    reg = png[int(y0 - m):int(y1 + m), int(x0 - m):int(x1 + m)]
    for w, h in sizes:
        t, al = render(part, w, h, flip)
        if reg.shape[0] < t.shape[0] or reg.shape[1] < t.shape[1]:
            continue
        _, v, _, loc = cv2.minMaxLoc(cv2.matchTemplate(reg, t, cv2.TM_CCORR_NORMED, mask=al.astype(np.float32)))
        if best is None or v > best[0]:
            best = (v, x0 - m + loc[0], y0 - m + loc[1], w, h)
    return [float(v) for v in best[1:]]

f = os.path.join(HERE, 'parts_fit.json')
out = json.load(open(f)) if os.path.exists(f) else {}
for name in sys.argv[1:] or FIGURES:
    png = np.asarray(Image.open(os.path.join(UBL, 'art', name + '.png')).convert('L')).astype(np.float32)
    got = {k: fit(png, p, b, fl) for k, (p, b, fl) in FIGURES[name].items()}
    docs = [k for k, (p, _, _) in FIGURES[name].items() if p == D]
    size = (statistics.median(got[k][2] for k in docs), statistics.median(got[k][3] for k in docs))
    for k in docs:
        got[k] = fit(png, D, FIGURES[name][k][1], size=size)
    out[name] = got
    for k, v in got.items():
        print(name, k, [round(x, 1) for x in v])
json.dump(out, open(f, 'w'), indent=1)
