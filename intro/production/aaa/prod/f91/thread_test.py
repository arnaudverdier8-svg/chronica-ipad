import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'kit'))
import bkit
import numpy as np, cv2
from bkit.canvas import Canvas
from bkit import geom as G
from chron import frontal, grade
import render_f91 as R
def variant(**kw):
    c = Canvas(110, 24, PX=10.0, seed=3, name='t', verbose=False)
    xs = np.linspace(10, 108, 300)
    ys = 12 + 0.1*np.sin(xs/23.) + 0.35*np.exp(-(xs-10)/2) + np.clip((xs-24)/60,0,1)**2*(3-2*np.clip((xs-24)/60,0,1))*1.2*np.sin((xs-10)/61+0.4)
    thr = np.stack([xs, ys], 1).astype(np.float32)
    c.metal_pair(thr, ties_s_mm=[7.5], tie_col='#C0281F', group='thread', seed=5, **kw)
    m = c.m
    # embed in linen with the occlusion irrelevant
    m['origin_mm'] = (0.0, 0.0); m['valid'] = np.ones(m['h'].shape, bool)
    fr = frontal.render(m, dict(x0_mm=0, y0_mm=0, px_per_mm=5.0), R.rig(), out_wh=(550, 120), fib_seed=3)
    return grade.grade(fr['lin'], exposure=1.0, act='I', seed=3)
G0 = np.array([0.66, 0.31, 0.035], np.float32)
V = [variant(tie_len_mm=3.9, tie_r=0.52, thread_r=0.40, sep_mm=0.92, gold=G0),
     variant(tie_len_mm=4.6, tie_r=0.62, thread_r=0.55, sep_mm=1.25, gold=G0, ply_mm=1.2, ply_deg=48, hamp=0.5),
     variant(tie_len_mm=4.6, tie_r=0.62, thread_r=0.55, sep_mm=1.25, gold=np.array([0.80,0.40,0.06],np.float32), ply_mm=1.0, ply_deg=40, hamp=0.55, h0=0.6)]
out = np.vstack(V)
out = cv2.resize(out, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
cv2.imwrite('_c/thread_variants.png', cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
