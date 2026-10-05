"""The head-of-table person, completed by symmetry, and the table's edges.
Table top (clean meeting render px), from its traced isometric edges: back-left A (275,205),
back-right B (727,463), front-right Cc (505,585); the front-left corner D where the head-end edge
(from A, at 150 deg) meets the front edge (from Cc, at 210 deg): a parallelogram, as a square
table is in isometric."""
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
box=(55,20,335,330); k=3; C,S=np.cos(np.pi/6),0.5
P=lambda x,y: ((x-box[0])*k,(y-box[1])*k)
lo=np.asarray(Image.open('lines/lines-only.png').convert('L'))<128
ys,xs=np.where(lo); X=xs/k+box[0]; Y=ys/k+box[1]
ov=Image.open('lines/overlay.png').convert('RGB'); W,H=ov.size
Tb=np.load('lines/T.npy'); Th=np.load('lines/Th.npy')
def poly(pts):
    m=Image.new('L',(W,H),0); ImageDraw.Draw(m).polygon([P(*p) for p in pts],fill=255); return np.asarray(m)>0
def layer(lines,w=3):
    l=Image.new('L',(W,H),0); d=ImageDraw.Draw(l)
    for pts in lines: d.line([P(*p) for p in pts],fill=255,width=w)
    return np.asarray(l)>0
def moved(sel,T):
    m=np.zeros((H,W),bool)
    xi=np.round((X[sel]+T[0]-box[0])*k).astype(int); yi=np.round((Y[sel]+T[1]-box[1])*k).astype(int)
    ok=(xi>=0)&(xi<W)&(yi>=0)&(yi<H); m[yi[ok],xi[ok]]=True
    return ndimage.binary_dilation(m,iterations=1)
# the table
A=np.array([275.,240+(218-275)*S/C]); Cc=np.array([505.,585.])
t=np.linalg.solve(np.array([[-C,C],[S,S]]),Cc-A)          # A + t0 (-C,S) = Cc + t1 (-C,-S)
D=A+t[0]*np.array([-C,S]); B=np.array([727.,463.])
print('table corners A',A,'B',B,'Cc',Cc,'D',D.round(1),'head-end edge',round(t[0],1),'right edge',round(np.hypot(*(B-Cc)),1))
# the arms (far: as traced; near: the far one moved) hide the table edge under them
farbar=[(234,199),(293,234),(277,240),(266,269),(223,242),(221,207)]
hand=(X>272)&(X<330)&(Y>220)&(Y<280)
cxh,cyh,ah,bh,angh=300.4,249.5,25,29.3,np.radians(143.6)
u=(X-cxh)*np.cos(angh)+(Y-cyh)*np.sin(angh); v=-(X-cxh)*np.sin(angh)+(Y-cyh)*np.cos(angh)
hand&=np.abs(np.sqrt((u/ah)**2+(v/bh)**2)-1)<0.18
# the hand as an ellipse fitted to the far hand's traced outline (lines/handell.npy), moved by the
# shift that lays the far hand's outline over the visible part of the near hand
hcx,hcy,ah,bh,angd=np.load('lines/handell.npy'); angh=np.radians(angd); hc=(hcx,hcy)
pn=np.stack([X,Y],1)
nearvis=(X>180)&(X<230)&(Y>280)&(Y<322)&((((X-240)/44)**2+((Y-330)/44)**2)>1.1)
def herr(c):
    u=(X[nearvis]-c[0])*np.cos(angh)+(Y[nearvis]-c[1])*np.sin(angh); v=-(X[nearvis]-c[0])*np.sin(angh)+(Y[nearvis]-c[1])*np.cos(angh)
    r=np.sqrt((u/ah)**2+(v/bh)**2); return np.mean(np.minimum(np.abs(r-1),0.3))
nh=min(((herr((a_,b_)),a_,b_) for a_ in np.arange(200,225,0.25) for b_ in np.arange(290,315,0.25)))
print('near hand fit',round(nh[0],3),nh[1:],'shift',(nh[1]-hcx,nh[2]-hcy))
nh=nh[1:]
tt=np.linspace(0,2*np.pi,160)
ell=lambda c:[(c[0]+ah*np.cos(q)*np.cos(angh)-bh*np.sin(q)*np.sin(angh), c[1]+ah*np.cos(q)*np.sin(angh)+bh*np.sin(q)*np.cos(angh)) for q in tt]
handfar=poly(ell(hc)); np.save('lines/nearhand_c.npy',np.array(nh))
handnear=poly(ell(nh)); handnear_l=layer([ell(nh)])
# the near forearm runs on back to the elbow, under the shoulder: half the torso's depth behind its front
# (the torso's depth from its near side: front edge x 148, back edge x 93, along (-C,-S): 55/C)
depth=55/C; E=-depth/2*np.array([C,S])
Ab,Dbk,D2b=[tuple(np.array(p)+Tb+E) for p in [(234,199),(221,207),(223,242)]]
At,Dt=[tuple(np.array(p)+Tb) for p in [(234,199),(221,207)]]       # where the top face meets the body, as on the far arm
nearbar=[At,tuple(np.array((293,234))+Tb),tuple(np.array((277,240))+Tb),tuple(np.array((266,269))+Tb),D2b,Dbk,Dt]
near=poly(nearbar)|handnear
print('elbow end of the near forearm (top corners)',np.round(Ab,1),np.round(Dbk,1))
far=poly(farbar)|handfar
table=layer([[tuple(A),tuple(D)],[tuple(A),tuple(B)]])&~near&~far
# the near forearm: the far one's edges, moved (the model edges, not the traced pixels: no table bits)
sh=lambda pts:[tuple(np.array(p)+Tb) for p in pts]
# the top face stops at the body, as on the far arm; the side face (its outer side, seen on this side)
# runs on back under the shoulder to the elbow
E2=np.array((266,269))+Tb; d=E2-np.array(D2b); t11=(93-E2[0])/d[0]; E11=tuple(E2+t11*d)   # 14e back to line 11
P6=(137.,193.)                                                                            # the lower end of 6
print('14e from',np.round(E11,1),'line 8 equivalent from',P6,'to',np.round(Dt,1))
def ext(p,q):     # run on to opposite the hand's centre, under the hand; the hand hides the rest
    p=np.array(p); d=np.array(q)-p; t=((np.array(nh)-p)@d)/(d@d); return tuple(p+d*t)
# the join of the lower edge and the hand: the far arm's own traced bend and connector, moved over as the hand was
j=(X>=246)&(X<=292)&(Y>=255)&(Y<=276)
cxh,cyh=hc; uu=(X-cxh)*np.cos(angh)+(Y-cyh)*np.sin(angh); vv=-(X-cxh)*np.sin(angh)+(Y-cyh)*np.cos(angh)
j&=np.sqrt((uu/ah)**2+(vv/bh)**2)>1.12                              # not the hand's own outline
joinm=moved(j,Th)
jx=X[j].min()+Th[0]                                                  # where the bend starts: 14e runs to there
d14=np.array(E2)-np.array(E11); E2b=tuple(np.array(E11)+d14*(jx-E11[0])/d14[0])
bar=(layer([[At,ext(At,tuple(np.array((293,234))+Tb))],[Dt,ext(Dt,tuple(np.array((277,240))+Tb))],[At,Dt],
           [E11,E2b]])|joinm)&~handnear
# the torso behind the person in front
yb=263+(178-148)*S/C; yl=yb-(148-93)*S/C
body=layer([[(148,226),(148,330)],[(93,210),(93,330)]])&~near
body&=~layer([[tuple(A),tuple(D)]],w=1)|True
# below the table's head-end edge the body is hidden by the table: the body lines stop there
yy,xx=np.mgrid[0:H,0:W]; Xs=xx/k+box[0]; Ys=yy/k+box[1]
undertable=Ys>A[1]+(A[0]-Xs)*S/C
body&=~undertable
# line 8 mirrored: his left shoulder's rounded corner and the outer edge of his left arm, through
# his mid-plane (on his front: x' = 2 xm - x, shifted along (-C, S)), give the same edge on his right
xm=189.5
sel8=(X>=226)&(X<=236)&(Y>=150)&(Y<=241)        # its straight part: the front edge of his left arm, on his front
mx=2*xm-X[sel8]; my=Y[sel8]+(X[sel8]-xm)*2*S/C
m8=np.zeros((H,W),bool)
xi=np.round((mx-box[0])*k).astype(int); yi=np.round((my-box[1])*k).astype(int); ok=(xi>=0)&(xi<W)&(yi>=0)&(yi<H); m8[yi[ok],xi[ok]]=True
# drawn as the straight edge it is: a fitted vertical from its top down to the forearm
x8=float(np.median(mx)); m8=layer([[(x8,float(my.min())),(x8,330)]])&~near
print('mirrored line 8 from',(round(mx[np.argmin(my)],1),round(my.min(),1)),'to',(round(mx[np.argmax(my)],1),round(my.max(),1)))
# the forearm as it is now hides what lies behind it: top face, and the outer side face back to line 11
bd=np.array((277,240))+Tb-np.array(Dt); B11=tuple(np.array(Dt)+(93-Dt[0])/bd[0]*bd)
near2=poly([At,tuple(np.array((293,234))+Tb),tuple(np.array((277,240))+Tb),tuple(E2),E11,B11,Dt])|handnear
# 10: the inside edge of his right upper arm, down to the forearm's top (14a), as 9 runs down on the left
ad=np.array((293,234))+Tb-np.array(At); y10=At[1]+(148-At[0])*ad[1]/ad[0]
# 11 stops at the elbow, where 14e meets it
body=layer([[(148,212),(148,y10)],[(93,210),E11]])&~near2&~undertable
# the back edge of the elbow: hidden, parallel to 14c and as long, from where 14e meets 11; dotted
cv=np.array(At)-np.array(Dt); EB=tuple(np.array(E11)+cv)
dots=np.zeros((H,W),bool)
for q in np.linspace(0,1,7)[::2]:
    a=np.array(E11)+cv*q; b=np.array(E11)+cv*min(q+1/6,1); dots|=layer([[tuple(a),tuple(b)]])
# the right side of his back: from the end of 21 straight down, as 11 ran, to the table (hidden behind the forearm)
back=layer([[EB,(EB[0],400)]])&~near2&~undertable
print('elbow back edge',np.round(E11,1),'->',np.round(EB,1))
print('10 down to',round(y10,1))
import json
json.dump(dict(At=At,Dt=Dt,E11=E11,E2b=E2b,EB=EB if 'EB' in dir() else None,P6=P6,y10=y10,Th=list(Th),Tb=list(Tb),hc=list(hc),nh=list(nh),
               hand=[float(ah),float(bh),float(np.degrees(angh))],jsel=[float(v) for v in (246,292,255,276)]),open('lines/geom.json','w'),default=float)
m8r=layer([[P6,Dt]])
blue=body|bar|handnear_l|table|m8r|back
out=[]
for im in (ov, Image.open('lines/lines-only.png').convert('RGB')):
    x=np.asarray(im).copy(); x[blue]=(0,90,255); out.append(Image.fromarray(x))
np.save('lines/blue_parts.npy',np.stack([body,bar,handnear_l,table,m8r,dots,back]))
s=Image.new('RGB',(W*2+20,H),'white'); s.paste(out[0],(0,0)); s.paste(out[1],(W+20,0)); s.save('lines/completed.png')
