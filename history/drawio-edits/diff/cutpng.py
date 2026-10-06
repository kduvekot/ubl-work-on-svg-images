"""The original PNG with the same space inserted as in the drawing: at each
cut, in order, a line of pixels next to it (the one with the least ink) is
repeated to fill the inserted width, so lines crossing the cut (the frame, lane
dividers, flows) run on unbroken. Where the drawing kept a shape whole (it
stayed, or moved whole past the space), the cut steps round it. Then drawn
against the drawing as one.py does. Run insertions.py once, and one.py first
(its result.json gets these numbers added).

    python3 cutpng.py <figure> <out dir>     writes <out>/<figure>/*_cut*.png
"""
import json, os, re, subprocess, sys
import numpy as np
from PIL import Image
from scipy import ndimage
from common import ART, NODE, RENDER, ROOT, natural_width
n, out = sys.argv[1], sys.argv[2]
d = os.path.join(out, n); os.makedirs(d, exist_ok=True)
im = Image.open(f'{ART}/{n}.png')
if im.mode in ('RGBA', 'LA', 'P'):
    im = im.convert('RGBA'); bg = Image.new('RGBA', im.size, 'white'); bg.alpha_composite(im); im = bg
a = np.asarray(im.convert('RGB')).copy()
PW = a.shape[1]; R = max(1, round(2 * PW / 1480))
s = PW / natural_width(n)
M = int(re.search(r'ubl-offset="(\d+)"', open(f'{ROOT}/diagrams/{n}/{n}.drawio').read())[1])
ins = json.load(open(os.path.join(out, 'insertions.json'))).get(n, [])
marked = np.zeros(a.shape[:2], bool)
def stepped(arr, cuts, e, fill=None):
    """insert e lines along axis 0 of arr, at cut cuts[j] in column j: the line
    at the cut is repeated (or `fill` is put in)"""
    H = arr.shape[0]; r = np.arange(H + e)[:, None]; cj = cuts[None, :]
    src = np.where(r < cj, r, np.where(r < cj + e, cj, r - e))
    out = np.take_along_axis(arr, src if arr.ndim == 2 else src[..., None], axis=0)
    if fill is not None:
        out[(r >= cj) & (r < cj + e)] = fill
    return out
for axis, cut, extra, kept in ins:
    c = int(round((cut - M) * s)); e = int(round(extra * s))
    A_, K_ = (a, marked) if axis == 1 else (a.transpose(1, 0, 2), marked.T)
    ink = A_.mean(axis=2) < 128
    win = max(2, int(round(4 * s))); pad = max(2, int(round(3 * s)))
    def best(c, cols):
        # the line to repeat: near c, the one with the least ink over these
        # columns (the drawing cuts through empty space; the PNG's own lines lie
        # a pixel or two apart)
        prof = ink[:, cols].sum(axis=1)
        lo, hi = max(0, c - win), min(len(prof) - 1, c + win)
        return min(range(lo, hi + 1), key=lambda k: (prof[k], abs(k - c)))
    cuts = np.full(A_.shape[1], best(c, slice(None)))
    # a shape the drawing kept whole (it stayed, or moved past the space): the
    # cut steps round it, below it or above it
    for o0, o1, a0, a1, moved, _ in kept:
        j0, j1 = max(0, int(round((o0 - M) * s)) - pad), min(A_.shape[1], int(round((o1 - M) * s)) + pad + 1)
        at = int(round((a0 - M) * s)) - pad if moved else int(round((a1 - M) * s)) + pad
        cuts[j0:j1] = best(at, slice(j0, j1))
    A_ = stepped(A_, cuts, e); K_ = stepped(K_, cuts, e, True)
    a, marked = (A_, K_) if axis == 1 else (A_.transpose(1, 0, 2), K_.T)
a = np.ascontiguousarray(a)
png = Image.fromarray(a); W, H = png.size; png.save(f'{d}/png_cut.png')
subprocess.run(['node', RENDER, f'{ROOT}/diagrams/{n}/{n}.drawio', f'{d}/drawio_cut.png', str(W), str(H), str(s), 'png'], check=True, capture_output=True, env=NODE)
dr = Image.open(f'{d}/drawio_cut.png').convert('RGB')
A = np.asarray(png.convert('L')) < 128; B = np.asarray(dr.convert('L')) < 128
k = np.ones((2 * R + 1, 2 * R + 1), bool)
red = A & ~ndimage.binary_dilation(B, k); blue = B & ~ndimage.binary_dilation(A, k)
o = np.full(A.shape + (3,), 255, np.uint8); o[A | B] = (185, 185, 185)
o[ndimage.binary_dilation(red, iterations=1)] = (220, 0, 0); o[ndimage.binary_dilation(blue, iterations=1)] = (0, 60, 230)
ov = Image.fromarray(o)
# the inserted space, marked
from PIL import ImageDraw
def mark(img):
    m = np.zeros(marked.shape + (4,), np.uint8); m[marked] = (255, 200, 0, 70)
    lay = Image.fromarray(m, 'RGBA')
    return Image.alpha_composite(img.convert('RGBA'), lay).convert('RGB')
mark(png).save(f'{d}/png_cut_b.png'); mark(dr).save(f'{d}/drawio_cut_b.png'); mark(ov).save(f'{d}/overlay_cut_b.png')
res = json.load(open(f'{d}/result.json')) if os.path.exists(f'{d}/result.json') else {}
res.update(cut_red=100 * red.sum() / A.sum(), cut_blue=100 * blue.sum() / A.sum())
json.dump(res, open(f'{d}/result.json', 'w'))
print(n, 'red %.2f blue %.2f (uncut: red %.2f blue %.2f)' % (res['cut_red'], res['cut_blue'], res.get('red', 0), res.get('blue', 0)))
