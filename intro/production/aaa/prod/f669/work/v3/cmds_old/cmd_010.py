import __main__ as _m; R = _m.R
import numpy as np, math
import threads3d
f = 669
lfn = shot.thread_light_fn(f)
P = np.array([[300, 232, 0.3], [310, 230, 3.0]], np.float32)
print('lc at P', lfn(P))
fill = shot.NIGHT * shot.FILL_I * shot.I0
print('fill', fill)
L = shot.light_of(f); C = np.asarray(L['candle']['pos_mm'], np.float32)
ld = C - P[0]; ld /= np.linalg.norm(ld); print('light dir', ld)
lc = lfn(P)[0]
alb = np.array([0.0775, 0.0506, 0.0656], np.float32)
# yarn along +x (screen), so side vector S = (0,1,0)*? sx,sy,sz ; front = (0,0,1); tangent T=(1,0,0)
T = (1.0, 0.0, 0.0); S = (0.0, 1.0, 0.0); F = (0.0, 0.0, 1.0)
for pitch in (1.8,):
    print('q   : rgb (linear)  at several s')
    for q in np.linspace(-0.9, 0.9, 10):
        vals = []
        for s_ in np.linspace(0, pitch, 6, endpoint=False):
            o = threads3d._ply_rgb(float(q), float(s_), pitch, 0.3, S[0], S[1], S[2], F[0], F[1], F[2], T[0], T[1], T[2],
                                   float(ld[0]), float(ld[1]), float(ld[2]), float(lc[0]), float(lc[1]), float(lc[2]),
                                   float(alb[0]), float(alb[1]), float(alb[2]), float(fill[0]), float(fill[1]), float(fill[2]), 2.0)
            vals.append(round(float(o[0]), 3))
        print('%5.2f' % q, vals)
