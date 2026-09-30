"""WMF to SVG: the clip art of the deck (polygons and polylines, pens and
brushes, fill modes) as SVG, in its own coordinates.

    python3 wmf2svg.py            <WORK>/pictures/*.wmf -> <WORK>/svg/*.svg
"""
import struct, sys, glob, os
from paths import WORK, work
def conv(fn,out):
    d=open(fn,'rb').read(); off=18
    objs={}; pen=brush=None; fill='nonzero'; org=(0,0); ext=(1,1); els=[]
    def free():
        i=0
        while i in objs: i+=1
        return i
    def col(v): return '#%02x%02x%02x'%(v&255,(v>>8)&255,(v>>16)&255)
    while off<len(d):
        sz,f=struct.unpack_from('<IH',d,off); p=off+6
        if f==0x20b: y,x=struct.unpack_from('<hh',d,p); org=(x,y)
        elif f==0x20c: h,w=struct.unpack_from('<hh',d,p); ext=(w,h)
        elif f==0x106: fill='evenodd' if struct.unpack_from('<H',d,p)[0]==1 else 'nonzero'
        elif f==0x2fa: st,w,_,c=struct.unpack_from('<HhhI',d,p); objs[free()]=('pen',None if st&0xf==5 else col(c),w)
        elif f==0x2fc: st,c,_=struct.unpack_from('<HIH',d,p); objs[free()]=('brush',None if st==1 else col(c))
        elif f==0x12d:
            o=objs[struct.unpack_from('<H',d,p)[0]]
            if o[0]=='pen': pen=o
            else: brush=o
        elif f==0x1f0: objs.pop(struct.unpack_from('<H',d,p)[0],None)
        elif f in(0x324,0x325):
            n=struct.unpack_from('<h',d,p)[0]; pts=struct.unpack_from('<%dh'%(2*n),d,p+2)
            pd='M'+' '.join('%d,%d'%(pts[i],pts[i+1]) for i in range(0,2*n,2))+(' Z' if f==0x324 else '')
            s='fill="%s" fill-rule="%s"'%((brush[1] if brush and brush[1] and f==0x324 else 'none'),fill)
            s+=' stroke="%s" stroke-width="%d"'%(pen[1],max(pen[2],1)) if pen and pen[1] else ' stroke="none"'
            els.append('<path d="%s" %s/>'%(pd,s))
        elif f==0: break
        off+=sz*2
    open(out,'w').write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d"><g transform="scale(%d,%d) translate(%d,%d)">\n%s\n</g></svg>\n'%(abs(ext[0]),abs(ext[1]),1 if ext[0]>0 else -1,1 if ext[1]>0 else -1,-org[0],-org[1],'\n'.join(els)))
    return len(els),org,ext
for f in sorted(glob.glob(os.path.join(WORK, 'pictures', '*.wmf'))):
    out = work('svg', os.path.basename(f)[:-4] + '.svg')
    print(out, conv(f, out))
