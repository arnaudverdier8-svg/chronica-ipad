import cv2, numpy as np, sys
for path in sys.argv[1:]:
    cap=cv2.VideoCapture(path); fr=[]
    while True:
        ok,f=cap.read()
        if not ok: break
        fr.append(cv2.cvtColor(f,cv2.COLOR_BGR2GRAY).astype(np.float32))
    fr=np.array(fr); n=len(fr)
    means=fr.mean(axis=(1,2))
    # temporal second diff
    d2=[]; d1=[]; dup=0
    for i in range(1,n-1):
        a=np.abs(fr[i]-0.5*(fr[i-1]+fr[i+1])).mean(); d2.append(a)
    for i in range(1,n):
        a=np.abs(fr[i]-fr[i-1]).mean(); d1.append(a)
        if a<0.05: dup+=1
    # optical-flow-compensated residual high freq
    res=[]
    for i in range(1,n,max(1,n//20)):
        p=fr[i-1].astype(np.uint8); c=fr[i].astype(np.uint8)
        flow=cv2.calcOpticalFlowFarneback(p,c,None,0.5,4,25,3,5,1.2,0)
        h,w=p.shape; gx,gy=np.meshgrid(np.arange(w),np.arange(h))
        warped=cv2.remap(c.astype(np.float32),(gx+flow[...,0]).astype(np.float32),(gy+flow[...,1]).astype(np.float32),cv2.INTER_LINEAR)
        r=np.abs(warped-fr[i-1])[40:-40,40:-40]
        res.append(r.mean())
    print(path.split('/')[-1], 'n',n,'dupFrames',dup,'meanLum range %.1f-%.1f'%(means.min(),means.max()),'max |dLum| %.2f'%np.abs(np.diff(means)).max(),'d1 mean %.2f'%np.mean(d1),'d2 mean %.2f max %.2f'%(np.mean(d2),np.max(d2)),'flowres %.2f max %.2f'%(np.mean(res),np.max(res)))
