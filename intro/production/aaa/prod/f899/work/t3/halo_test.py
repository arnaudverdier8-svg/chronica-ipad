import os, sys, json
sys.path.insert(0,'/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f899/src')
import bkit, numpy as np, cv2
from chron.maps import MapSet
from chron import shade, frontal, grade
ROOT='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f899'
shot=json.load(open(ROOT+'/shot_f899.json'))
ms=MapSet(ROOT+'/maps/war_ground')
H=shot['hearth']
rig=shade.rig(az=H['az'],el=H['el'],K=H['K'],key_i=H['key_i'],tint=H['tint'],fill_ratio=1e9,fill_i=0.0,rim_i=0.0)
rigf=shade.rig(az=90,el=60,K=5200,key_i=0.0,tint=0.1,fill_i=0.5,fill_K=5200,rim_i=0.0)
view=dict(x0_mm=500,y0_mm=180,px_per_mm=8)
for name,r,fib in (('h_fib',rig,'auto'),('h_nofib',rig,None),('f',rigf,None)):
    fr=frontal.render(ms,view,r,out_wh=(640,400),fib=fib,fib_seed=899)
    img=grade.grade(fr['lin'],exposure=0.8,act='III',seed=1,grain=0)
    cv2.imwrite(f'{ROOT}/work/t3/halo_{name}.png',cv2.cvtColor(img,cv2.COLOR_RGB2BGR))
print('ok')
