import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/src')
import numpy as np, cv2
import shot
A = shot.assets(); lo = A['loose']
im = cv2.imread('/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/out/f669_2560x1440.png')[..., ::-1].astype(float)
v = shot.view_of(669); s = v['px_per_mm']; x0 = v['cx_mm'] - 1280 / s; y0 = v['cy_mm'] - 720 / s
W = np.array([0.2126, 0.7152, 0.0722])
rows = []
for i in lo.stubborn:
    P, _ = lo.curve(lo.blocks[i], 669)
    for p in P[8:-4:6]:
        X = int(round((p[0] - x0) * s)); Y = int(round((p[1] - y0) * s))
        c = np.median(im[Y-1:Y+2, X-1:X+2].reshape(-1, 3), 0)
        rows.append((p[2], c))
z = np.array([r[0] for r in rows]); C = np.array([r[1] for r in rows]); Yl = C @ W
lowm = z < 0.6; hi = z > 2.0
print('n', len(rows), ' lying (z<0.6mm): luma %.0f rgb %s' % (Yl[lowm].mean(), C[lowm].mean(0).round(0).tolist()))
print(' lifted (z>2mm): luma %.0f rgb %s  n=%d' % (Yl[hi].mean(), C[hi].mean(0).round(0).tolist(), hi.sum()))
