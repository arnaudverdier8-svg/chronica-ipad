"""v3 look-dev: 100 % windows of the f669 frame (L0), several variants per process (assets are built once).
   python3 ld3.py shield|void|crown|strands|lords  [tag]       env F669_* as in shot.py"""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np, cv2
import shot
what = sys.argv[1] if len(sys.argv) > 1 else 'shield'
tag = sys.argv[2] if len(sys.argv) > 2 else 'ld3'
W_ = os.path.join(HERE, '..', 'work', 'v3'); os.makedirs(W_, exist_ok=True)
CEN = {'shield': (470, 205), 'void': (295, 190), 'crown': (296, 135), 'strands': (300, 232), 'lords': (300, 175),
       'lap': (300, 235), 'gl': (455, 200)}
F = 669
t = time.time()
v = shot.view_of(F); s = v['px_per_mm']
cx, cy = CEN[what]
shot.VIEW_OVERRIDE = dict(cx_mm=cx, cy_mm=cy, px_per_mm=s)
r = shot.render_frame(F, out_wh=(1280, 720), level=0, threads=True, free_tiles=True, fuzz=True)
cv2.imwrite(os.path.join(W_, f'{tag}_{what}.png'), r['img'][..., ::-1])
print(what, 'time %.1fs' % (time.time() - t), {k: (round(x, 2) if isinstance(x, float) else x) for k, x in r['timing'].items() if k != 'view'})
