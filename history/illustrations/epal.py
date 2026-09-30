# The EPAL Euro pallet (EPAL 1, EN 13698-1) from its parts: 1200 x 800 x 144 mm,
# 11 boards and 9 blocks (EPAL: epal-pallets.org; the part sizes as the
# suppliers list them).
#
# World axes, in mm: X along the long side (1200), Z along the short side
# (800), Y up; the front-left corner on the floor at the origin.
#
# From the floor up, four layers:
#   bottom boards  3, running along X: 100, 145, 100 wide, 22 thick
#   blocks         9, 78 high, in 3 rows of 3: 145 along X; 100 across in the
#                  outer rows, 145 in the middle row (so 6 of 145 x 100, 3 of
#                  145 x 145); 382.5 between them along X, 227.5 across
#   cross boards   3, running along Z over the block rows: 800 x 145 x 22
#   deck boards    5, running along X: 145, 100, 145, 100, 145 wide, 22 thick,
#                  evenly spaced (41.25 between)
import numpy as np

L, W = 1200, 800
T = 22                     # board thickness
BH = 78                    # block height
BLOCK_X = [(0, 145), (527.5, 672.5), (1055, 1200)]
ROW_Z = [(0, 100), (327.5, 472.5), (700, 800)]
_deck_w = [145, 100, 145, 100, 145]
_gap = (W - sum(_deck_w)) / 4
DECK_Z = []
_z = 0
for w in _deck_w:
    DECK_Z.append((_z, _z + w)); _z += w + _gap

def parts():
    """(layer, name, (x0, x1), (y0, y1), (z0, z1), grain axis)"""
    P = []
    for (z0, z1), n in zip(ROW_Z, ('edge', 'centre', 'edge')):
        P.append(('bottom', 'bottom board (%s) 1200 x %d x 22' % (n, z1 - z0), (0, L), (0, T), (z0, z1), 'x'))
    for x0, x1 in BLOCK_X:
        for z0, z1 in ROW_Z:
            P.append(('block', 'block 145 x %d x 78' % (z1 - z0), (x0, x1), (T, T + BH), (z0, z1), 'y'))
    for x0, x1 in BLOCK_X:
        P.append(('cross', 'cross board 800 x 145 x 22', (x0, x1), (T + BH, 2 * T + BH), (0, W), 'z'))
    for z0, z1 in DECK_Z:
        P.append(('deck', 'deck board 1200 x %d x 22' % (z1 - z0), (0, L), (2 * T + BH, 3 * T + BH), (z0, z1), 'x'))
    return P

LAYERS = ['bottom', 'block', 'cross', 'deck']
assert len([p for p in parts() if p[0] != 'block']) == 11 and len([p for p in parts() if p[0] == 'block']) == 9
assert 3 * T + BH == 144

def faces(x, y, z):
    (x0, x1), (y0, y1), (z0, z1) = x, y, z
    return {  # name: (outward normal, corners)
        'top': ((0, 1, 0), [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]),
        'bottom': ((0, -1, 0), [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]),
        'front': ((0, 0, -1), [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)]),
        'back': ((0, 0, 1), [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]),
        'left': ((-1, 0, 0), [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)]),
        'right': ((1, 0, 0), [(x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0)]),
    }

# the light: from above, front and a little left, as in the photo
SHADE = {'top': 0.88, 'front': 0.76, 'left': 0.64, 'right': 0.58, 'back': 0.5, 'bottom': 0.4}

def draw(project, eye, emit, lift=None, shade_inside=True):
    """Draws the pallet: layer by layer from the floor up (the eye is above the
    pallet, so a higher layer is never hidden by a lower one), far to near
    within a layer, only the faces turned to the eye.
    project: (N,3) -> (N,2); eye: the camera's position; emit(points, grey, face, part)
    lift: {layer: mm} to pull the layers apart (an exploded view)."""
    eye = np.array(eye, float)
    lift = lift or {}
    for layer in LAYERS:
        ps = [p for p in parts() if p[0] == layer]
        dy = lift.get(layer, 0)
        def dist(p):
            lo = np.array([p[2][0], p[3][0] + dy, p[4][0]]); hi = np.array([p[2][1], p[3][1] + dy, p[4][1]])
            return np.linalg.norm(np.clip(eye, lo, hi) - eye)
        for p in sorted(ps, key=dist, reverse=True):
            _, name, x, y, z, grain = p
            y = (y[0] + dy, y[1] + dy)
            for fname, (n, F) in faces(x, y, z).items():
                c = np.mean(F, 0)
                if np.dot(n, eye - c) <= 0: continue          # turned away
                t = SHADE[fname]
                if shade_inside and not lift:
                    outside = ((fname == 'top' and y[1] == 144) or (fname == 'front' and z[0] == 0) or
                               (fname == 'left' and x[0] == 0) or (fname == 'right' and x[1] == L) or
                               (fname == 'back' and z[1] == W))
                    if not outside:
                        t *= 0.7                               # inside the pallet: in its shade
                emit(project(np.array(F, float)), t, fname, p)
