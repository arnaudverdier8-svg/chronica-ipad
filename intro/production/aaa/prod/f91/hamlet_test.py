import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'kit'))
import bkit
import numpy as np, cv2
from bkit.canvas import Canvas
from bkit import motifs as M
from chron import frontal, shade, grade
import render_f91 as R

def variant(name, models, style, w=52.0, vs=1.5, pennant=None):
    c = Canvas(90, 60, PX=10.0, seed=3, name='t', verbose=False)
    res = M.town(c, models, 45, 52, w, seed=80, group='towns', style=style, pennant_col=pennant, vstretch=vs, outline_w=0.82)
    m = c.m
    m['origin_mm'] = (0.0, 0.0); m['valid'] = np.ones(m['h'].shape, bool)
    fr = frontal.render(m, dict(x0_mm=0, y0_mm=0, px_per_mm=8.0), R.rig(), out_wh=(720, 480), fib_seed=3)
    img = grade.grade(fr['lin'], exposure=1.0, act='I', seed=3)
    return img

def hamlet(vs=1.5):
    c = Canvas(90, 60, PX=10.0, seed=3, name='t', verbose=False)
    M.cottage(c, 33, 52.5, 13, 8.0, 6.5, wall_col='stone', roof_col='terracotta', seed=1, group='towns')
    M.cottage(c, 57, 53.5, 15, 9.0, 7.5, wall_col='clay', roof_col='mustard', seed=2, group='towns')
    M.cottage(c, 71, 52.0, 10, 7.0, 6.0, wall_col='stone_warm', roof_col='woad', seed=3, group='towns')
    ap = M.watch_tower(c, 45, 52.5, seed=4, group='towns')
    M.pennant(c, ap[0], ap[1] - 10, 10, 'road_green', direction=1, length=12.0, height=5.0, seed=9, group='pennants')
    m = c.m
    m['origin_mm'] = (0.0, 0.0); m['valid'] = np.ones(m['h'].shape, bool)
    fr = frontal.render(m, dict(x0_mm=0, y0_mm=0, px_per_mm=8.0), R.rig(), out_wh=(720, 480), fib_seed=3)
    return grade.grade(fr['lin'], exposure=1.0, act='I', seed=3)
V = [hamlet(1.4)]
cv2.imwrite('_c/hamlets.png', cv2.cvtColor(np.hstack(V), cv2.COLOR_RGB2BGR))
