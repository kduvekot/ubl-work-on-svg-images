"""The person's lines, clean: the curves (head, neck, 4, 5, 6, 7, 8) fitted to their traced lines; the
straight edges and the right side as constructed (lines/geom.json); the hands as ellipses; the bend where
a forearm's lower edge runs into its hand fitted on the left arm and moved over for the right.
Writes lines/clean.json {name: [polyline, ...]} in the clean render's px."""
import json, numpy as np
from PIL import Image
from scipy import ndimage, interpolate
import importlib.util
spec=importlib.util.spec_from_file_location('sm','lines/smooth.py'); src=open('lines/smooth.py').read()
ns={}; exec(src.split('out={}')[0],ns)                       # paths(), fit(), ellipse() from smooth.py
paths,fit,ellipse=ns['paths'],ns['fit'],ns['ellipse']
M=np.load('lines/masks.npz'); G=json.load(open('lines/geom.json'))
box=(55,20,335,330); k=3; C,S=np.cos(np.pi/6),0.5
P=lambda p:np.array(p,float)
def ell(c,a,b,ang,n=160):
    t=np.linspace(0,2*np.pi,n); A=np.radians(ang)
    return np.stack([c[0]+a*np.cos(t)*np.cos(A)-b*np.sin(t)*np.sin(A), c[1]+a*np.cos(t)*np.sin(A)+b*np.sin(t)*np.cos(A)],1)
out={}
out['1']=ellipse(M['1'])
for n in ('2','4','5','6','7','8'):
    out[n]=[fit(p) for p in paths(M[n]) if len(p)>=12]
ha,hb,hang=G['hand']; out['13']=[ell(G['hc'],ha,hb,hang)]; out['15']=[ell(G['nh'],ha,hb,hang)]
# the table edge against his belly (16): through A at 150 degrees
A=P((275,207.09)); line16=lambda x: A[1]+(A[0]-x)*S/C
out['9']=[P([(218,178),(218,line16(218))])]
out['10']=[P([(148,212),(148,G['y10'])])]
y4=max(q[:,1].max() for q in out['4']); out['11']=[P([(93,y4),G['E11']])]
out['20']=[P([G['P6'],G['Dt']])]
EB=P(G['EB']); out['22']=[P([(EB[0],G['E11'][1]+(EB[0]-93)*(G['E2b'][1]-G['E11'][1])/(G['E2b'][0]-93)),(EB[0],line16(EB[0]))])]
# the forearms: top faces and lower edges; the bend into the hand from the traced left one
lo=np.asarray(Image.open('lines/lines-only.png').convert('L'))<128
ys,xs=np.where(lo); X=xs/k+box[0]; Y=ys/k+box[1]
j=(X>=246)&(X<=292)&(Y>=255)&(Y<=276)
hc=P(G['hc']); A_=np.radians(hang); uu=(X-hc[0])*np.cos(A_)+(Y-hc[1])*np.sin(A_); vv=-(X-hc[0])*np.sin(A_)+(Y-hc[1])*np.cos(A_)
j&=np.sqrt((uu/ha)**2+(vv/hb)**2)>1.12
jm=np.zeros_like(lo); jm[ys[j],xs[j]]=True
bend=max((fit(p) for p in paths(jm)),key=len); bend=bend[np.argsort(bend[:,0])]
b0=bend[0]
end_on=lambda p,q: q                                         # (the hand drawn over the ends hides what is under it)
dbar=P((59,35))/np.hypot(59,35)
def run(p,h):           # from p along the bar's own direction, to opposite the hand's centre (under the hand)
    p=P(p); return P([p,p+dbar*((P(h)-p)@dbar)])
# left: 12a, 12b to under the hand, 12c, 12d, 12e to the bend, the bend
# 12d and 9 are one line: the inside edge of his left upper arm, down past the elbow (12c) to the table
K=(218,207); K2=(218,line16(218)+2)
out['12']=[run((234,199),hc),run(K,hc),P([(234,199),K]),P([K2,b0]),bend]
out['9']=[P([(218,178),K2])]
Th=P(G['Th']); At,Dt,E11=P(G['At']),P(G['Dt']),P(G['E11'])
nh=P(G['nh'])
out['14']=[run(At,nh),run(Dt,nh),P([At,Dt]),P([E11,b0+Th]),bend+Th]
# the table edge against his belly (16), where it shows: from 9 to the right forearm, and below it, to 22
def cross(p0,d0,q0,q1):
    q0,q1=P(q0),P(q1); M_=np.array([d0,q0-q1]).T; t=np.linalg.solve(M_,q0-P(p0)); return P(p0)+d0*t[0]
d16=P((-C,S))
a16=P((218,line16(218))); b16=cross(a16,d16,At,At+dbar)   # from where it meets 12d to the right forearm
c16=cross(a16,d16,E11,P(G['E2b'])); e16=P((EB[0],line16(EB[0])))
out['16']=[P([a16,b16]),P([c16,e16])]
# line ends that just miss the line they run into: carried on to it
allpts=lambda skip:[(n,i,q) for n,v in out.items() for i,q in enumerate(v) if (n,i)!=skip]
def nearest(p,skip):
    best=(1e9,None)
    for n,i,q in allpts(skip):
        for a,b in zip(q[:-1],q[1:]):
            ab=b-a; t=np.clip(((p-a)@ab)/(ab@ab+1e-12),0,1); r=a+t*ab; d=np.hypot(*(p-r))
            if d<best[0]: best=(d,r)
    return best
for n,v in out.items():
    if n in ('1','13','15'): continue
    for i,q in enumerate(v):
        for end in (0,-1):
            d,r=nearest(q[end],(n,i))
            if 0.5<d<9: v[i]=np.vstack([r,q]) if end==0 else np.vstack([q,r]); q=v[i]
json.dump({n:[q.tolist() for q in v] for n,v in out.items()},open('lines/clean.json','w'))
