"""static look-dev: replay every (non-heal) event of the test/full bake into the maps, relight a window with the two candles, grade, save.
python3 lookdev.py [maps_dir] cx cz w_units out.png [gL gR] [--neutral]"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from replay import load, schedule, apply, copy_maps, et
from r25render import shade_window, grade
import numpy as np, cv2
sys.path.insert(0, RND)
from emb.fibres import make_fibres
args = [a for a in sys.argv[1:] if not a.startswith('--')]
D = args[0]; cx, cz, wu = float(args[1]), float(args[2]), float(args[3]); outp = args[4]
gL = float(args[5]) if len(args) > 5 else 1.0; gR = float(args[6]) if len(args) > 6 else 1.0
T0 = time.time()
def log(*a): print(f'[{time.time()-T0:6.1f}s]', *a, flush=True)
R, canvas, masks, hexmap = load(D)
rec = R['record']; hs = R.get('heal_start', len(rec))
m = copy_maps(canvas)
for i in range(hs):
    apply(m, rec[i], 1.0)
log('replayed', hs)
u, v = (cx - BX0) * PPU, (cz - BZ0) * PPU
w = wu * PPU; h = w * 9 / 16
reg = (int(max(0, u - w / 2)), int(max(0, v - h / 2)), int(min(W, u + w / 2)), int(min(H, v + h / 2)))
mw = {k: (m[k][reg[1]:reg[3], reg[0]:reg[2]] if isinstance(m[k], np.ndarray) and m[k].ndim >= 2 else m[k]) for k in m}
mw['PX'] = PX
fib = make_fibres(mw, density=0.9, seed=6, len_mm=(0.4, 2.0), max_fibres=900000)
if fib is not None:
    Lr = (mw['alb'][fib['root'][:, 1], fib['root'][:, 0]] @ np.array([0.2126, 0.7152, 0.0722], np.float32))
    fib['alpha'] = fib['alpha'] * np.clip((Lr - 0.03) / 0.12, 0, 1).astype(np.float32) * 0.85
    fib['P'] = fib['P'] + np.array([reg[0] / PX, reg[1] / PX, 0], np.float32)
    fib['root'] = fib['root'] + np.array([reg[0], reg[1]], np.int32)
    # shade_window expects fibres in full-map coordinates relative to the window: shift back inside
    fib['P'] = fib['P'] - np.array([reg[0] / PX, reg[1] / PX, 0], np.float32); fib['root'] = fib['root'] - np.array([reg[0], reg[1]], np.int32)
fullreg = (0, 0, reg[2] - reg[0], reg[3] - reg[1])
# pools must be evaluated at the true board position: shift via x0,y0 -> use shade_window on the window dict directly
import lightmodel as lm, shade2
from emb.shade import normals, ambient_occlusion
from emb.fibres import halo
mw['N'] = normals(mw['h'], PX, blur=0.5); mw['ao'] = ambient_occlusion(mw['h'], PX)
kL, kR, kF = lm.kmaps(mw['h'].shape, reg[0], reg[1], 1, None)
col, vis = shade2.relight2(mw, kL, kR, kF, gL, gR, N=mw['N'], ao=mw['ao'])
col = halo(col, mw, 0.3, 0.33)
def project(P):
    Q = np.empty(P.shape[:2] + (2,), np.float32); Q[..., 0] = P[..., 0] * PX; Q[..., 1] = P[..., 1] * PX
    return Q, -P[..., 2]
shade2.render_fibres2(col, fib, vis[0], vis[1], kL, kR, kF, gL, gR, project)
log('shaded', col.shape, float(col.mean()))
neutral = '--neutral' in sys.argv
img = grade(cv2.resize(col, (1920, int(1920 * col.shape[0] / col.shape[1])), interpolation=cv2.INTER_AREA), grain=0.0, neutral=neutral)
cv2.imwrite(outp, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
np.save(outp.replace('.png', '_lin.npy'), col.astype(np.float16))
log('saved', outp)
