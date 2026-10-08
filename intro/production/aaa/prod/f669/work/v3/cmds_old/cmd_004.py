import numpy as np, cv2
from threads3d import ThreadSet
A = shot._ASSETS; lo = A['loose']
ts = ThreadSet(); lo.add_to(ts, 669)
s = 5.8125; x0 = 300 - 640 / s; y0 = 232 - 360 / s
im = cv2.imread(os.path.join(W, 's2_strands.png'))[..., ::-1].astype(float)
for k, t in enumerate(ts.th):
    P = t['P']; n = len(P)
    pts = []
    for j in range(5, n - 5, max(1, n // 12)):
        X = int(round((P[j, 0] - x0) * s)); Y = int(round((P[j, 1] - y0) * s))
        if 3 <= X < 1277 and 3 <= Y < 717:
            pts.append((j, X, Y, round(float(P[j, 2]), 2), im[Y, X].round(0)))
    print('thread', k, 'R', t['R'].mean().round(3), 'kind', t['kind'], 'n', n)
    for q in pts: print('   ', q)
