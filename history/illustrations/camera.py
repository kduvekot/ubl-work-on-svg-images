# Fits a two-point-perspective camera (upright edges stay upright, as in the
# photo) to the measured points, with the pallet at EPAL's 1200 x 800 x 144 mm.
# World: X along the long side (the front, to the right), Z along the short
# side (away, to the left in the picture), Y up; the pallet's front-left
# bottom corner at the origin.
import numpy as np, json
from scipy.optimize import least_squares

def project(p, P):
    f, cx, cy, yaw, tx, ty, tz = p[:7]
    P = np.atleast_2d(P).astype(float)
    X, Y, Z = P[:, 0] - tx, P[:, 1] - ty, P[:, 2] - tz
    c, s = np.cos(yaw), np.sin(yaw)
    xc = c * X - s * Z          # camera right
    zc = s * X + c * Z          # camera depth
    return np.stack([cx + f * xc / zc, cy - f * Y / zc], 1)

def points(p):
    bx0, bz0, BX, BZ, Yt = p[7:]
    return {
        'box front-left top': ((bx0, Yt, bz0), (110, 13.5)),
        'box front-left foot': ((bx0, 144, bz0), (110, 295)),
        'box front-right top': ((bx0 + BX, Yt, bz0), (371, 59.5)),
        'box front-right foot': ((bx0 + BX, 144, bz0), (371, 263)),
        'box back-left top': ((bx0, Yt, bz0 + BZ), (20, 56)),
        'box back-left foot': ((bx0, 144, bz0 + BZ), (20, 263)),
        'pallet front-left floor': ((0, 0, 0), (103, 347)),
        'pallet front-right floor': ((1200, 0, 0), (373, 301)),
        'pallet front-right top': ((1200, 144, 0), (373, 264)),
        'pallet back-left top': ((0, 144, 800), (17, 264)),
        'pallet back-left floor': ((0, 0, 800), (17, 305)),
    }

def resid(p):
    pts = points(p)
    W = np.array([v[0] for v in pts.values()]); I = np.array([v[1] for v in pts.values()])
    return (project(p, W) - I).ravel()

if __name__ == '__main__':
    p0 = [900, 200, 150, np.radians(-30), -900, 1000, -1800, 10, 10, 1180, 780, 1300]
    p0[4:7] = [600, 1200, -2500]
    best = None
    for yaw in np.radians(np.arange(-80, 0, 5)):
        for d in (1500, 2500, 4000, 7000):
            q = list(p0); q[3] = yaw
            # camera in front, to the right, looking back-left
            q[4], q[5], q[6] = 600 + d * np.sin(-yaw) * 0, 1000, -d
            try:
                r = least_squares(resid, q, max_nfev=20000)
            except Exception:
                continue
            if best is None or r.cost < best.cost: best = r
    p = best.x
    res = resid(p).reshape(-1, 2)
    for (k, v), e in zip(points(p).items(), res): print('%-26s off by %5.1f, %5.1f px' % (k, *e))
    print('rms %.2f px' % np.sqrt((res ** 2).mean()))
    print('f %.0f  centre %.1f,%.1f  yaw %.1f deg  camera %s' % (p[0], p[1], p[2], np.degrees(p[3]), np.round(p[4:7])))
    print('boxes: offset X %.0f Z %.0f  size %.0f x %.0f  top at %.0f mm (height %.0f)' % (p[7], p[8], p[9], p[10], p[11], p[11] - 144))
    from paths import work
    json.dump(list(p), open(work('camera.json'), 'w'))
