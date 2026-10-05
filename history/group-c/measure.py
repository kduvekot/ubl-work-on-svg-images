"""Measuring a UBL PNG (history/group-c): long straight strokes (box edges, rules, arrow shafts) and
text lines (ink grouped by dilation), in PNG px, so the build scripts can be written from numbers.

    python3 history/group-c/measure.py <png> lines [minlen]      horizontal and vertical runs
    python3 history/group-c/measure.py <png> text [x0,y0,x1,y1]  text-line candidates (ink boxes)
"""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi


def ink(path, thr=128):
    im = Image.open(path).convert('RGBA')
    bg = Image.new('RGBA', im.size, 'white')
    bg.alpha_composite(im)
    return np.asarray(bg.convert('L')) < thr


def runs(m, minlen):
    out = []
    for axis, name in ((1, 'H'), (0, 'V')):
        mm = m if axis == 1 else m.T
        for i in range(mm.shape[0]):
            row = np.concatenate([[0], mm[i].astype(np.int8), [0]])
            d = np.diff(row)
            for s, e in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
                if e - s >= minlen:
                    out.append((name, i, int(s), int(e)))
    # merge adjacent rows of the same extent into strokes
    strokes = []
    for name in 'HV':
        rs = sorted([r for r in out if r[0] == name], key=lambda r: (r[2], r[3], r[1]))
        cur = None
        for _, i, s, e in rs:
            if cur and abs(cur[2] - s) <= 3 and abs(cur[3] - e) <= 3 and i - cur[1] <= 1:
                cur[1] = i
                cur[4] += 1
            else:
                if cur:
                    strokes.append(cur)
                cur = [name, i, s, e, 1, i]
            # cur = name, last row, start, end, thickness, first row
        if cur:
            strokes.append(cur)
    return strokes


def main():
    p, mode = sys.argv[1], sys.argv[2]
    m = ink(p)
    if mode == 'lines':
        minlen = int(sys.argv[3]) if len(sys.argv) > 3 else 200
        for name, last, s, e, th, first in sorted(runs(m, minlen), key=lambda r: (r[0], r[5], r[2])):
            print('%s  across %d-%d (centre %.1f, %d thick)  along %d-%d  (len %d)' % (name, first, last, (first + last) / 2, th, s, e, e - s))
    else:
        if len(sys.argv) > 3:
            x0, y0, x1, y1 = map(int, sys.argv[3].split(','))
        else:
            x0, y0, x1, y1 = 0, 0, m.shape[1], m.shape[0]
        sub = m[y0:y1, x0:x1]
        dil = ndi.binary_dilation(sub, np.ones((9, 45)))
        lab, nl = ndi.label(dil)
        for i, sl in enumerate(ndi.find_objects(lab), 1):
            comp = sub[sl] & (lab[sl] == i)
            ys, xs = np.where(comp)
            h = ys.max() - ys.min() + 1
            w = xs.max() - xs.min() + 1
            print('ink x %d-%d y %d-%d  (%d x %d)' % (x0 + sl[1].start + xs.min(), x0 + sl[1].start + xs.max(), y0 + sl[0].start + ys.min(), y0 + sl[0].start + ys.max(), w, h))


main()
