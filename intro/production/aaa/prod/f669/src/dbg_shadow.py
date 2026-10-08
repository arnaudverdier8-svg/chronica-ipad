import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np, cv2
import shot
F = 669
v = shot.view_of(F)
shot.VIEW_OVERRIDE = dict(cx_mm=300, cy_mm=170, px_per_mm=v['px_per_mm'])
r = shot.render_frame(F, out_wh=(1280, 720), level=1, threads=False, debug=True)
L = r['L']; sh = r['sh']; al = L['alpha']; tsh = L['tether_shadow']
vis = np.zeros(sh.shape + (3,), np.uint8)
vis[..., 2] = np.clip(L['shadow'] * 255, 0, 255); vis[..., 1] = np.clip(al * 255, 0, 255); vis[..., 0] = np.clip(tsh * 255 * 3, 0, 255)
cv2.imwrite(os.path.join(HERE, '..', 'work', 'dbg_shadow.png'), vis)
print('shadow max', sh.max(), 'tether', tsh.max(), 'ao', L['ao'].max())
