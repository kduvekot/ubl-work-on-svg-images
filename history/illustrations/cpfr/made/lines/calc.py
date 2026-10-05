# A printing calculator, isometric: keys towards him, the display behind them, the printer and its roll
# at the back, the tape coming over the roll and curling down the back onto the desk.
# u: along the edge he sits at, v: away from him, z: up.
import numpy as np
O=np.array([80.,246.]); U=np.array([0.866,-0.5]); V=np.array([0.866,0.5])
W,D,h0,h1=40.,50.,5.,11.
def P(u,v,z): p=O+u*U+v*V+np.array([0,-z]); return f"{p[0]:.1f},{p[1]:.1f}"
def poly(pts,**a):
    at=' '.join(f'{k.replace("_","-")}="{v}"' for k,v in a.items())
    return f'<path d="M{" L".join(P(*q) for q in pts)} Z" {at}/>'
top=lambda v:h0+(h1-h0)*v/D
out=['<!-- the calculator: keys towards him, display behind them, the printer roll at the back, its tape curling down onto the desk -->',
 '<g stroke="#262626" stroke-width="4" stroke-linejoin="round">']
out.append(poly([(0,0,0),(0,D,0),(0,D,h1),(0,0,h0)],fill="#9a9a9a"))           # his left side
out.append(poly([(0,D,0),(W,D,0),(W,D,h1),(0,D,h1)],fill="#b4b4b4"))           # the back
out.append(poly([(0,0,h0),(W,0,h0),(W,D,h1),(0,D,h1)],fill="url(#calc)"))     # the top, sloping up to the back
out.append('</g>')
# keys: 4 x 4, nearest him
k=['<g fill="#f7f7f7" stroke="#6a6a6a" stroke-width="1.1" stroke-linejoin="round">']
for i in range(4):
    for j in range(3):
        u0=5+i*8; v0=4+j*6
        k.append(poly([(u0,v0,top(v0)),(u0+5.5,v0,top(v0)),(u0+5.5,v0+3.8,top(v0+3.8)),(u0,v0+3.8,top(v0+3.8))]))
k.append('</g>'); out+=k
# the display, behind the keys
v0,v1=25,31
out.append(poly([(4,v0,top(v0)),(W-4,v0,top(v0)),(W-4,v1,top(v1)),(4,v1,top(v1))],fill="#8d8d8d",stroke="#4a4a4a",stroke_width="1.4"))
# the roll: a cylinder along u at the back
rc_v,rc_z,r=D-5,h1+4.5,4.5
a=np.linspace(0,2*np.pi,48)
def roll_end(u): return [(u,rc_v+r*np.cos(t),rc_z+r*np.sin(t)) for t in a]
ua,ub=5,35
# body of the roll: outline of the swept circle = hull of both end ellipses
import shapely.geometry as G
def xy(q):
    p=O+q[0]*U+q[1]*V+np.array([0,-q[2]]); return tuple(p)
hull=G.MultiPoint([xy(q) for q in roll_end(ua)+roll_end(ub)]).convex_hull
out.append('<path d="M'+' L'.join(f'{x:.1f},{y:.1f}' for x,y in hull.exterior.coords)+' Z" fill="#e2e2e2" stroke="#262626" stroke-width="2.2" stroke-linejoin="round"/>')
out.append(poly(roll_end(ua),fill="#cfcfcf",stroke="#262626",stroke_width="2"))
out.append(poly([(ua,rc_v+1.6*np.cos(t),rc_z+1.6*np.sin(t)) for t in a],fill="#7a7a7a",stroke="none"))
# the tape: out of the slot in front of the roll, up and over it, down the back and curling out over the desk
prof=[(D-10.5,top(D-10.5))]
prof+=[(rc_v+(r+0.8)*np.cos(t),rc_z+(r+0.8)*np.sin(t)) for t in np.linspace(np.pi,0,14)]
# down the back, curling out onto the desk
c=[(rc_v+r+0.8,rc_z),(D+3,h1-1),(D+6,3),(D+11,0.3),(D+18,0)]
from scipy.interpolate import CubicSpline
cv=np.array(c); t=np.linspace(0,1,len(cv)); cs=CubicSpline(t,cv)
prof+=[tuple(cs(s)) for s in np.linspace(0,1,16)[1:]]
t0,t1=10,30
strip=[(t0,v,z) for v,z in prof]+[(t1,v,z) for v,z in prof[::-1]]
segs=[]
for (va,za),(vb,zb) in zip(prof[:-1],prof[1:]):
    segs.append(G.Polygon([xy((t0,va,za)),xy((t0,vb,zb)),xy((t1,vb,zb)),xy((t1,va,za))]).buffer(0))
from shapely.ops import unary_union
tp=unary_union(segs).buffer(0.01)
out.append('<path d="M'+' L'.join(f'{x:.1f},{y:.1f}' for x,y in tp.exterior.coords)+' Z" fill="#fdfdfd" stroke="#262626" stroke-width="2.2" stroke-linejoin="round"/>')
# a few printed lines on the hanging part
lines=[]
for s in (0.35,0.55,0.75):
    v,z=cs(s); lines.append(f'M{P(t0+3,v,z)} L{P(t1-6,v,z)}')
out.append(f'<path d="{" ".join(lines)}" fill="none" stroke="#9a9a9a" stroke-width="1.1"/>')
CALC='\n  '.join(out)
if __name__=='__main__': print(CALC)
