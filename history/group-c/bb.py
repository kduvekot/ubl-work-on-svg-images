"""bb.py <png> x0,y0,x1,y1 ...: the ink's bounding box inside each window (PNG px)"""
import sys
import numpy as np
sys.argv, a = sys.argv[:1], sys.argv[1:]
exec(open('history/group-c/measure.py').read().replace('\nmain()\n', '\n'))
m = ink(a[0])
for w in a[1:]:
    x0, y0, x1, y1 = map(int, w.split(',')[:4])
    ys, xs = np.where(m[y0:y1, x0:x1])
    print(w, '-> x %d-%d y %d-%d' % (x0 + xs.min(), x0 + xs.max(), y0 + ys.min(), y0 + ys.max()))
