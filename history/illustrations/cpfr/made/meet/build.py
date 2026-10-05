"""The meeting table as clean vector. The people on the far side are the person at the head of the table
(lines/person2.json) mirrored; he himself as he is. Everything else (the table, the chairs, the people on the
near side, seen from behind) from the areas the clean 730 px render's own lines split it into: each area traced
smooth and filled with a grey gradient fitted to the render. Drawn: what is behind the people, the people,
then what is in front of them (an area is in front of a person where it shows inside his outline)."""
import json, numpy as np, potrace, cv2, io
from PIL import Image
from scipy import ndimage
import cairosvg
Z=3
src=np.asarray(Image.open('ris/found-meeting-730x792-pinimg.png').convert('RGBA')).astype(np.uint8)
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
H,W=lb.shape
# the people we draw ourselves: rasterise their outlines at Z
P=json.load(open('lines/person2.json')); F=json.load(open('meet/farperson.json')); hc=(165.6,75.8)
FAR=[(355,72),(485,150),(617,226)]
A=np.array([275,207.09]); B=np.array([727,463.])
def rast(svg):
    png=cairosvg.svg2png(bytestring=svg.encode(),output_width=W,output_height=H)
    return np.asarray(Image.open(io.BytesIO(png)).convert('L'))<128
wrap=lambda g:f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W/Z} {H/Z}" width="{W}" height="{H}"><rect width="100%" height="100%" fill="white"/>{g}</svg>'
silp=lambda Q=None: f'<path d="{(Q or P)["sil"]}" fill="black"/>'
far_clip=f'M0,0 L{W/Z},0 L{W/Z},{A[1]+(W/Z-A[0])*(B[1]-A[1])/(B[0]-A[0]):.1f} L{A[0]},{A[1]} L0,{A[1]} Z'
farT=[f'translate({x+hc[0]:.1f} {y-hc[1]:.1f}) scale(-1 1)' for x,y in FAR]
S_head=rast(wrap(silp()))
S_far=[rast(wrap(f'<clipPath id="c"><path d="{far_clip}"/></clipPath><g clip-path="url(#c)"><g transform="{t}">{silp(F)}</g></g>')) for t in farT]
S_people=[S_head]+S_far
yy,xx=np.mgrid[0:H,0:W]; X=xx/Z; Y=yy/Z
# in front of the person at the head: the two people on the near side whose heads overlap him (not his own near forearm)
from PIL import ImageDraw
ap=Image.new('L',(W,H),0); ImageDraw.Draw(ap).polygon([(x*Z,y*Z) for x,y in [(146,248),(204,279),(224,300),(210,320),(182,318),(146,302)]],fill=255)
E2=(((X-240)/44)**2+((Y-330)/44)**2)<1.15
FRONT=((((X-111)/43)**2+((Y-262)/50)**2)<1.15)|E2|((Y>298)&(X<218))|((Y>250)&(X<72))
FRONT&=~(np.asarray(ap)>0)|E2
def grey_at(m):
    c=big[m].astype(float); return ((0.30*c[:,0]+0.59*c[:,1]+0.11*c[:,2])/255)**0.6
def path(mask,alpha=1.0,tol=0.4):
    cs=list(potrace.Bitmap(~mask).trace(turdsize=20,alphamax=alpha,opticurve=True,opttolerance=tol))
    f=lambda p: f'{p.x/Z:.1f},{p.y/Z:.1f}'; d=[]
    for c in cs:
        d.append('M'+f(c.start_point))
        for s in c.segments: d.append(('L'+f(s.c)+'L'+f(s.end_point)) if s.is_corner else ('C'+f(s.c1)+' '+f(s.c2)+' '+f(s.end_point)))
        d.append('Z')
    return ''.join(d)
def poly(mask,eps=1.3):
    cs,_=cv2.findContours(mask.astype(np.uint8),cv2.RETR_CCOMP,cv2.CHAIN_APPROX_NONE)
    out=[]; nv=0
    for c in cs:
        if cv2.contourArea(c)<30*Z*Z: continue
        a=cv2.approxPolyDP(c,eps*Z,True)[:,0]; nv=max(nv,len(a))
        out.append('M'+' L'.join(f'{x/Z:.1f},{y/Z:.1f}' for x,y in a)+'Z')
    return ''.join(out),nv
def shape(mask):                                               # straight-edged areas (table, chairs) as polygons
    d,nv=poly(mask)
    cs,_=cv2.findContours(mask.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE); c=max(cs,key=cv2.contourArea)
    hull=cv2.convexHull(c); a=cv2.contourArea(c); ah=cv2.contourArea(hull); pr=cv2.arcLength(hull,True)
    round_=4*np.pi*ah/pr**2>0.8 and a/ah>0.9                   # heads, necks: curved
    return path(mask,0.9,1.0) if round_ or nv>16 else d
hexg=lambda v: '#'+f'{int(round(np.clip(v,0,1)*255)):02x}'*3
defs=[]; behind=[]; front=[]
for r in range(1,n+1):
    if sz[r-1]<60*Z*Z: continue
    m=lb==r
    ins=[(m&S).sum()/m.sum() for S in S_people]
    cy_,cx_=np.argwhere(m).mean(0).astype(int); infront=FRONT[cy_,cx_]
    if max(ins)>0.5 and not infront: continue                  # one of the people we draw ourselves
    occl=infront or any((m&S).sum()>40*Z*Z for S in S_people)
    m=ndimage.binary_dilation(m,iterations=3)&alb
    g=grey_at(m); xv,yv=X[m],Y[m]
    sub=slice(None,None,max(1,len(g)//4000)); g,xv,yv=g[sub],xv[sub],yv[sub]
    Am=np.stack([np.ones_like(xv),xv,yv],1); c=np.linalg.lstsq(Am,g,rcond=None)[0]
    dv=c[1:]/(np.linalg.norm(c[1:])+1e-12); pr=xv*dv[0]+yv*dv[1]; p0,p1=pr.min(),pr.max()
    pt=lambda t:(xv.mean()+(p0+t*(p1-p0)-pr.mean())*dv[0],yv.mean()+(p0+t*(p1-p0)-pr.mean())*dv[1])
    q=lambda t:c[0]+c[1]*pt(t)[0]+c[2]*pt(t)[1]
    head=abs(np.ptp(xv)-np.ptp(yv))<0.25*np.ptp(yv) and 60<np.ptp(yv)<110 and g.mean()>0.75
    if head:                                                   # a head: lit from the upper left
        i=np.argmax(g); R=np.hypot(xv-xv[i],yv-yv[i]).max()
        defs.append(f'<radialGradient id="m{r}" gradientUnits="userSpaceOnUse" cx="{xv[i]:.1f}" cy="{yv[i]:.1f}" r="{R:.1f}"><stop offset="0" stop-color="{hexg(np.percentile(g,99))}"/><stop offset="1" stop-color="{hexg(np.percentile(g,3))}"/></radialGradient>')
    else:
        defs.append(f'<linearGradient id="m{r}" gradientUnits="userSpaceOnUse" x1="{pt(0)[0]:.1f}" y1="{pt(0)[1]:.1f}" x2="{pt(1)[0]:.1f}" y2="{pt(1)[1]:.1f}"><stop offset="0" stop-color="{hexg(q(0))}"/><stop offset="1" stop-color="{hexg(q(1))}"/></linearGradient>')
    (front if occl else behind).append(f'<path d="{shape(m)}" fill="url(#m{r})"/>')
outline=path(ndimage.binary_fill_holes(alb),alpha=0.9,tol=1.0)
I,O=1.81/0.755,5.66/0.755
def person(t=None,clip=False,P=P):
    g=(f'<g fill="none" stroke="#262626" stroke-width="{I}" stroke-linejoin="round" stroke-linecap="round">'+''.join(f'<path d="{d}"/>' for d in P['lines'])+'</g>'
       +f'<g stroke="#262626" stroke-width="{I}">'+''.join(P['hands'])+'</g>'
       +f'<path d="{P["sil"]}" fill="none" stroke="#262626" stroke-width="{O}" stroke-linejoin="round"/>')
    g=''.join(P['fills'])+g
    return g
lines=lambda ps: f'<g fill="none" stroke="#262626" stroke-width="{I}" stroke-linejoin="round">'+''.join(p.replace('fill="url','data-f="') for p in ps)+'</g>'
x0,y0,w,h=1,24,728,766
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 561 595" width="561" height="595">
 <!-- A meeting at a table (the Visio work-flow shape of the UBL CPFR figures), in grey. The people on the far side
      are the person at the head of the table mirrored; the table, the chairs and the people on the near side are the
      areas of a clean render, each filled with its own gradient. Isometric, 30 degrees. -->
 <defs>{''.join(P['defs'])}{''.join(d.replace('id="p','id="f') for d in F['defs'])}{''.join(defs)}<clipPath id="farclip"><path d="{far_clip}"/></clipPath></defs>
 <g transform="matrix(0.755 0 0 0.755 6 -8)">   <!-- the render placed as the original: fitted on the outlines -->
 <g stroke="#262626" stroke-width="{I}" stroke-linejoin="round">{''.join(behind)}</g>
 <g clip-path="url(#farclip)">{''.join(f'<g transform="{t}">{person(P=F)}</g>' for t in farT)}</g>   <!-- copies, not <use>: the UBL export allows no <use> -->
 {person()}
 <g stroke="#262626" stroke-width="{I}" stroke-linejoin="round">{''.join(front)}</g>
 <path d="{outline}" fill="none" stroke="#262626" stroke-width="{O}" stroke-linejoin="round"/>
 </g>
</svg>'''
open('v2/meeting-clean.svg','w').write(svg)
print(len(behind),'behind',len(front),'in front',len(svg)//1024,'KB')
