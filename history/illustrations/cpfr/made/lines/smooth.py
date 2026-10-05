"""Every line of the person as a clean curve: each traced line's centre line followed from end to end,
fitted with a smoothing spline (a straight line where it is one); the head and hands as ellipses.
Writes lines/smooth.json: {n: [[x,y],...] (src px), ...}"""
import numpy as np, cv2, json
from scipy import ndimage, interpolate
from skimage.morphology import skeletonize
box=(55,20,335,330); k=3
M=np.load('lines/masks.npz')
def paths(mask):
    """the skeleton's longest paths, as ordered pixel lists (a line may break into several pieces)"""
    sk=skeletonize(ndimage.binary_closing(mask,iterations=2))
    out=[]
    lab,n=ndimage.label(sk,structure=np.ones((3,3)))
    for i in range(1,n+1):
        pts=set(zip(*np.where(lab==i)))
        if len(pts)<12: continue
        nb=lambda p:[(p[0]+a,p[1]+b) for a in (-1,0,1) for b in (-1,0,1) if (a or b) and (p[0]+a,p[1]+b) in pts]
        def bfs(s):
            prev={s:None}; q=[s]
            for p in q:
                for r in nb(p):
                    if r not in prev: prev[r]=p; q.append(r)
            return q[-1],prev
        a,_=bfs(next(iter(pts))); b,prev=bfs(a)
        path=[]; p=b
        while p is not None: path.append(p); p=prev[p]
        out.append(np.array([[x/k+box[0],y/k+box[1]] for y,x in path],float))
    return out
def fit(p,closed=False):
    if len(p)<4: return p
    # straight?
    c=p.mean(0); u,s_,vt=np.linalg.svd(p-c); d=vt[0]
    if s_[1]/np.sqrt(len(p))<0.35:
        t=(p-c)@d; return np.array([c+d*t.min(),c+d*t.max()])
    tck,_=interpolate.splprep(p.T,s=len(p)*0.12,per=closed)
    return np.array(interpolate.splev(np.linspace(0,1,max(20,len(p)//3)),tck)).T
def ellipse(mask):
    ys,xs=np.where(mask); (cx,cy),(w,h),a=cv2.fitEllipse(np.stack([xs,ys],1).astype(np.float32))
    t=np.linspace(0,2*np.pi,120); A=np.radians(a)
    x=cx+w/2*np.cos(t)*np.cos(A)-h/2*np.sin(t)*np.sin(A); y=cy+w/2*np.cos(t)*np.sin(A)+h/2*np.sin(t)*np.cos(A)
    return [np.stack([x/k+box[0],y/k+box[1]],1)]
out={}
for n in M.files:
    m=M[n]
    if n in ('1',): out[n]=[e.tolist() for e in ellipse(m)]; continue
    if n in ('13','15'):
        hx,hy,ha,hb,hang=np.load('lines/handell.npy'); c=np.array([hx,hy])+(np.load('lines/nearhand_c.npy')-[hx,hy] if n=='15' else 0)
        t=np.linspace(0,2*np.pi,120); A=np.radians(hang)
        out[n]=[np.stack([c[0]+ha*np.cos(t)*np.cos(A)-hb*np.sin(t)*np.sin(A), c[1]+ha*np.cos(t)*np.sin(A)+hb*np.sin(t)*np.cos(A)],1).tolist()]; continue
    out[n]=[fit(p).tolist() for p in paths(m) if len(p)>=12]
json.dump(out,open('lines/smooth.json','w'))
for n in sorted(out,key=int): print(n,len(out[n]),[len(q) for q in out[n]])
