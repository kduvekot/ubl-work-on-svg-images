"""All visible lines of the person at the head of the meeting table: the drawn outlines and every
edge where one fill meets another, found on the clean render (enlarged 4x), thinned to centre lines,
kept where they belong to the person, and drawn over the crop."""
import numpy as np, cv2
from PIL import Image, ImageDraw
from scipy import ndimage
from skimage.morphology import skeletonize
Z = 4
src = Image.open('ris/found-meeting-730x792-pinimg.png').convert('RGBA')
box = (55, 20, 335, 330)                                   # the crop shown before (280 x 310)
crop = src.crop(box)
bg = Image.new('RGB', crop.size, 'white'); bg.paste(crop, mask=crop.split()[3])
# the two persons in front (lower left, lower middle) removed: white over their heads and bodies
yy0, xx0 = np.mgrid[0:crop.height, 0:crop.width]; X = xx0 + box[0]; Y = yy0 + box[1]
fr = (((X - 111) / 43) ** 2 + ((Y - 262) / 50) ** 2 < 1) | (((X - 240) / 44) ** 2 + ((Y - 330) / 44) ** 2 < 1)
fr |= (Y > 298) & (X < 218)                                       # the front person's neck and shoulders
fr |= (Y > 250) & (X < 72)
# the person across the table (top right) removed too: right of x 282, above the table
fr |= (X > 282) & (Y < 228 - (X - 282) * 0.05)
# the head-of-table person's own near forearm and hand stay (they run from under the front head to the right)
ap = Image.new('L', crop.size, 0)
ImageDraw.Draw(ap).polygon([(x - box[0], y - box[1]) for x, y in [(146, 248), (204, 279), (224, 300), (210, 320), (182, 318), (146, 302)]], fill=255)
fr &= ~(np.asarray(ap) > 0) | (((X - 240) / 44) ** 2 + ((Y - 330) / 44) ** 2 < 1)
b = np.asarray(bg).copy(); b[fr] = 255; bg = Image.fromarray(b)
big = bg.resize((crop.width * Z, crop.height * Z), Image.LANCZOS)
a = np.asarray(big).astype(np.float32)
# edges: the drawn lines and the boundaries between fills, on a smoothed copy
lab = cv2.cvtColor(np.asarray(big), cv2.COLOR_RGB2LAB)
sm = cv2.bilateralFilter(lab, 9, 20, 7)
e = np.zeros(a.shape[:2], bool)
for ch, lo, hi in ((0, 18, 45), (1, 10, 25), (2, 10, 25)):
    e |= cv2.Canny(sm[..., ch], lo, hi) > 0
# the person: head, torso, far arm and hand (the chair panel, the table and the others left out)
S = np.asarray(src); Si = S.astype(int)
def poly(pts):
    m = Image.new('L', src.size, 0); ImageDraw.Draw(m).polygon(pts, fill=255); return np.asarray(m) > 0
person = poly([(146,248),(204,279),(224,300),(210,320),(146,302)]) | poly([(92,128),(122,100),(122,12),(212,12),(214,100),(240,114),(242,206),(255,212),(300,226),(332,236),(344,262),(326,290),(286,288),(250,268),(238,262),(150,262),(92,262)])
pm = Image.fromarray((person[box[1]:box[3], box[0]:box[2]] * 255).astype(np.uint8)).resize(big.size, Image.NEAREST)
pm = ndimage.binary_dilation(np.asarray(pm) > 0, iterations=6)
yy, xx = np.mgrid[0:pm.shape[0], 0:pm.shape[1]]
# the person in front (its head and shoulder, lower left) covers this one there: left out
front = ((xx / Z + box[0] - 124) / 46) ** 2 + ((yy / Z + box[1] - 280) / 52) ** 2 < 1
e &= pm & ~front & ~ndimage.binary_dilation(np.asarray(Image.fromarray((fr * 255).astype(np.uint8)).resize(big.size, Image.NEAREST)).astype(bool), iterations=4 * Z)   # the removed persons' outlines and the edge of the white left in their place
sk = skeletonize(ndimage.binary_closing(e, np.ones((3, 3))))
# into polylines: trace the skeleton's pixels as chains, smooth and simplify
lab_, n = ndimage.label(sk, structure=np.ones((3, 3)))
lines = []
for i in range(1, n + 1):
    m = (lab_ == i).astype(np.uint8)
    if m.sum() < 25: continue
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    for c in cs:
        c = cv2.approxPolyDP(c, 1.2, False)[:, 0]
        if len(c) >= 2: lines.append(c / Z)
np.save('lines/lines.npy', np.array(lines, dtype=object), allow_pickle=True)
# the overlay, at 3x
k = 3
ov = np.asarray(bg.resize(big.size, Image.LANCZOS).convert('RGB')).copy()
thick = ndimage.binary_dilation(sk, iterations=1)
ov[thick] = (230, 0, 0)
Image.fromarray(ov).resize((crop.width * k, crop.height * k), Image.LANCZOS).save('lines/overlay.png')
on = np.full(ov.shape, 255, np.uint8); on[thick] = 0
Image.fromarray(on).resize((crop.width * k, crop.height * k), Image.LANCZOS).save('lines/lines-only.png')
# the lines alone
#only = Image.new('RGB', ov.size, 'white'); d = ImageDraw.Draw(only)
#for c in lines: d.line([(x * k, y * k) for x, y in c], fill=(0, 0, 0), width=2)
#only.save('lines/lines-only.png')
print(len(lines), 'polylines')
