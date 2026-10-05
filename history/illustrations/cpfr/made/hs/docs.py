# the stack of documents of the handshake, measured on the prd1 master (ref px): three sheets, the top one
# with five lines of text and its far right corner folded over
import numpy as np
A=np.array
L=A([127.5,339]); B=A([276,254]); F=A([245,402.5]); R=B+(F-L)
P=lambda *ps:' L'.join(f'{p[0]:.1f},{p[1]:.1f}' for p in ps)
out=['<g stroke="#262626" stroke-width="5" stroke-linejoin="round" stroke-linecap="round">']
for dy,fill in ((61,'#dcdcdc'),(31.5,'#e6e6e6')):              # the two sheets under it
    o=A([0,dy]); out.append(f'  <path d="M{P(L+o,B+o,R+o,F+o)} Z" fill="{fill}"/>')
# the top sheet, its far right corner folded over as on a note: a cut across the corner (both sides the same
# length, so square to the sheet), the folded-back triangle lying on the sheet
d=40
C1=R+d*(B-R)/np.linalg.norm(B-R); C2=R+d*(F-R)/np.linalg.norm(F-R)
# the flap not pressed flat: turned over the fold line by FOLD degrees (180 = flat on the sheet), so it stands up
FOLD=165
c30=np.cos(np.pi/6)
w=lambda q:np.array([(q[0]/c30+2*q[1])/2,(2*q[1]-q[0]/c30)/2,0.0])     # screen -> on the sheet (height 0)
scr=lambda W:np.array([(W[0]-W[1])*c30,(W[0]+W[1])/2-W[2]])
a,b,r=w(C1),w(C2),w(R); k_=(b-a)/np.linalg.norm(b-a); v=r-a
def rot(t):
    t=np.radians(t); return a+v*np.cos(t)+np.cross(k_,v)*np.sin(t)+k_*(k_@v)*(1-np.cos(t))
Rw=rot(FOLD) if rot(FOLD)[2]>0 else rot(-FOLD)
Rf=scr(Rw)
out.append(f'  <path d="M{P(L,B,C1,C2,F)} Z" fill="url(#hs-sheet)"/>')
out.append(f'  <path d="M{P(C1,C2,Rf)} Z" fill="#d2d2d2" stroke-width="3.5"/>')
out.append('</g>')
# its text: five lines, the top one shorter
txt=[((171.2,329.3),(255.8,378.4)),((193.8,318.4),(277,366.9)),((215,304.6),(298.4,353.3)),((237.6,292.6),(320.8,340.6)),((258.2,280.7),(314,313))]
out.append('<g stroke="#555555" stroke-width="3.6" stroke-linecap="round">'+''.join(
    f'<line x1="{a[0]+1.7:.1f}" y1="{a[1]+1:.1f}" x2="{b[0]-1.7:.1f}" y2="{b[1]-1:.1f}"/>' for a,b in txt)+'</g>')
DOCS=' <!-- the stack of documents -->\n '+'\n '.join(out)+'\n'
