"""lines.py <png> [x0,y0,x1,y1]: the text lines of a figure, in PNG px: ink components smaller than a letter's
size (so not the strokes of boxes and arrows), grouped into lines (same baseline band, near in x). Prints per
line: ink x range, ink top (y0) and bottom (y1), and the height of its tallest capital-ish part."""
import sys
import numpy as np
from scipy import ndimage as ndi
a = sys.argv[1:]
sys.argv = sys.argv[:1]
exec(open('history/group-c/measure.py').read().replace('\nmain()\n', '\n'))
m = ink(a[0])
x0, y0, x1, y1 = (map(int, a[1].split(','))) if len(a) > 1 else (12, 12, m.shape[1] - 12, m.shape[0] - 12)
lab, n = ndi.label(m, np.ones((3, 3)))
keep = np.zeros_like(m)
for i, sl in enumerate(ndi.find_objects(lab), 1):
    h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
    if h < 110 and w < 110:
        keep[sl] |= (lab[sl] == i)
keep[:y0] = 0; keep[y1:] = 0; keep[:, :x0] = 0; keep[:, x1:] = 0
lab, n = ndi.label(ndi.binary_dilation(keep, np.ones((3, 60))))
res = []
for i, sl in enumerate(ndi.find_objects(lab), 1):
    comp = keep[sl] & (lab[sl] == i)
    ys, xs = np.where(comp)
    if len(ys) < 40:
        continue
    res.append((sl[0].start + ys.min(), sl[0].start + ys.max(), sl[1].start + xs.min(), sl[1].start + xs.max(), len(ys)))
for y_0, y_1, x_0, x_1, c in sorted(res):
    print('y %4d-%4d  x %4d-%4d  (h %d, w %d)' % (y_0, y_1, x_0, x_1, y_1 - y_0 + 1, x_1 - x_0 + 1))
