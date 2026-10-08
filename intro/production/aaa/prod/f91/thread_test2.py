import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault('F91_SHOT', 'shot_f91_t1.json')
sys.path.insert(0, HERE)
import numpy as np, cv2
import render_f91 as R
from bkit.canvas import Canvas
from chron import frontal, grade
PXB = 7.0
def variant(**kw):
    c = Canvas(120, 26, PX=PXB, seed=3, name='t', verbose=False)
    xs = np.linspace(6, 118, 400)
    u = np.clip((xs - 6 - 14.0) / 60.0, 0, 1); u = u * u * (3 - 2 * u)
    ys = 13 + 0.10*np.sin((xs-6)/23.) - 0.25*((xs-6)/144.).clip(0,1) + 0.35*np.exp(-(xs-6)/2.0) + u*(2.6*np.sin((xs-6)/47.+0.4) + 0.45*np.sin((xs-6)/17.))
    thr = np.stack([xs, ys], 1).astype(np.float32)
    c.metal_pair(thr, ties_s_mm=[8.0], group='thread', seed=5, **kw)
    m = c.m
    m['origin_mm'] = (0.0, 0.0); m['valid'] = np.ones(m['h'].shape, bool)
    out = []
    for s, wh in ((5.0, (600, 130)), ):
        fr = frontal.render(m, dict(x0_mm=0, y0_mm=0, px_per_mm=s), R.rig(dict(R.SHOT['light'], k_env=0.9)), out_wh=wh, fib_seed=3, kmap=None, edit=R.fold_field)
        out.append(grade.grade(fr['lin'], exposure=1.1, act='I', seed=3))
    fr = frontal.render(m, dict(x0_mm=0, y0_mm=6, px_per_mm=14.0), R.rig(dict(R.SHOT['light'], k_env=0.9)), out_wh=(600, 260), fib_seed=3, kmap=None)
    out.append(grade.grade(fr['lin'], exposure=1.1, act='I', seed=3))
    return out
base = dict(tie_col='#B02A20', thread_r=0.55, sep_mm=1.25, h0=0.6, hamp=0.55, gold=np.array([0.815, 0.515, 0.141], np.float32) * 0.92)
V = [variant(tie_len_mm=5.6, tie_r=0.40, tie_turns=3, tie_pitch_mm=1.7, tail_mm=6.0, ply_mm=1.5, ply_deg=44, **base),
     variant(tie_len_mm=5.6, tie_r=0.36, tie_turns=4, tie_pitch_mm=1.35, tail_mm=6.0, ply_mm=1.5, ply_deg=44, **base)]
rows = []
for v in V:
    rows.append(np.hstack([v[0], cv2.resize(v[1], (600, 260), interpolation=cv2.INTER_CUBIC)[:130]]) if False else v[0])
    rows.append(v[1])
cv2.imwrite(os.path.join(HERE, '_c', 'thread2.png'), cv2.cvtColor(np.vstack(rows), cv2.COLOR_RGB2BGR))
