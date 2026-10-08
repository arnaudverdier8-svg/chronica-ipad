"""Smoke test of the README snippets (small frames)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import cv2; cv2.setNumThreads(2)
import numpy as np
from chron.config import MAPS
from chron.maps import MapSet
from chron import frontal, shade, grade
from chron.qa.void import check_void
from chron.anim.groupanim import GroupAnim
from chron.lift import Slip, tethers
P1 = MapSet(MAPS + '/p1_oath')
light = shade.rig(az=135, el=22, K=3000, key_i=2.7, rim_i=0.25)
fr = frontal.render(P1, dict(cx_mm=295.2, cy_mm=173.6, px_per_mm=4.65 / 4), light, out_wh=(640, 360),
                    kmap=dict(cx_mm=230, cy_mm=150, r_mm=400, floor=0.55), fib_seed=3)
check_void(fr['lin'], fr['alpha'])
img = grade.grade(fr['lin'], exposure=0.95, act='I', seed=140)
G = MapSet(MAPS + '/p1_oath_ground')
king, crown = GroupAnim(G, ['king']), GroupAnim(G, ['crown'])
candle = dict(pos_mm=(-63, 190, 78.0), K=1900, i=2.6, ref_mm=360, tint=0.55, shadow=True)
light = shade.rig(az=150, el=12, K=1900, key_i=0.3, fill_ratio=6, tint=0.5, points=[candle])
f = 600
u = king.n * (f - 561) / 80
view = dict(cx_mm=310, cy_mm=170, px_per_mm=5.81 / 4)
fr = frontal.render(G, view, light, out_wh=(640, 360), age=1.0, edit=king.edit(u, mode='unpick'),
                    overlay=king.loose_overlay(u, rate=king.n / 80, light=light))
slip = Slip(crown); L = slip.layers(view, light, lift_mm=15.0, out_wh=(640, 360))
lin = slip.composite(fr['lin'], L)
img = grade.grade(lin, exposure=1.0, act='II', seed=f)
assert img.shape == (360, 640, 3)
print('README snippets OK')
