"""Reference pictures from the prd1 colour masters: each clipart cut out
(mask = not the panel's pink; the diagram's own ink over it, connector lines,
arrowheads, the Resolve Exception box and text, erased by hand-set boxes;
the largest piece kept, small holes filled), put on white, cropped to its
bounding box. Writes ref/<part>.png (RGB on white) and ref/<part>-mask.png."""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage
M = '../cpfr/UBL-CPFR-dossier/artwork/prd1-masters/UBL-2.1-CPFR-%s.png'
PINK = np.array([255, 204, 204])
# part: (figure, crop box in master px, erase boxes in crop px)
PARTS = {
 'meeting':   ('Steps1-2',   (480, 151, 1065, 774), []),
 'handshake': ('Steps1-2',   (562, 1166, 1029, 1663), [(188, 0, 252, 26), (292, 440, 310, 497)]),
 'document':  ('Steps1-2',   (763, 1954, 966, 2310), [(76, 0, 120, 60), (92, 266, 108, 356)]),
 'clipboard': ('Steps3-4-5', (2302, 198, 2493, 558), []),
 'desk':      ('Steps3-4-5', (1761, 1545, 2140, 1895), [(224, 0, 379, 24), (224, 0, 244, 128), (224, 272, 379, 350), (282, 100, 379, 195)]),
}
DEBUG = len(sys.argv) > 1
for part, (fig, box, erase) in PARTS.items():
    a = np.asarray(Image.open(M % fig).convert('RGB').crop(box)).astype(int)
    fg = np.abs(a - PINK).sum(2) > 30
    if part == 'desk':
        fg &= ~(np.abs(a - [164, 164, 206]).sum(2) < 40)     # the box's flat lavender
    ink = (a.max(2) - a.min(2) < 40) & (a.sum(2) < 480)        # the diagram's black/grey ink
    ink = ndimage.binary_dilation(ink, iterations=2)
    for x0, y0, x1, y1 in erase:
        fg[y0:y1, x0:x1] &= ~ink[y0:y1, x0:x1]
    if DEBUG:
        Image.fromarray(np.where(fg[..., None], a, 255).astype(np.uint8)).save(f'ref/{part}-debug.png'); continue
    op = ndimage.binary_opening(fg, np.ones((7, 7)))
    lab, n = ndimage.label(op)
    sizes = ndimage.sum(op, lab, range(1, n + 1))
    keep = np.isin(lab, [i for i, sz in enumerate(sizes, 1) if sz > 0.02 * sizes.max()])
    keep = fg & ndimage.binary_dilation(keep, iterations=4) | keep
    holes = ndimage.binary_fill_holes(keep) & ~keep
    hl, hn = ndimage.label(holes)
    for i, sz in enumerate(ndimage.sum(holes, hl, range(1, hn + 1)), 1):
        if sz < 0.01 * keep.sum(): keep |= hl == i
    ys, xs = np.where(keep)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    Image.fromarray(np.where(keep[..., None], a, 255)[y0:y1, x0:x1].astype(np.uint8)).save(f'ref/{part}.png')
    Image.fromarray((keep[y0:y1, x0:x1] * 255).astype(np.uint8)).save(f'ref/{part}-mask.png')
    print(part, x1 - x0, 'x', y1 - y0, 'at', box[0] + x0, box[1] + y0)
