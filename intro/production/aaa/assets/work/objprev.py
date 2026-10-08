import numpy as np,cv2,json,os,sys,math
def load_obj(p):
    mtl={}; cur=None
    for l in open(p.replace('.obj','.mtl')):
        t=l.split()
        if not t: continue
        if t[0]=='newmtl': cur=t[1]
        elif t[0]=='Kd': mtl[cur]=[float(x) for x in t[1:4]]
    V=[];F=[];C=[]; m=None
    for l in open(p):
        if l.startswith('v '): V.append([float(x) for x in l.split()[1:4]])
        elif l.startswith('usemtl'): m=l.split()[1]
        elif l.startswith('f '):
            F.append([int(x.split('/')[0])-1 for x in l.split()[1:4]]); C.append(mtl.get(m,[.8,.8,.8]))
    return np.array(V),np.array(F),np.array(C)
def render(p,size=360,yaw=35,pitch=28):
    V,F,C=load_obj(p)
    ya,pi=math.radians(yaw),math.radians(pitch)
    Ry=np.array([[math.cos(ya),0,math.sin(ya)],[0,1,0],[-math.sin(ya),0,math.cos(ya)]])
    Rx=np.array([[1,0,0],[0,math.cos(pi),-math.sin(pi)],[0,math.sin(pi),math.cos(pi)]])
    P=V@Ry.T@Rx.T
    tri=P[F]; n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]); n/=np.linalg.norm(n,axis=1,keepdims=True).clip(1e-12)
    L=np.array([-0.4,0.7,0.6]); L/=np.linalg.norm(L)
    sh=0.35+0.65*np.abs(n@L)
    mn=P[:,:2].min(0); mx=P[:,:2].max(0); sc=(size*0.9)/max(mx-mn).max()
    c=(mn+mx)/2
    img=np.full((size,size,3),128,np.uint8)
    order=np.argsort(tri[:,:,2].mean(1))  # far (low z?) first: camera looks along -z, so larger z closer
    for i in order:
        pts=((tri[i,:,:2]-c)*sc*np.array([1,-1])+size/2).astype(np.int32)
        col=np.clip(np.array(C[i])**(1/2.2)*sh[i]*255,0,255)[::-1]
        cv2.fillConvexPoly(img,pts,col.tolist(),lineType=cv2.LINE_AA)
    return img
if __name__=='__main__':
    info=json.load(open(sys.argv[1]+'/models.json'))
    tiles=[]
    for r in info:
        im=render(r['obj'])
        cv2.putText(im,r['name'],(6,20),cv2.FONT_HERSHEY_SIMPLEX,0.55,(255,255,255),1,cv2.LINE_AA)
        cv2.putText(im,f"{r['tris']} tris",(6,size_:=350),cv2.FONT_HERSHEY_SIMPLEX,0.45,(230,230,230),1,cv2.LINE_AA)
        tiles.append(im)
    cols=10; rows=(len(tiles)+cols-1)//cols
    sheet=np.full((rows*360,cols*360,3),128,np.uint8)
    for k,t in enumerate(tiles): sheet[(k//cols)*360:(k//cols+1)*360,(k%cols)*360:(k%cols+1)*360]=t
    cv2.imwrite(sys.argv[2],sheet,[cv2.IMWRITE_JPEG_QUALITY,88])
