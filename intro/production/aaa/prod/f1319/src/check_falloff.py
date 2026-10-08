"""Proof that the falloff is physical (in the light transport) and measures -2.5 EV at the frame edges: relight a flat 18 % grey plane
with the final rig + pool through the same patched BRDF, and read the linear radiance at the frame centre / edge mid-points / corners."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f1319/src')
from world import *
PX = 0.5
x0, y0, Wpx, Hpx = world_grid(PX)
m = dict(PX=PX, origin_mm=(x0, y0), h=np.zeros((Hpx, Wpx), np.float32), alb=np.full((Hpx, Wpx, 3), 0.18, np.float32),
         T=np.dstack([np.ones((Hpx, Wpx), np.float32), np.zeros((Hpx, Wpx), np.float32)]), mat=np.zeros((Hpx, Wpx), np.uint8),
         cov=np.zeros((Hpx, Wpx), np.float32), valid=np.ones((Hpx, Wpx), bool))
km = pool(PX, x0, y0, Wpx, Hpx)
light = rig_last_light()
frontal.prepare(m, S_SCREEN, True)
col, _ = shade_s18.relight(m, light, cam=(0, 0, 1500.0), kmap=km, h_shadow=m['h'], return_vis=True)
L = col @ np.array([0.2126, 0.7152, 0.0722], np.float32)
def at(x, y):
    i = int((y - y0) * PX); j = int((x - x0) * PX)
    return float(L[i - 3:i + 4, j - 3:j + 4].mean())
c0 = at(0, 0); cp = at(POOL['cx'], POOL['cy'])
pts = {'frame centre (0,0)': (0, 0), 'pool peak': (POOL['cx'], POOL['cy']), 'left edge mid': (-WIN_W / 2 + 6, 0), 'right edge mid': (WIN_W / 2 - 6, 0),
       'top edge mid': (0, -WIN_H / 2 + 6), 'bottom edge mid': (0, WIN_H / 2 - 6), 'top-left corner': (-WIN_W / 2 + 6, -WIN_H / 2 + 6),
       'bottom-right corner': (WIN_W / 2 - 6, WIN_H / 2 - 6)}
res = {k: dict(radiance=at(*v), EV_vs_pool_peak=float(np.log2(at(*v) / cp)), EV_vs_frame_centre=float(np.log2(at(*v) / c0))) for k, v in pts.items()}
edges = [res[k]['EV_vs_pool_peak'] for k in ('left edge mid', 'right edge mid', 'top edge mid', 'bottom edge mid')]
res['mean_EV_edge_midpoints_vs_pool_peak'] = float(np.mean(edges))
json.dump(res, open(OUT + '/falloff_check.json', 'w'), indent=1)
for k, v in res.items(): print(k, v)
