"""Oblique 2560x1440 still (camera tilted 42 deg from the cloth normal): knight risen ~8 mm with stumpwork padding,
king and titulus in depth-of-field falloff. Supersampled ray march (ss=2 -> 4 samples/px)."""
import sys, time, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2
cv2.setNumThreads(2)
from emb.core import *
from emb.scene import load, PX
from emb.oblique import Camera
from emb.obl_render import render_oblique, lift_map
from emb.render import undulation
out = sys.argv[1] if len(sys.argv) > 1 else 'out/still_oblique.png'
lift = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
pad = float(sys.argv[3]) if len(sys.argv) > 3 else 2.5
ss = int(sys.argv[4]) if len(sys.argv) > 4 else 2
W, H = 2560, 1440
sc = load()
cam = Camera((218, 111, 0), 215, 42, 72, 28, W, H)
l1 = lift_map(sc['k_alpha'], PX, lift, curl=lift * 0.10) if lift > 0 else np.zeros_like(sc['k_alpha'], np.float32)
U = undulation(sc['canvas']['h'].shape, PX, 0.0, amp=1.0)
light = dict(az=128, el=22, key_i=2.8, fill_i=0.18, rim_i=0.25, rim_az=25, rim_el=9)
tm = {}
img, zf, lay = render_oblique(sc, cam, light, lift1=l1, dof_px=14, timing=tm, pad=pad, undul=U, ss=ss,
                              kmap_params=dict(cx=200, cy=95, r=130, floor=0.35, aspect=1.4))
print({k: round(v, 2) for k, v in tm.items()}, 'miss', (lay < 0).mean())
save_rgb(out, img)
