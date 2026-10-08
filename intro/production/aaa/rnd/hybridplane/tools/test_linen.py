import sys, time, numpy as np, cv2
sys.path.insert(0, '.')
import emb
t=time.time()
L = emb.linen_tile(40, 16, seed=3)
print('linen', time.time()-t, L['h'].min(), L['h'].max())
cv = emb.Canvas(L['S'], L['S'], 16); cv.h = L['h'].copy(); cv.alb = L['alb'].copy(); cv.T = L['T']
cv.mat[:] = emb.MAT_LINEN
emb.finish(cv, fuzz=False)
img = emb.preview(cv.h, cv.alb_final, cv.mat, cv.T, 16)
cv2.imwrite('../work/linen_prev.png', img[:400,:600,::-1])
