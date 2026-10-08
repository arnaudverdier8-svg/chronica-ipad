import numpy as np,json,glob,os
from PIL import Image
T='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/assets/tex/figures/'
for fn in sorted(glob.glob('raw/*_normal.rgba')):
    n=os.path.basename(fn)[:-5]
    j=json.load(open(f'raw/{n}.json'))
    a=np.fromfile(fn,dtype=np.uint8).reshape(j['h'],j['w'],4).astype(np.float32)
    x=a[...,0]/127.5-1; y=a[...,3]/127.5-1
    z=np.sqrt(np.clip(1-x*x-y*y,0,1))
    out=np.stack([a[...,0],a[...,3],np.round((z*0.5+0.5)*255)],-1).astype(np.uint8)
    alb=np.array(Image.open(T+n.replace('_normal','_albedo')+'.png'))
    out=np.dstack([out,alb[...,3]])
    Image.fromarray(out,'RGBA').save(T+n+'.png')
    print(n, out.shape, 'zmean',z[alb[...,3]>128].mean().round(3))
