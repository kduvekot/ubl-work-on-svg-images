"""The person on the far side of the meeting table (drawn mirrored): the person at the head of the table without
his forearms and hands (on the far side they are under the table top), his body and arms down to the table's far edge.
Otherwise as person2.py: the person as clean vector, from the clean lines (lines/clean.json): the lines split him into areas
(rasterised at 6x only to find the areas), each area's outline traced smooth and filled with a grey
gradient fitted to the clean render where it shows him (elsewhere from its counterpart on his other side).
The lines themselves are drawn from the fitted curves, the hands last (over the ends of the forearms).
Writes lines/person2.json with the SVG pieces, in the clean render's px."""
import json, numpy as np, potrace
from PIL import Image, ImageDraw
from scipy import ndimage
S=json.load(open('lines/clean.json')); S_all=dict(S); G=json.load(open('lines/geom.json'))
box=(55,20,335,330); k=6; W,H=(box[2]-box[0])*k,(box[3]-box[1])*k; C,Sn=np.cos(np.pi/6),0.5
Pk=lambda x,y:((x-box[0])*k,(y-box[1])*k)
def draw(lines,w=3,img=None):
    img=img or Image.new('L',(W,H),0); d=ImageDraw.Draw(img)
    for p in lines: d.line([Pk(*q) for q in p],fill=255,width=w)
    return img
FA=[p for n in ('12','14') for p in S[n]]
S={n:ps for n,ps in S.items() if n not in ('12','14','13','15','16')}
EDGE=[[(40,347-0.5664*40),(340,347-0.5664*340)]]            # the far table edge, in his own px (mirrored back)
ey=lambda x:347-0.5664*x+4
def down(p):                                                   # carried on straight down to (just past) the edge
    p=[list(q) for q in p]; e=p[-1] if p[-1][1]>p[0][1] else p[0]; return [q for q in p]+[[e[0],ey(e[0])]] if e is p[-1] else [[e[0],ey(e[0])]]+p
S['8']=[max(S['8'],key=len)]; e8=max(S['8'][0],key=lambda q:q[1]); S['8'].append([e8,[e8[0],ey(e8[0])]])
for n in ('10','11'): q=S[n][0]; e=max(q,key=lambda q:q[1]); S[n]=[[min(q,key=lambda q:q[1]),[e[0],ey(e[0])]]]
q=S['20'][0]; a,b=np.array(q[0]),np.array(q[-1]); t=(ey(b[0])-a[1])/(b[1]-a[1]); S['20']=[[list(a),list(a+(b-a)*t)]]
allp=[p for n,ps in S.items() for p in ps]+EDGE
A=(275,207.09); line16=[[A,(A[0]-260*C,A[1]+260*Sn)]]
L=np.asarray(draw(allp,w=5))>0
L=ndimage.binary_closing(L,iterations=4)                     # junctions that just miss each other
lab,n=ndimage.label(~L)
border=set(np.unique(np.r_[lab[0],lab[-1],lab[:,0],lab[:,-1]]))
sizes=ndimage.sum(~L,lab,range(1,n+1))
yy,xx=np.mgrid[0:H,0:W]; X=xx/k+box[0]; Y=yy/k+box[1]
hand=lambda c: (lambda u,v: (u/G['hand'][0])**2+(v/G['hand'][1])**2<1)(*( ( (X-c[0])*np.cos(np.radians(G['hand'][2]))+(Y-c[1])*np.sin(np.radians(G['hand'][2])), -(X-c[0])*np.sin(np.radians(G['hand'][2]))+(Y-c[1])*np.cos(np.radians(G['hand'][2])) ) ))
H1,H2=hand(G['hc']),hand(G['nh'])
regions=[i for i in range(1,n+1) if sizes[i-1]>=600*(k/3)**2 and i not in border]
src=np.asarray(Image.open('ris/found-meeting-730x792-pinimg.png').convert('RGBA')).astype(float)
fr=((((X-111)/43)**2+((Y-262)/50)**2)<1.15)|((((X-240)/44)**2+((Y-330)/44)**2)<1.15)|((Y>298)&(X<218))
Th=np.array(G['Th'])
from scipy.spatial import ConvexHull
def hullmask(pts):
    pts=np.vstack(pts); hp=pts[ConvexHull(pts).vertices]
    im=Image.new('L',(W,H),0); ImageDraw.Draw(im).polygon([Pk(*q) for q in hp],fill=255); return np.asarray(im)>0
FAm=ndimage.binary_dilation(hullmask(S_all['12'])|hullmask(S_all['14']),iterations=3*k)
def grey_at(x,y):
    xi=np.clip(np.round(x).astype(int),0,src.shape[1]-1); yi=np.clip(np.round(y).astype(int),0,src.shape[0]-1)
    c=src[yi,xi,:3]; return ((0.30*c[...,0]+0.59*c[...,1]+0.11*c[...,2])/255)**0.6
def path(mask):
    cs=list(potrace.Bitmap(~mask).trace(turdsize=40,alphamax=1.2,opticurve=True,opttolerance=0.6))
    f=lambda p: f'{p.x/k+box[0]:.2f},{p.y/k+box[1]:.2f}'; d=[]
    for c in cs:
        d.append('M'+f(c.start_point))
        for s in c.segments: d.append(('L'+f(s.c)+'L'+f(s.end_point)) if s.is_corner else ('C'+f(s.c1)+' '+f(s.c2)+' '+f(s.end_point)))
        d.append('Z')
    return ''.join(d)
hexg=lambda v: '#'+f'{int(round(np.clip(v,0,1)*255)):02x}'*3
defs=[]; fills=[]; sil=np.zeros((H,W),bool)
for r in regions:
    m=lab==r
    m=ndimage.binary_dilation(m,iterations=4)
    sil|=m
    x,y=X[m][::7],Y[m][::7]; vis=~fr[m][::7]&~FAm[m][::7]
    if vis.mean()>0.35: g=grey_at(x[vis],y[vis]); xv,yv=x[vis],y[vis]
    else: g=grey_at(x-Th[0],y-Th[1]); xv,yv=x,y
    Am=np.stack([np.ones_like(xv),xv,yv],1); c=np.linalg.lstsq(Am,g,rcond=None)[0]
    dv=c[1:]/(np.linalg.norm(c[1:])+1e-12); pr=xv*dv[0]+yv*dv[1]; p0,p1=pr.min(),pr.max()
    pt=lambda t:(xv.mean()+(p0+t*(p1-p0)-pr.mean())*dv[0],yv.mean()+(p0+t*(p1-p0)-pr.mean())*dv[1])
    q=lambda t:c[0]+c[1]*pt(t)[0]+c[2]*pt(t)[1]
    if np.hypot(xv.mean()-166,yv.mean()-75)<25:              # the head: lit from the upper left
        i=np.argmax(g); R=np.hypot(xv-xv[i],yv-yv[i]).max()
        defs.append(f'<radialGradient id="p{r}" gradientUnits="userSpaceOnUse" cx="{xv[i]:.1f}" cy="{yv[i]:.1f}" r="{R:.1f}"><stop offset="0" stop-color="{hexg(np.percentile(g,99))}"/><stop offset="1" stop-color="{hexg(np.percentile(g,3))}"/></radialGradient>')
    else:
        defs.append(f'<linearGradient id="p{r}" gradientUnits="userSpaceOnUse" x1="{pt(0)[0]:.1f}" y1="{pt(0)[1]:.1f}" x2="{pt(1)[0]:.1f}" y2="{pt(1)[1]:.1f}"><stop offset="0" stop-color="{hexg(q(0))}"/><stop offset="1" stop-color="{hexg(q(1))}"/></linearGradient>')
    fills.append(f'<path d="{path(m)}" fill="url(#p{r})"/>')
sil=ndimage.binary_fill_holes(ndimage.binary_closing(sil,iterations=4))
hands=[]
def pd(p): return 'M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in p)
lines=[pd(p) for n,ps in S.items() for p in ps]
json.dump(dict(defs=defs,fills=fills,lines=lines,hands=hands,sil=path(sil)),open('meet/farperson.json','w'))
print(len(fills),'areas')
