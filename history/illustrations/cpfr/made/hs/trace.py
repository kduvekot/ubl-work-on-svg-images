# the handshake render's lines, as numbered polylines (in the render's px), over the render
import numpy as np, cv2, json
from PIL import Image, ImageDraw
from scipy import ndimage
from skimage.morphology import skeletonize
Z=3
src=np.asarray(Image.open('ris/found-handshake-551x763-pinimg.png').convert('RGBA'))
rgb=src[...,:3].copy(); rgb[src[...,3]<=128]=255
big=cv2.resize(rgb,None,fx=Z,fy=Z,interpolation=cv2.INTER_CUBIC); lab=cv2.cvtColor(big,cv2.COLOR_RGB2LAB)
alb=cv2.GaussianBlur(cv2.resize(src[...,3],None,fx=Z,fy=Z,interpolation=cv2.INTER_CUBIC),(0,0),Z*0.7)>128
e=np.zeros(alb.shape,bool)
for c in range(3): e|=cv2.Canny(cv2.GaussianBlur(lab[...,c],(7,7),2),6,16)>0
e&=ndimage.binary_erosion(alb,iterations=2*Z)
sk=skeletonize(ndimage.binary_closing(ndimage.binary_dilation(e),np.ones((5,5))))
# break at junctions so each piece is a simple chain
nb=ndimage.convolve(sk.astype(int),np.ones((3,3)),mode='constant')-1
sk2=sk&~ndimage.binary_dilation(sk&(nb>2))
lb,n=ndimage.label(sk2,structure=np.ones((3,3)))
lines=[]
for i in range(1,n+1):
    ys,xs=np.nonzero(lb==i)
    if len(ys)<8*Z: continue
    m=(lb==i).astype(np.uint8)
    cs,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    c=max(cs,key=len)[:,0]; c=c[:len(c)//2+1]
    a=cv2.approxPolyDP(c.reshape(-1,1,2),0.7*Z,False)[:,0]/Z
    lines.append(a.round(1).tolist())
json.dump(lines,open('hs/lines.json','w'))
k=2; im=Image.open('ris/found-handshake-551x763-pinimg.png').convert('RGBA'); bg=Image.new('RGB',im.size,'white'); bg.paste(im,mask=im)
bg=Image.eval(bg,lambda v:int(150+v*0.4)).resize((im.width*k,im.height*k))
d=ImageDraw.Draw(bg)
cols=[(220,0,0),(0,140,0),(0,0,220),(200,0,200),(0,150,150),(200,120,0)]
for j,l in enumerate(lines):
    d.line([(x*k,y*k) for x,y in l],fill=cols[j%6],width=2)
    x,y=l[len(l)//2]; d.text((x*k+3,y*k-5),str(j),fill=cols[j%6])
bg.save('hs/lines-numbered.png'); print(len(lines))
