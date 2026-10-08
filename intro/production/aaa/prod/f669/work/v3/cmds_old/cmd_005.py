import numpy as np, math
from threads3d import ThreadSet
A = shot._ASSETS; lo = A['loose']
ts = ThreadSet(); lo.add_to(ts, 669)
L = shot.light_of(669); C = np.asarray(L['candle']['pos_mm'], np.float32)
print('candle', C)
t = ts.th[1]
P = t['P']; R = t['R']
z = np.clip(P[:, 2], 0, C[2] - 1); k = C[2] / (C[2] - z)
S = C[None, :2] + (P[:, :2] - C[None, :2]) * k[:, None]
print('shift mm at z', list(zip(z[::40].round(2), np.hypot(*(S - P[:, :2]).T)[::40].round(2))))
s = 5.8125
flame_r = 6.0
pen = (flame_r * z / (C[2] - z) + 0.12) * s
Rs = R * s * k
dens = np.clip(2.2 * Rs / (2.2 * Rs + 1.6 * pen), 0, 1) * np.exp(-z / 3.4)
print('Rs px', Rs[::40].round(2), 'pen px', pen[::40].round(2), 'dens', dens[::40].round(2))
print('shadow dir', ((S - P[:, :2])[::60] / (np.hypot(*(S - P[:, :2]).T)[::60, None] + 1e-9)).round(2))
