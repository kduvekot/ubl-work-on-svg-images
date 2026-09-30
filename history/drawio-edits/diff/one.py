"""One figure: the original PNG (UBL art/) at its own pixel size, untouched,
and the draw.io drawing rendered onto exactly that canvas, and the diff between
them (tolerance 2 px per 1480 px of width, as in the SVG comparison).
Where the drawing grew (space inserted for short arrows), the canvas takes its
growth, and the PNG gets white at its right and bottom.

    python3 one.py <figure> <out dir>      writes <out>/<figure>/{png,drawio,overlay}.png, result.json
"""
import json, os, re, subprocess, sys
import numpy as np
from PIL import Image
from scipy import ndimage
from common import ART, BEFORE_SPACE, NODE, RENDER, ROOT, illustration, natural_width

n, out = sys.argv[1], sys.argv[2]
d = os.path.join(out, n); os.makedirs(d, exist_ok=True)
im = Image.open(f'{ART}/{n}.png')
if im.mode in ('RGBA', 'LA', 'P'):
    im = im.convert('RGBA'); bg = Image.new('RGBA', im.size, 'white'); bg.alpha_composite(im); im = bg
png = im.convert('RGB'); PW, PH = png.size; R = max(1, round(2 * PW / 1480))
page = lambda t: [int(v) for v in re.search(r'pageWidth="(\d+)" pageHeight="(\d+)"', t).groups()]
now = page(open(f'{ROOT}/diagrams/{n}/{n}.drawio').read())
# (an illustration was made after, and had no space inserted)
was = now if illustration(n) else page(subprocess.run(['git', '-C', ROOT, 'show', f'{BEFORE_SPACE}:diagrams/{n}/{n}.drawio'], capture_output=True, text=True).stdout)
s = PW / natural_width(n)
c = Image.new('RGB', (PW + round((now[0] - was[0]) * s), PH + round((now[1] - was[1]) * s)), 'white'); c.paste(png, (0, 0)); png = c
W, H = png.size
png.save(f'{d}/png.png')
subprocess.run(['node', RENDER, f'{ROOT}/diagrams/{n}/{n}.drawio', f'{d}/drawio.png', str(W), str(H), str(s)], check=True, capture_output=True, env=NODE)
dr = Image.open(f'{d}/drawio.png').convert('RGB')
A = np.asarray(png.convert('L')) < 128; B = np.asarray(dr.convert('L')) < 128
assert A.shape == B.shape, (A.shape, B.shape)
k = np.ones((2 * R + 1, 2 * R + 1), bool)
red = A & ~ndimage.binary_dilation(B, k); blue = B & ~ndimage.binary_dilation(A, k)
o = np.full(A.shape + (3,), 255, np.uint8); o[A | B] = (185, 185, 185)
o[ndimage.binary_dilation(red, iterations=1)] = (220, 0, 0); o[ndimage.binary_dilation(blue, iterations=1)] = (0, 60, 230)
Image.fromarray(o).save(f'{d}/overlay.png')
json.dump(dict(png_size=[PW, PH], red=100 * red.sum() / A.sum(), blue=100 * blue.sum() / A.sum(), tol=R), open(f'{d}/result.json', 'w'))
print(n, 'red %.2f blue %.2f' % (100 * red.sum() / A.sum(), 100 * blue.sum() / A.sum()))
