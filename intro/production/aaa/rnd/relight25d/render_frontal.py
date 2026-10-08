"""Frontal 2560x1440 still under raking light (both motifs flat-stitched on linen)."""
import sys, time, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2
from emb.core import *
from emb.scene import load, composite_flat, PX
from emb.render import frontal, spot, undulation
out = sys.argv[1] if len(sys.argv) > 1 else 'out/still_frontal.png'
az = float(sys.argv[2]) if len(sys.argv) > 2 else 122
el = float(sys.argv[3]) if len(sys.argv) > 3 else 20
sc = load()
c, fib = composite_flat(sc)
H, W = c['h'].shape
km = spot((H, W), PX, 150, 92, 100, floor=0.3, aspect=1.55)
U = undulation((H, W), PX, 0.0, amp=1.2)
light = dict(az=az, el=el, key_i=3.0, fill_i=0.16, rim_i=0.22, rim_az=25, rim_el=9)
view = (23 * PX, 20 * PX, 284 * PX, 160 * PX)
for i in range(2):
    tm = {}
    t = time.time()
    img = frontal(c, view, (2560, 1440), light, fib=fib, kmap=km, timing=tm, exposure=0.95, undul=U)
    print('frame %.2fs' % (time.time() - t), {k: round(v, 2) for k, v in tm.items()})
save_rgb(out, img)
