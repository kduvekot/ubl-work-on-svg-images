"""A replacement picture against the original clipart, as history/drawio-edits/
diff/one.py compares a drawing with its PNG: the SVG rendered onto the
reference's own canvas (ref/<part>.png, cut from the prd1 master at 600 dpi;
the SVG's viewBox is that canvas, so no fitting), tolerance 2 px per 1480 px of
the figure's width, red: only the original, blue: only ours, % of the
original's. Two measures:
  shape  the silhouettes (everything that is not background)
  ink    the dark lines (grey < 128), as one.py
    python3 clipdiff.py <part> [<svg>]      default svg: parts/<part>.svg
writes diff/<part>-{overlay,side}.png and diff/<part>.json"""
import io, json, os, sys
import cairosvg, numpy as np
from PIL import Image
from scipy import ndimage
FIG_W = {'meeting': 4044, 'handshake': 4044, 'document': 4044, 'clipboard': 3120, 'desk': 3120, 'desk-full': 3120}
part = sys.argv[1]; svg = sys.argv[2] if len(sys.argv) > 2 else f'parts/{part}.svg'
os.makedirs('diff', exist_ok=True)
ref = Image.open(f'ref/{part}.png').convert('RGB'); W, H = ref.size
A_sh = np.asarray(Image.open(f'ref/{part}-mask.png')) > 127
ours = Image.open(io.BytesIO(cairosvg.svg2png(url=svg, output_width=W, output_height=H))).convert('RGBA')
assert ours.size == (W, H), ours.size
B_sh = np.asarray(ours)[..., 3] > 127
bg = Image.new('RGB', (W, H), 'white'); bg.paste(ours, mask=ours.split()[3]); ours_rgb = bg
A_ink = np.asarray(ref.convert('L')) < 128; B_ink = np.asarray(ours_rgb.convert('L')) < 128
R = max(1, round(2 * FIG_W[part] / 1480)); k = np.ones((2 * R + 1, 2 * R + 1), bool)
def cmp(A, B):
    red = A & ~ndimage.binary_dilation(B, k); blue = B & ~ndimage.binary_dilation(A, k)
    return red, blue, 100 * red.sum() / A.sum(), 100 * blue.sum() / A.sum()
res = {'size': [W, H], 'tol': R}
ov = []
for name, A, B in (('shape', A_sh, B_sh), ('ink', A_ink, B_ink)):
    red, blue, r, b = cmp(A, B); res[name] = {'red': round(r, 2), 'blue': round(b, 2)}
    o = np.full(A.shape + (3,), 255, np.uint8); o[A | B] = (185, 185, 185)
    o[ndimage.binary_dilation(red, iterations=1)] = (220, 0, 0); o[ndimage.binary_dilation(blue, iterations=1)] = (0, 60, 230)
    ov.append(Image.fromarray(o))
json.dump(res, open(f'diff/{part}.json', 'w'))
gap = 20; side = Image.new('RGB', (4 * W + 5 * gap, H + 2 * gap), (235, 235, 235))
for i, im in enumerate([ref, ours_rgb] + ov): side.paste(im, (gap + i * (W + gap), gap))
side.save(f'diff/{part}-side.png')
print(f"{part:10s} shape red {res['shape']['red']:6.2f}  blue {res['shape']['blue']:6.2f}   ink red {res['ink']['red']:6.2f}  blue {res['ink']['blue']:6.2f}   (tol {R} px)")
