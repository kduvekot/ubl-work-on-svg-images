"""Where a Group B drawing's pieces lie against the UBL PNG it is drawn from: the export, put where the PNG has its
ink (as history/group-a/compare_png.py does), is held against the PNG in windows, and the shift that fits best is
printed for each ((dx, dy) in PNG px: how far the export lies right of / below the PNG's ink).

    python3 history/group-b/align.py <ubl>/art <export>/art <figure> x0,y0,x1,y1[,name] ...
"""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'group-a'))
from compare_png import ink, fit  # noqa: E402


def best_shift(o, w, box, reach=40):
    x0, y0, x1, y1 = box
    a = o[y0:y1, x0:x1].astype(np.float32)
    best = (-1, 0, 0)
    for dy in range(-reach, reach + 1, 2):
        for dx in range(-reach, reach + 1, 2):
            ys, ye, xs, xe = y0 + dy, y1 + dy, x0 + dx, x1 + dx
            if ys < 0 or xs < 0 or ye > w.shape[0] or xe > w.shape[1]:
                continue
            s = float((a * w[ys:ye, xs:xe]).sum())
            if s > best[0]:
                best = (s, dx, dy)
    # refine to 1 px
    _, bx, by = best
    for dy in range(by - 1, by + 2):
        for dx in range(bx - 1, bx + 2):
            ys, ye, xs, xe = y0 + dy, y1 + dy, x0 + dx, x1 + dx
            s = float((a * w[ys:ye, xs:xe]).sum())
            if s > best[0]:
                best = (s, dx, dy)
    return best[1], best[2]


def main(a):
    orig, ours, name = a[:3]
    o = ink(os.path.join(orig, name + '.png'))
    w = ink(os.path.join(ours, name + '.png'), (o.shape[1], o.shape[0]))
    w = fit(o, w)
    for spec in a[3:]:
        p = spec.split(',')
        box = tuple(int(v) for v in p[:4])
        dx, dy = best_shift(o, w, box)
        print('%-28s export lies %+d px right, %+d px below the PNG' % (p[4] if len(p) > 4 else spec, dx, dy))


if __name__ == '__main__':
    main(sys.argv[1:])
