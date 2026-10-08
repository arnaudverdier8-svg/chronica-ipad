import numpy as np, sys
lin=np.load(sys.argv[1]).astype(np.float32)
Y=(lin*[0.2126,0.7152,0.0722]).sum(-1)
s=5.8125; x0=307.7129-1280/s; y0=173-720/s
def box(x,y,r=6):
    X=int((x-x0)*s); Yp=int((y-y0)*s); R=int(r*s)
    return np.median(Y[Yp-R:Yp+R, X-R:X+R])
v=box(297,215)
print('void %.3f' % v)
for nm,x,y in [('void top',297,165),('void bottom',297,250),('red face',198,148),('blue face',396,148),('gold face',126,158),('green face',472,156),('crown',294,128),('bg UL',150,80),('bg UR',450,80),('table mid',300,285)]:
    m=box(x,y); print('%-12s %.3f EV %.2f' % (nm, m, np.log2(m/v)))
