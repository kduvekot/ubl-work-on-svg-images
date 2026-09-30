# From a pixel of the photo back to a point on a box face, in mm, through
# the fitted camera (camera.py's project, inverted).
import numpy as np, json
from paths import WORK
import os
CAM = json.load(open(os.path.join(WORK, 'camera.json')))
f, cx, cy, yaw, tx, ty, tz = CAM[:7]
BX0, BZ0, BXL, BZL, YT = CAM[7:]          # the stack: front-left corner, size, top
c, s = np.cos(yaw), np.sin(yaw)

def on_front(u, v, Z=BZ0):
    """pixel -> (X, Y) on the plane Z (the stack's front)"""
    a = (np.asarray(u, float) - cx) / f; Zp = Z - tz
    Xp = -(s + a * c) * Zp / (a * s - c)
    zc = s * Xp + c * Zp
    return Xp + tx, -(np.asarray(v, float) - cy) * zc / f + ty

def on_side(u, v, X=BX0):
    """pixel -> (Z, Y) on the plane X (the stack's left side)"""
    a = (np.asarray(u, float) - cx) / f; Xp = X - tx
    Zp = Xp * (c - a * s) / (a * c + s)
    zc = s * Xp + c * Zp
    return Zp + tz, -(np.asarray(v, float) - cy) * zc / f + ty
