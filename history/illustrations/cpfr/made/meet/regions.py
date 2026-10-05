"""Clean vector from a clean render of a clip-art shape: the render's own lines split it into areas; each area
is traced (straight-edged ones as polygons, curved ones smooth), filled with a grey gradient fitted to the
render (heads radial, lit from the upper left), and outlined thin; the whole shape gets a thick outline."""
import numpy as np, potrace, cv2
from PIL import Image
from scipy import ndimage
def vectorize(png,Z=3,prefix='r',minarea=60,skip=None):
    src=np.asarray(Image.open(png).convert('RGBA')).astype(np.uint8)
    al=src[...,3]>128; rgb=src[...,:3].copy(); rgb[~al]=255
    big=cv2.resize(rgb,None,fx=Z,fy=Z,interpolation=cv2.INTER_CUBIC)
    lab=cv2.cvtColor(big,cv2.COLOR_RGB2LAB)
    e=np.zeros(big.shape[:2],bool)
    for c in range(3): e|=cv2.Canny(cv2.GaussianBlur(lab[...,c],(5,5),1.2),25,60)>0
    alb=cv2.GaussianBlur(cv2.resize(src[...,3],None,fx=Z,fy=Z,interpolation=cv2.INTER_CUBIC),(0,0),Z*0.7)>128
    e|=alb^ndimage.binary_erosion(alb)
    e=ndimage.binary_dilation(e,iterations=2)
    reg=alb&~e
    lb,n=ndimage.label(reg); sz=ndimage.sum(reg,lb,range(1,n+1))
    H,W=lb.shape; yy,xx=np.mgrid[0:H,0:W]; X=xx/Z; Y=yy/Z
    def grey_at(m):
        c=big[m].astype(float); return ((0.30*c[:,0]+0.59*c[:,1]+0.11*c[:,2])/255)**0.6
    def path(mask,alpha=0.9,tol=1.0):
        cs=list(potrace.Bitmap(~mask).trace(turdsize=20,alphamax=alpha,opticurve=True,opttolerance=tol))
        f=lambda p: f'{p.x/Z:.1f},{p.y/Z:.1f}'; d=[]
        for c in cs:
            d.append('M'+f(c.start_point))
            for s in c.segments: d.append(('L'+f(s.c)+'L'+f(s.end_point)) if s.is_corner else ('C'+f(s.c1)+' '+f(s.c2)+' '+f(s.end_point)))
            d.append('Z')
        return ''.join(d)
    def poly(mask,eps=1.3):
        cs,_=cv2.findContours(mask.astype(np.uint8),cv2.RETR_CCOMP,cv2.CHAIN_APPROX_NONE); out=[]; nv=0
        for c in cs:
            if cv2.contourArea(c)<30*Z*Z: continue
            a=cv2.approxPolyDP(c,eps*Z,True)[:,0]; nv=max(nv,len(a))
            out.append('M'+' L'.join(f'{x/Z:.1f},{y/Z:.1f}' for x,y in a)+'Z')
        return ''.join(out),nv
    def shape(mask):
        d,nv=poly(mask)
        cs,_=cv2.findContours(mask.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE); c=max(cs,key=cv2.contourArea)
        hull=cv2.convexHull(c); a=cv2.contourArea(c); ah=cv2.contourArea(hull); pr=cv2.arcLength(hull,True)
        round_=4*np.pi*ah/pr**2>0.8 and a/ah>0.9
        return path(mask) if round_ or nv>16 else d
    hexg=lambda v: '#'+f'{int(round(np.clip(v,0,1)*255)):02x}'*3
    out=[]
    for r in range(1,n+1):
        if sz[r-1]<minarea*Z*Z: continue
        m=lb==r
        if skip is not None:
            k=skip(m,X,Y)
            if k=='skip': continue
        else: k=None
        m=ndimage.binary_dilation(m,iterations=3)&alb
        g=grey_at(m); xv,yv=X[m],Y[m]
        sub=slice(None,None,max(1,len(g)//4000)); g,xv,yv=g[sub],xv[sub],yv[sub]
        Am=np.stack([np.ones_like(xv),xv,yv],1); c=np.linalg.lstsq(Am,g,rcond=None)[0]
        dv=c[1:]/(np.linalg.norm(c[1:])+1e-12); pr=xv*dv[0]+yv*dv[1]; p0,p1=pr.min(),pr.max()
        pt=lambda t:(xv.mean()+(p0+t*(p1-p0)-pr.mean())*dv[0],yv.mean()+(p0+t*(p1-p0)-pr.mean())*dv[1])
        q=lambda t:c[0]+c[1]*pt(t)[0]+c[2]*pt(t)[1]
        head=abs(np.ptp(xv)-np.ptp(yv))<0.25*np.ptp(yv) and 50<np.ptp(yv)<130 and g.mean()>0.75
        if head:
            i=np.argmax(g); R=np.hypot(xv-xv[i],yv-yv[i]).max()
            d=f'<radialGradient id="{prefix}{r}" gradientUnits="userSpaceOnUse" cx="{xv[i]:.1f}" cy="{yv[i]:.1f}" r="{R:.1f}"><stop offset="0" stop-color="{hexg(np.percentile(g,99))}"/><stop offset="1" stop-color="{hexg(np.percentile(g,3))}"/></radialGradient>'
        else:
            d=f'<linearGradient id="{prefix}{r}" gradientUnits="userSpaceOnUse" x1="{pt(0)[0]:.1f}" y1="{pt(0)[1]:.1f}" x2="{pt(1)[0]:.1f}" y2="{pt(1)[1]:.1f}"><stop offset="0" stop-color="{hexg(q(0))}"/><stop offset="1" stop-color="{hexg(q(1))}"/></linearGradient>'
        out.append(dict(defs=d,path=f'<path d="{shape(m)}" fill="url(#{prefix}{r})"/>',tag=k))
    outline=path(ndimage.binary_fill_holes(alb))
    return out,outline
