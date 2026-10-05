"""How far an export is from the UBL PNG it replaces: the share of the PNG's ink with no ink of
the export within R px (at the PNG's size), and the other way round. Writes a red/blue image
(red: only in the PNG, blue: only in the export) next to the figure's name in <out>.

    python3 history/group-a/compare_png.py <ubl>/art <to-ubl-repo>/art <out> <figure> ...
"""
import os, sys
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation

R = 4


def ink(path, size=None):
    im = Image.open(path).convert('RGBA')
    bg = Image.new('RGBA', im.size, 'white')
    bg.alpha_composite(im)
    g = bg.convert('L')
    if size and g.size != size:
        g = g.resize(size, Image.LANCZOS)
    return np.asarray(g) < 128


def fit(o, w):
    """the export put where the PNG has its ink: both cropped to the ink's bounding box, the export
    scaled to the PNG's (the PNG has a margin of its own, which the export does not)"""
    def box(m):
        ys, xs = np.where(m)
        return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    ox0, oy0, ox1, oy1 = box(o)
    wx0, wy0, wx1, wy1 = box(w)
    crop = Image.fromarray((w[wy0:wy1, wx0:wx1] * 255).astype(np.uint8)).resize((ox1 - ox0, oy1 - oy0), Image.LANCZOS)
    out = np.zeros_like(o)
    out[oy0:oy1, ox0:ox1] = np.asarray(crop) >= 128
    print('  export scaled by %.4f x %.4f' % ((ox1 - ox0) / (wx1 - wx0), (oy1 - oy0) / (wy1 - wy0)))
    return out


def main(a):
    orig, ours, out = a[:3]
    os.makedirs(out, exist_ok=True)
    for name in a[3:]:
        o = ink(os.path.join(orig, name + '.png'))
        w = ink(os.path.join(ours, name + '.png'), (o.shape[1], o.shape[0]))
        w = fit(o, w)
        k = np.ones((2 * R + 1, 2 * R + 1), bool)
        only_o = o & ~binary_dilation(w, k)
        only_w = w & ~binary_dilation(o, k)
        img = np.full(o.shape + (3,), 255, np.uint8)
        img[o & w] = (0, 0, 0)
        img[o & ~w] = (255, 200, 200)
        img[w & ~o] = (200, 200, 255)
        img[only_o] = (255, 0, 0)
        img[only_w] = (0, 0, 255)
        Image.fromarray(img).save(os.path.join(out, name + '-diff.png'))
        print('%-45s png ink %d, only in png %.2f%%, only in export %.2f%%  (within %d px)' % (
            name, o.sum(), 100 * only_o.sum() / o.sum(), 100 * only_w.sum() / w.sum(), R))


if __name__ == '__main__':
    main(sys.argv[1:])
