"""The two people shaking hands, as clean vector, in the clean 551 px render's px.
Right (facing us): the seated person at the head of the meeting table, mirrored and 1.26x (fitted on head, neck
and shoulders: mean 0.5 px): his head, neck, shoulder and chest lines, the arm reaching out (the forearm that
lay on the table) and its hand; his other arm hangs down (from the render), his legs and feet from the render.
Left (from behind): the same head, neck and hands; arms, legs and feet from the render's lines.
The lines split them into areas, each filled with a grey gradient fitted to the render; lines drawn thin over
them, the outline thick. Writes hs/people.json (defs, fills, lines, outline)."""
import json, numpy as np, potrace, cv2
from PIL import Image, ImageDraw
from scipy import ndimage, optimize
S=json.load(open('lines/clean.json')); L=json.load(open('hs/lines.json'))
src=np.asarray(Image.open('ris/found-handshake-551x763-pinimg.png').convert('RGBA'))
W0,H0=551,763; k=4; W,H=W0*k,H0*k
A=np.array
def TR(p): p=A(p,float); return np.c_[457+1.26*(165.6-p[:,0]),91+1.26*(p[:,1]-75.8)]
def chaikin(p,n=2):
    p=A(p,float)
    for _ in range(n):
        q=[p[0]]
        for a,b in zip(p[:-1],p[1:]): q+= [0.75*a+0.25*b,0.25*a+0.75*b]
        q.append(p[-1]); p=A(q)
    return p
def ell(c,ang,a=25.07,b=33.25,n=120,t0=0,t1=2*np.pi):
    t=np.linspace(t0,t1,n); R=np.radians(ang)
    return np.c_[c[0]+a*np.cos(t)*np.cos(R)-b*np.sin(t)*np.sin(R), c[1]+a*np.cos(t)*np.sin(R)+b*np.sin(t)*np.cos(R)]
def inside(p,c,ang,a=25.07,b=33.25):
    R=np.radians(ang); d=p-c; u=d[:,0]*np.cos(R)+d[:,1]*np.sin(R); v=-d[:,0]*np.sin(R)+d[:,1]*np.cos(R)
    return (u/a)**2+(v/b)**2<1
# --- the right person
R=[TR(p) for n in ('1','2','4','5','6','7','8','9','12') for p in S[n]]
# the strip between his legs: its top is behind the documents' far corner in the figure, so it starts below that
R+=[chaikin(L[19]), A([[438.4,429],[435.0,564.0]]), A([[450.2,437]]+L[36][3:]), A(L[47]), A(L[61])]
HB=((274.41,328.94),60.62)                 # his hand in the handshake (behind the other)
HR=((519.88,451.37),186.31)                # his hanging hand
# --- the left person: the head and neck fitted on the render (the same head, 1.26x)
a=src[...,3]>128; edge=a^ndimage.binary_erosion(a); dt=ndimage.distance_transform_edt(~edge)
head=A(S['1'][0],float)
def hp(c): return np.c_[c[0]+1.26*(head[:,0]-165.6),c[1]+1.26*(head[:,1]-75.8)]
def cost(c):
    q=hp(c); q=q[q[:,1]<c[1]+20]           # the top of the head: the outline there
    return np.minimum(dt[np.clip(q[:,1].astype(int),0,H0-1),np.clip(q[:,0].astype(int),0,W0-1)],6).mean()
cL=optimize.minimize(cost,[95,181],method='Nelder-Mead').x
def TL(p): p=A(p,float); return np.c_[cL[0]+1.26*(p[:,0]-165.6),cL[1]+1.26*(p[:,1]-75.8)]
Lf=[TL(p) for n in ('1','2') for p in S[n]]
def extend(p,t):                            # a line carried on, along its last piece, by t px
    d=p[-1]-p[-2]; d=d/np.linalg.norm(d); return np.vstack([p,p[-1]+d*t])
lower=extend(A(L[39]+L[34]),40)              # the forearm's lower edge, on under the hand
top=extend(A(L[29])[::-1],30)[::-1]           # its top face's lower edge, likewise
Lf+=[A(L[14]), chaikin([[22.7,260],[48.3,262.7],[68.3,271]]),
     chaikin(L[24][:8]), chaikin(L[33]), A([[133.0,458.7],[135,459]]), lower, top,
     A(L[28]), chaikin(L[49]), A(L[51]),
     A([[74,509],[73,513.3],[71.7,589.3],[68.7,674],[68.7,704.3]]), A([[74,509],[82.3,513.3],[83.7,516],[85,582.7],[87.5,727]]),
     A(L[44]), A(L[66])]
HF=((257.52,351.15),64.45)                 # his hand in the handshake (in front)
hands=[('F',HF,ell(*HF)),('B',HB,ell(*HB)),('R',HR,ell(*HR))]
def dense(p,step=0.5):
    out=[p[0]]
    for a,b in zip(p[:-1],p[1:]):
        n=max(1,int(np.linalg.norm(b-a)/step)); out+=[a+(b-a)*t for t in np.linspace(0,1,n+1)[1:]]
    return A(out)
def clip(p,hs):                             # leave out what is under the hands in front of it
    p=dense(A(p,float))
    keep=np.ones(len(p),bool)
    for _,(c,ang),_ in hs: keep&=~inside(p,A(c),ang)
    out=[]; cur=[]
    for q,kp in zip(p,keep):
        if kp: cur.append(q)
        elif cur: out.append(A(cur)); cur=[]
    if cur: out.append(A(cur))
    return [o for o in out if len(o)>=2]
lines=[]
for p in R+Lf: lines+=clip(p,hands)
hl=[clip(hands[0][2],[]), clip(hands[1][2],[hands[0]]), clip(hands[2][2],[])]
handlines=[q for h in hl for q in h]
# --- areas
img=Image.new('L',(W,H),0); d=ImageDraw.Draw(img)
for p in lines+handlines: d.line([(x*k,y*k) for x,y in p],fill=255,width=k+1)
Lm=ndimage.binary_closing(np.asarray(img)>0,iterations=2)
# where a line ends in the open it is carried on, unseen, to the next line or the outline (for the areas only)
wall=Lm|~ndimage.binary_erosion(ndimage.binary_fill_holes(cv2.resize(cv2.GaussianBlur(src[...,3],(0,0),0.7),(W,H),interpolation=cv2.INTER_CUBIC)>128),iterations=2)
ext=Image.new('L',(W,H),0); de=ImageDraw.Draw(ext)
for p in lines:
    if len(p)<3: continue
    for e0,e1 in ((p[-1],p[max(0,len(p)-6)]),(p[0],p[min(len(p)-1,5)])):
        dv=e0-e1; nrm=np.linalg.norm(dv)
        if nrm<1e-6: continue
        dv=dv/nrm; hit=None
        for t in np.arange(1.5,60,0.25):
            q=e0+dv*t; xi,yi=int(q[0]*k),int(q[1]*k)
            if not(0<=xi<W and 0<=yi<H): break
            if wall[yi,xi]: hit=q; break
        if hit is not None: de.line([(e0[0]*k,e0[1]*k),(hit[0]*k,hit[1]*k)],fill=255,width=k+1)
Lm|=np.asarray(ext)>0
al=cv2.GaussianBlur(cv2.resize(src[...,3],(W,H),interpolation=cv2.INTER_CUBIC),(0,0),1.6*k)>128
al=ndimage.binary_fill_holes(al)
lab,n=ndimage.label(al&~Lm); sz=ndimage.sum(al&~Lm,lab,range(1,n+1))
keep=[i for i in range(1,n+1) if sz[i-1]>=25*k*k]
grow=np.where(np.isin(lab,keep),lab,0)
_,(iy,ix)=ndimage.distance_transform_edt(grow==0,return_indices=True); full=grow[iy,ix]; full[~al]=0
rgb=src[...,:3].astype(float)
yy,xx=np.mgrid[0:H,0:W]
hexg=lambda v:'#'+f'{int(round(np.clip(v,0,1)*255)):02x}'*3
def path(mask):
    cs=list(potrace.Bitmap(~mask).trace(turdsize=30,alphamax=1.0,opticurve=True,opttolerance=0.8))
    f=lambda p:f'{p.x/k:.1f},{p.y/k:.1f}'; o=[]
    for c in cs:
        o.append('M'+f(c.start_point))
        for s in c.segments: o.append(('L'+f(s.c)+'L'+f(s.end_point)) if s.is_corner else ('C'+f(s.c1)+' '+f(s.c2)+' '+f(s.end_point)))
        o.append('Z')
    return ''.join(o)
defs=[]; fills=[]
for r in keep:
    m=full==r
    core=(lab==r)
    ys,xs=np.nonzero(core); sel=slice(None,None,max(1,len(ys)//4000)); ys,xs=ys[sel],xs[sel]
    xv,yv=xs/k,ys/k; c=rgb[np.clip((yv).astype(int),0,H0-1),np.clip((xv).astype(int),0,W0-1)]
    g=((0.30*c[:,0]+0.59*c[:,1]+0.11*c[:,2])/255)**0.6
    ok=g>0.55                                 # not the render's own dark outline
    if ok.sum()>20: xv,yv,g=xv[ok],yv[ok],g[ok]
    Am=np.stack([np.ones_like(xv),xv,yv],1); cf=np.linalg.lstsq(Am,g,rcond=None)[0]
    dv=cf[1:]/(np.linalg.norm(cf[1:])+1e-12); pr=xv*dv[0]+yv*dv[1]; p0,p1=pr.min(),pr.max()
    pt=lambda t:(xv.mean()+(p0+t*(p1-p0)-pr.mean())*dv[0],yv.mean()+(p0+t*(p1-p0)-pr.mean())*dv[1])
    q=lambda t:cf[0]+cf[1]*pt(t)[0]+cf[2]*pt(t)[1]
    isheadlike=np.ptp(xv)<120 and np.ptp(yv)<130 and g.mean()>0.78 and abs(np.ptp(xv)-np.ptp(yv))<0.3*np.ptp(yv)
    if isheadlike:
        i=np.argmax(g); Rr=np.hypot(xv-xv[i],yv-yv[i]).max()
        defs.append(f'<radialGradient id="s{r}" gradientUnits="userSpaceOnUse" cx="{xv[i]:.1f}" cy="{yv[i]:.1f}" r="{Rr:.1f}"><stop offset="0" stop-color="{hexg(np.percentile(g,99))}"/><stop offset="1" stop-color="{hexg(np.percentile(g,3))}"/></radialGradient>')
    else:
        defs.append(f'<linearGradient id="s{r}" gradientUnits="userSpaceOnUse" x1="{pt(0)[0]:.1f}" y1="{pt(0)[1]:.1f}" x2="{pt(1)[0]:.1f}" y2="{pt(1)[1]:.1f}"><stop offset="0" stop-color="{hexg(q(0))}"/><stop offset="1" stop-color="{hexg(q(1))}"/></linearGradient>')
    fills.append(f'<path d="{path(ndimage.binary_dilation(m,iterations=k)&al)}" fill="url(#s{r})"/>')
def simp(p):
    if len(p)<3: return p
    return cv2.approxPolyDP(A(p,np.float32).reshape(-1,1,2),0.25,False)[:,0]
pd=lambda p:'M'+' L'.join(f'{x:.1f},{y:.1f}' for x,y in simp(p))
json.dump(dict(defs=defs,fills=fills,lines=[pd(p) for p in lines+handlines],outline=path(al)),open('hs/people.json','w'))
col=np.random.RandomState(3).randint(80,255,(full.max()+1,3)).astype(np.uint8); col[0]=255
dbg=col[full]; dbg[Lm]=0
Image.fromarray(dbg).resize((W0*2,H0*2)).save('hs/areas.png')
print(len(fills),'areas',len(lines)+len(handlines),'lines', 'left head at',cL.round(1))
