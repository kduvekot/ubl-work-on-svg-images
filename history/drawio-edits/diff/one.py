"""One figure: the original PNG (UBL art/) at its own pixel size, untouched,
and the draw.io drawing rendered onto exactly that canvas, and the diff between
them (tolerance 2 px per 1480 px of width, as in the SVG comparison).
Where the drawing grew (space inserted for short arrows), the canvas takes its
growth, and the PNG gets white at its right and bottom.

A figure drawn after the 78 were read (common.drawn_later: Groups A, B, C) had no space inserted. One
drawn on its PNG's pixels at one scale (its page is the PNG's size over that scale: Groups B and C,
Ordering) is rendered at that scale, as the others are at theirs. One that is not (the TC's own drawings
of Group A) is placed by its ink: rendered at the scale that makes its ink as wide as the PNG's, on a
canvas that holds it whole, then moved onto the PNG's ink for the diff (drawio.png).

render.png is what a baseline keeps (tools/drawio_baseline.py make): the drawing on that canvas, at that
scale, drawn as the baseline's check draws it again (common.NODE_DEVICE), so that the check finds it as
stored. The diff is of the zoomed render, which puts each line where it is to the device pixel.

    python3 one.py <figure> <out dir>      writes <out>/<figure>/{png,drawio,overlay,render}.png, result.json
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image
from scipy import ndimage
from common import ART, BEFORE_SPACE, NODE, NODE_DEVICE, RENDER, ROOT, drawn_later, illustration, natural_width, page

n, out = sys.argv[1], sys.argv[2]
d = os.path.join(out, n); os.makedirs(d, exist_ok=True)
src = f'{ROOT}/diagrams/{n}/{n}.drawio'
im = Image.open(f'{ART}/{n}.png')
if im.mode in ('RGBA', 'LA', 'P'):
    im = im.convert('RGBA'); bg = Image.new('RGBA', im.size, 'white'); bg.alpha_composite(im); im = bg
png = im.convert('RGB'); PW, PH = png.size; R = max(1, round(2 * PW / 1480))
now = page(open(src).read())
later = drawn_later(n)


def render(w, h, s, path, env=NODE):
    subprocess.run(['node', RENDER, src, path, str(w), str(h), str(s)], check=True, capture_output=True, env=env)
    return Image.open(path).convert('RGB')


def box(a):
    ys, xs = np.nonzero(a)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


if later and abs(PW / now[0] / (PH / now[1]) - 1) > 0.01:
    # placed by its ink: its extent at scale 1, then rendered at the scale that makes its ink the PNG's width
    A = np.asarray(png.convert('L')) < 128
    E = 6000
    t = np.asarray(render(E, E, 1, f'{d}/extent.png').convert('L')) < 128
    os.remove(f'{d}/extent.png')
    b = box(t)
    if b[2] >= E - 1 or b[3] >= E - 1:
        raise SystemExit('%s: larger than %d px at scale 1' % (n, E))
    pa = box(A)
    s = (pa[2] - pa[0]) / (b[2] - b[0])
    full = render(math.ceil(b[2] * s) + 8, math.ceil(b[3] * s) + 8, s, f'{d}/full.png')
    os.remove(f'{d}/full.png')
    rb = box(np.asarray(full.convert('L')) < 128)
    dx, dy = int(pa[0] - rb[0]), int(pa[1] - rb[1])
    dr = Image.new('RGB', (PW, PH), 'white'); dr.paste(full, (dx, dy)); dr.save(f'{d}/drawio.png')
    extra = dict(placed='ink', canvas=list(full.size), offset=[dx, dy])
else:
    # at its natural scale (a figure drawn later: its page on the PNG's pixels), grown where space was inserted
    # (an illustration or a figure drawn later had none)
    was = now if illustration(n) or later else page(subprocess.run(
        ['git', '-C', ROOT, 'show', f'{BEFORE_SPACE}:diagrams/{n}/{n}.drawio'], capture_output=True, text=True).stdout)
    s = PW / (now[0] if later else natural_width(n))
    c = Image.new('RGB', (PW + round((now[0] - was[0]) * s), PH + round((now[1] - was[1]) * s)), 'white'); c.paste(png, (0, 0)); png = c
    dr = render(png.width, png.height, s, f'{d}/drawio.png')
    extra = dict(placed='page' if later else 'natural', canvas=[png.width, png.height])
render(*extra['canvas'], s, f'{d}/render.png', NODE_DEVICE)
png.save(f'{d}/png.png')
A = np.asarray(png.convert('L')) < 128; B = np.asarray(dr.convert('L')) < 128
assert A.shape == B.shape, (A.shape, B.shape)
k = np.ones((2 * R + 1, 2 * R + 1), bool)
red = A & ~ndimage.binary_dilation(B, k); blue = B & ~ndimage.binary_dilation(A, k)
o = np.full(A.shape + (3,), 255, np.uint8); o[A | B] = (185, 185, 185)
o[ndimage.binary_dilation(red, iterations=1)] = (220, 0, 0); o[ndimage.binary_dilation(blue, iterations=1)] = (0, 60, 230)
Image.fromarray(o).save(f'{d}/overlay.png')
json.dump(dict(png_size=[PW, PH], scale=s, red=100 * red.sum() / A.sum(), blue=100 * blue.sum() / A.sum(), tol=R, **extra),
          open(f'{d}/result.json', 'w'))
print(n, 'red %.2f blue %.2f' % (100 * red.sum() / A.sum(), 100 * blue.sum() / A.sum()))
