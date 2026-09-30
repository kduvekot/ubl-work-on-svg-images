# Traces the Fulfilment figures' document icon (pic02: black ink, 468 x 595 px) into curves: the white page, and the ink over it.
#
#   python3 document.py      <WORK>/pictures/pic02.png -> illustrations/parts/document.svg
import os
import numpy as np, potrace, cv2
from PIL import Image
from paths import WORK, PARTS
a = np.array(Image.open(os.path.join(WORK, 'pictures', 'pic02.png')).convert('RGBA'))
ink = (a[..., 3] > 80) & (a[..., :3].mean(-1) < 128)   # the underline's dashes are faint
# the page: all that the outside cannot reach (the PNG leaves the inside
# of the page transparent; it is drawn white here, so the icon stands on any ground)
# (the border is open at the top right corner, where the top edge, at
# (447, 1), stops short of the right edge, at (452, 10): bridged for the page only)
M = 2
border = np.pad(ink.astype(np.uint8), M)
cv2.line(border, (447 + M, 1 + M), (452 + M, 11 + M), 1, 3)
mask = np.zeros((border.shape[0] + 2, border.shape[1] + 2), np.uint8)
cv2.floodFill(border, mask, (0, 0), 2)
page = (border[M:-M, M:-M] != 2)
def trace(mask):
    # potracer traces the zero pixels, so it is given the inverse
    parts = []
    for c in potrace.Bitmap(~mask).trace(turdsize=0, alphamax=1.0, opticurve=True, opttolerance=0.2):
        s = c.start_point; d = 'M%.1f,%.1f' % (s.x, s.y)
        for seg in c.segments:
            if seg.is_corner:
                d += 'L%.1f,%.1fL%.1f,%.1f' % (seg.c.x, seg.c.y, seg.end_point.x, seg.end_point.y)
            else:
                d += 'C%.1f,%.1f %.1f,%.1f %.1f,%.1f' % (seg.c1.x, seg.c1.y, seg.c2.x, seg.c2.y,
                                                        seg.end_point.x, seg.end_point.y)
        parts.append(d + 'Z')
    return parts
pg, ik = trace(page), trace(ink)
h, w = ink.shape
svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">\n'
       '<title>Document</title>\n'
       '<path fill="#ffffff" fill-rule="evenodd" d="%s"/>\n'
       '<path fill="#000000" fill-rule="evenodd" d="%s"/>\n</svg>\n') % (w, h, w, h, ''.join(pg), ''.join(ik))
os.makedirs(PARTS, exist_ok=True)
open(os.path.join(PARTS, 'document.svg'), 'w').write(svg)
print('page', len(pg), 'paths; ink', len(ik), 'paths;', len(svg), 'bytes')
