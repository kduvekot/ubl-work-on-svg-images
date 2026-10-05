"""Where each picture of Steps3-4-5 is in the UBL 2.2 PNG: each part rendered and matched (grey, normalised
correlation) over its size and aspect, near where the PNG's ink has it. Writes parts_fit.json:
{instance: [x, y, width, height]} in the PNG's px (steps345.py divides them by its scale).

    UBL=<clone of oasis-tcs/ubl, branch ubl-2.5> python3 history/illustrations/cpfr/parts_fit.py

The five documents are one picture: parts_fit.json keeps their median size, each at the top the ink has.
"""
import io, json, os, statistics
import cairosvg, cv2, numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
UBL = os.environ.get('UBL') or os.path.join(os.path.dirname(ROOT), 'ubl')
PARTS = os.path.join(ROOT, 'illustrations', 'parts')
png = np.asarray(Image.open(os.path.join(UBL, 'art', 'UBL-2.2-CPFR-Steps3-4-5.png')).convert('L')).astype(np.float32)

def render(part, w, h, flip=False):
    im = Image.open(io.BytesIO(cairosvg.svg2png(url=os.path.join(PARTS, part + '.svg'), output_width=int(w), output_height=int(h)))).convert('RGBA')
    bg = Image.new('RGBA', im.size, 'white'); bg.alpha_composite(im)
    a = np.asarray(bg.convert('L')).astype(np.float32); al = np.asarray(im)[..., 3] > 40
    return (a[:, ::-1], al[:, ::-1]) if flip else (a, al)

def fit(part, box, aspect, flip=False):
    x0, y0, x1, y1 = box; best = None
    for h in np.arange((y1 - y0) * 0.85, (y1 - y0) * 1.25, 1.0):
        for asp in (aspect * 0.94, aspect * 0.97, aspect, aspect * 1.03, aspect * 1.06):
            t, al = render(part, h * asp, h, flip)
            reg = png[int(y0 - 25):int(y1 + 25), int(x0 - 25):int(x1 + 25)]
            if reg.shape[0] < t.shape[0] or reg.shape[1] < t.shape[1]:
                continue
            _, v, _, loc = cv2.minMaxLoc(cv2.matchTemplate(reg, t, cv2.TM_CCORR_NORMED, mask=al.astype(np.float32)))
            if best is None or v > best[0]:
                best = (v, x0 - 25 + loc[0], y0 - 25 + loc[1], h * asp, h)
    return [float(v) for v in best[1:]]

tops = [141, 438, 758, 1085, 1377]          # the documents' top-left corners, from the ink (less 1 px)
docs = [fit('cpfr-document', (378, t + 1, 443, t + 133), 169 / 327) for t in tops]
w, h = statistics.median(d[2] for d in docs), statistics.median(d[3] for d in docs)
out = {'doc%d' % (i + 1): [376.0, t, w, h] for i, t in enumerate(tops)}
out['clipboard'] = fit('cpfr-exception', (1254, 159, 1331, 331), 159 / 342)
out['desk-left'] = fit('cpfr-person-at-desk', (969, 850, 1146, 1030), 350 / 327)
out['desk-right'] = fit('cpfr-person-at-desk', (1451, 850, 1629, 1030), 350 / 327, flip=True)
json.dump(out, open(os.path.join(HERE, 'parts_fit.json'), 'w'), indent=1)
for k, v in out.items():
    print(k, [round(x, 1) for x in v])
