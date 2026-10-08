"""Look-dev: render f669 (or a 100 % window of it) fast.  Usage:
   python3 lookdev.py full|void|crown|strands|lords  [tag]
full = 1280x720 on the L1 mip of the whole frame (cheap).  void/crown/... = 100 % windows of the 2560 frame at L0."""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np, cv2
import shot
what = sys.argv[1] if len(sys.argv) > 1 else 'full'
tag = sys.argv[2] if len(sys.argv) > 2 else 'ld'
W_ = os.path.join(HERE, '..', 'work'); os.makedirs(W_, exist_ok=True)
F = 669
t = time.time()
if what == 'full':
    r = shot.render_frame(F, out_wh=(1280, 720), level=1, threads=True)
elif what == 'fullL0':
    r = shot.render_frame(F, out_wh=(1280, 720), level=0, threads=True, free_tiles=False)
else:
    v = shot.view_of(F)
    s = v['px_per_mm']
    cx, cy = {'void': (295, 190), 'crown': (296, 135), 'strands': (300, 232), 'lords': (300, 175), 'lap': (300, 235), 'lgob': (142, 262), 'gob0': (82, 262), 'rcand': (525, 262)}[what]
    shot.VIEW_OVERRIDE = dict(cx_mm=cx, cy_mm=cy, px_per_mm=s)
    r = shot.render_frame(F, out_wh=(1280, 720), level=0, threads=True, free_tiles=True)
img = r['img']
cv2.imwrite(os.path.join(W_, f'{tag}_{what}.png'), img[..., ::-1])
Y = (r['lin'] * [0.2126, 0.7152, 0.0722]).sum(-1)
print(what, 'time %.1fs' % (time.time() - t), {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r['timing'].items() if k != 'view'})
