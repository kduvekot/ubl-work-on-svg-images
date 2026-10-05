"""Every line of the head-of-table person (and the table), in its own colour with its number: the
traced lines assigned to the nearest of the named lines below, the constructed (blue) lines as built."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
box=(55,20,335,330); k=3
def ell(c,a,b,ang=0,n=200):
    t=np.linspace(0,2*np.pi,n); A=np.radians(ang)
    return [(c[0]+a*np.cos(u)*np.cos(A)-b*np.sin(u)*np.sin(A), c[1]+a*np.cos(u)*np.sin(A)+b*np.sin(u)*np.cos(A)) for u in t]
hx,hy,ha,hb,hang=np.load('lines/handell.npy')
LINES={
 1:('head',[ell((165.9,75.5),41.8,47.6)]),
 2:('neck',[[(142,114),(142,130),(165,135),(188,130),(188,114)]]),
 3:('straight line from the neck, up-left',[[(140,114),(92,139)]]),
 4:('curve from the neck down to the outer edge of his right arm',[[(146,124),(122,138),(104,158),(95,180),(93,200)]]),
 5:('small lobe arc',[[(96,174),(110,171),(124,176),(133,185),(137,193)]]),
 6:('big lobe curve',[[(137,193),(150,170),(170,150),(195,137),(222,133)]]),
 7:('straight line from the neck to his left shoulder corner',[[(190,114),(222,133)]]),
 8:('left shoulder corner and the outer edge of his left arm',[[(222,133),(229,139),(232,152),(233,240)]]),
 9:('inner edge of his left upper arm',[[(218,178),(218,240)]]),
 10:('inner edge of his right upper arm',[[(148,212),(148,232)]]),
 11:('outer edge of his right arm',[[(93,195),(93,215)]]),
 12:('left forearm',[[(234,199),(293,234)],[(221,207),(277,240)],[(223,242),(266,269)],[(221,207),(223,242)]]),
 13:('left hand',[ell((hx,hy),ha,hb,hang)]),
 16:('table edge, head end',[[(218,240),(178,263)]]),
 17:('table back edge',[[(276,207),(335,240)]]),
 18:('chair-back line right of the head',[[(206,76),(220,89),(222,132)]]),
 19:('chair panel top edge',[[(92,139),(60,157)]]),
}
lo=np.asarray(Image.open('lines/lines-only.png').convert('RGB')).astype(int); H,W=lo.shape[:2]
black=lo.sum(2)<300
ys,xs=np.where(black); X=xs/k+box[0]; Y=ys/k+box[1]
def dist_to(pts,px,py):
    best=np.full(len(px),1e9)
    for poly in pts:
        p=np.array(poly,float)
        for a,b in zip(p[:-1],p[1:]):
            ab=b-a; t=np.clip(((px-a[0])*ab[0]+(py-a[1])*ab[1])/(ab@ab+1e-9),0,1)
            best=np.minimum(best,np.hypot(px-(a[0]+t*ab[0]),py-(a[1]+t*ab[1])))
    return best
keys=list(LINES); D=np.stack([dist_to(LINES[n][1],X,Y) for n in keys]); j=D.argmin(0); ok=D.min(0)<9
masks={n:np.zeros((H,W),bool) for n in keys}
for i,n in enumerate(keys): masks[n][ys[ok&(j==i)],xs[ok&(j==i)]]=True
# the constructed lines
body,bar,hand,table,m8r,dots,back=np.load('lines/blue_parts.npy')
yy,xx=np.mgrid[0:H,0:W]; XS=xx/k+box[0]
masks[10]|=body&(np.abs(XS-148)<4); masks[11]|=body&(np.abs(XS-93)<4)
masks[14]=bar; masks[15]=hand; masks[20]=m8r; masks[22]=back
tl=table; Ab=np.array([275.,207.1])
masks[16]|=tl&((yy/k+box[1])>Ab[1]+(Ab[0]-XS)*0.5774-6)&(XS<Ab[0]+2)
masks[17]=tl&~masks[16]|masks[17]
LINES[14]=('right forearm (constructed)',[]); LINES[20]=('right counterpart of 8',[]); LINES[21]=('back edge of the right elbow (hidden)',[]); LINES[22]=('right side of his back',[]); LINES[15]=('right hand (constructed)',[])
# the seat's edges, not the person's: assigned, then left out
DROP={3,18,19,21}
for n in DROP: masks.pop(n, None)
import colorsys
order=sorted(masks)
cols={n:tuple(int(255*c) for c in colorsys.hsv_to_rgb((i*0.137)%1,0.95,0.8)) for i,n in enumerate(sorted(list(order)+list(DROP)))}
img=np.asarray(Image.open('lines/overlay.png').convert('RGB')).astype(float)
base=(img*0.3+255*0.7).astype(np.uint8)
# the overlay's own red is replaced: fade it out completely where it was red
red=(img[...,0]>200)&(img[...,1]<60)&(img[...,2]<60); base[red]=255
# the seat's areas, which those edges bounded, go too: the panel left of him (out to line 4 / 11)
# and the seat back right of his head (between the head, line 7 and line 18)
seat=Image.new('L',(W,H),0); ds=ImageDraw.Draw(seat)
P=lambda x,y: ((x-box[0])*k,(y-box[1])*k)
ds.polygon([P(*p) for p in [(30,20),(150,20),(150,112),(140,114),(122,137),(104,157),(95,180),(92,200),(92,340),(30,340)]],fill=255)
ds.polygon([P(*p) for p in [(196,40),(240,40),(240,140),(222,133),(190,114)]],fill=255)
headm=Image.new('L',(W,H),0); ImageDraw.Draw(headm).polygon([P(*p) for p in LINES[1][1][0]],fill=255)
seat=(np.asarray(seat)>0)&~(np.asarray(headm)>0)
base[seat]=255
out=base.copy(); only=np.full_like(base,255)
for n in order:
    t=ndimage.binary_dilation(masks[n],iterations=1 if n==21 else 2); out[t]=cols[n]; only[t]=cols[n]
f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',22)
LAB={1:(118,40),2:(165,143),3:(112,118),4:(112,150),5:(112,182),6:(178,158),7:(210,116),8:(243,170),9:(212,210),10:(140,222),
     11:(85,250),12:(262,212),13:(318,258),14:(165,276),15:(220,318),16:(196,262),17:(306,216),18:(230,95),19:(72,140),20:(128,222),21:(82,240),22:(116,282)}
res=[]
for arr in (out,only):
    im=Image.fromarray(arr); d=ImageDraw.Draw(im)
    for n,(x,y) in LAB.items():
        if n in DROP: continue
        X_,Y_=(x-box[0])*k,(y-box[1])*k
        d.ellipse([X_-17,Y_-17,X_+17,Y_+17],fill=cols[n],outline=(0,0,0),width=2)
        t=str(n); w=d.textlength(t,font=f); d.text((X_-w/2,Y_-14),t,fill=(255,255,255),font=f,stroke_width=2,stroke_fill=(0,0,0))
    res.append(im)
s=Image.new('RGB',(W*2+20,H),'white'); s.paste(res[0],(0,0)); s.paste(res[1],(W+20,0)); s.save('lines/coloured.png')
for n in order: print(n, LINES[n][0], int(masks[n].sum()))
np.savez('lines/masks.npz',**{str(n):masks[n] for n in masks})
