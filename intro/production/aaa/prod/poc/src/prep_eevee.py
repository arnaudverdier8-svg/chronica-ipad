"""Inputs for the Eevee scene (v2): reveal map (footprint switch A->B per piece), heal map (B->C), base pool maps, wool stitch tile,
tether anchors, light rig JSON.  python3 prep_eevee.py"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import numpy as np, cv2
import anim
from anim import schedule, tether_snap_frames, _h
from exr import write_exr
import lightmodel as lm
from elev import load_elev
E = f'{POC}/data/eevee'; os.makedirs(E, exist_ok=True)
D = f'{POC}/maps'
pieces = json.load(open(f'{POC}/data/pieces.json'))
mk = np.load(f'{D}/masks.npz')
pid = mk['pidmap'].astype(np.int32)
present = set(int(v) for v in np.unique(pid))
for i, p in enumerate(pieces):
    if (i + 1) not in present: p['skip'] = True
json.dump(pieces, open(f'{POC}/data/pieces.json', 'w'), indent=0)
starts = schedule(pieces)
st_arr = np.array([99999.0] + [float(s) if s is not None else 99999.0 for s in starts], np.float32)
reveal = st_arr[pid] + 2.0          # the lying piece rests on its stitched elevation for 2 frames, then the footprint opens
write_exr(f'{E}/reveal.exr', reveal.astype(np.float32), half=False)
sweep = np.load(f'{D}/sweep.npy').astype(np.float32)
heal = np.where(pid > 0, st_arr[pid] + anim.HEAL_DELAY + anim.HEAL_SPAN * sweep, 1e6).astype(np.float32)
write_exr(f'{E}/heal.exr', heal, half=False)
# base pool maps (the state R25 radiance is baked in): RGB = (kL, kR, kF) at 1/4 map resolution
kL, kR, kF = lm.kmaps((H // 4, W // 4), 0, 0, 4, None)
np.save(f'{E}/km0_shape.npy', np.array([H // 4, W // 4]))
write_exr(f'{E}/km0.exr', np.dstack([kL, kR, kF]).astype(np.float32), half=False)
json.dump(lm.light_table(), open(f'{E}/lights.json', 'w'), indent=1)
# wool stitch tile: laid 2-ply strands (R height, G per-strand shade, B groove ao), 16 strands per 512 px tile, ply ridges at 30 deg, couching ticks
N = 128; nst = 16; per = N / nst           # v3: 128 px tile (8 px per strand): the 512 px tile aliased into speckle at the film scale
v, u = np.mgrid[0:N, 0:N].astype(np.float32)
k = np.floor(v / per); f = v / per - k
rng = np.random.default_rng(3)
ph = rng.uniform(0, 2 * np.pi, nst)[k.astype(int) % nst]; wj = rng.uniform(0.82, 1.0, nst)[k.astype(int) % nst]
shade = rng.uniform(0.80, 1.14, nst)[k.astype(int) % nst]
prof = np.clip(1 - ((f - 0.5) / (0.5 * wj)) ** 2, 0, 1) ** 0.45
ply = 0.5 + 0.5 * np.cos(2 * np.pi * (u + (f - 0.5) * per * 0.58) / (per * 0.9) + ph)
hgt = prof * (0.80 + 0.20 * ply)
# couching ticks: a perpendicular dark tie every 128 px on every 4th strand pair
tick = np.exp(-(((u % 32) - 16) / 1.5) ** 2) * (0.5 + 0.5 * np.cos(2 * np.pi * k / 8.0)) ** 2
hgt = hgt + 0.10 * tick
hgt = cv2.GaussianBlur(hgt, (0, 0), 0.5)
ao = np.clip(0.55 + 0.45 * prof, 0, 1)
tile = np.dstack([np.clip(hgt, 0, 1), np.clip((shade - 0.7) / 0.5, 0, 1), ao])
cv2.imwrite(f'{E}/wool_tile.png', cv2.cvtColor((tile * 65535).astype(np.uint16), cv2.COLOR_RGB2BGR))
# tethers: points on the lying elevation outline (face-local x, height y) = needle holes on the cloth
def contour_pts(alpha, n, xmin, ymax, ppu, seed, ylim=0.3):
    cs, _ = cv2.findContours(alpha.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=len)[:, 0, :].astype(np.float32)
    L = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(c, axis=0).T))])
    r = np.random.default_rng(seed)
    out = []
    for i in range(n * 3):
        s = (i + r.uniform(0.2, 0.8)) / (n * 3) * L[-1]
        j = int(np.searchsorted(L, s)); j = min(j, len(c) - 1)
        out.append(c[j])
    out = np.array(out)
    yv = ymax - (out[:, 1] + 0.5) / ppu
    out = out[yv <= ylim]
    if len(out) > n: out = out[np.linspace(0, len(out) - 1, n).astype(int)]
    return [[float(xmin + (px + 0.5) / ppu), float(ymax - (py + 0.5) / ppu)] for px, py in out]
teth = {}
cache = {}
for i, p in enumerate(pieces):
    if p.get('skip') or starts[i] is None: continue
    if p['kind'] in ('town', 'site', 'lumber', 'banner'):
        if p['model'] not in cache:
            lab, names, J = load_elev(p['model'])
            cache[p['model']] = (lab >= 0, J)
        al, J = cache[p['model']]
        n = {'town': 11, 'site': 5, 'lumber': 4, 'banner': 3}[p['kind']]
        pts = contour_pts(al, n, J['x_min'], J['y_max'], J['ppu'], i, ylim=min(0.3, 0.5 * J['y_max']) / p['scale'])
        pts = [[x * p['scale'], y * p['scale']] for x, y in pts]
    elif p['kind'] == 'tree':
        rad, ht = p['rad'], p['height']
        pts = [[-rad * 0.85, 0.02], [rad * 0.85, 0.02], [0.0, ht * 0.28]]
    else:
        pts = [[-p['w'] * 0.38, 0.03], [p['w'] * 0.38, 0.03], [0.0, p['height'] * 0.30], [-p['w'] * 0.2, p['height'] * 0.12]]
    snaps = tether_snap_frames(starts[i], len(pts), i, p['kind'])
    teth[p['id']] = dict(pts=pts, snap=snaps, start=starts[i])
json.dump(dict(starts=starts, tethers=teth), open(f'{E}/anim.json', 'w'))
ss = sorted(set(s for s in starts if s))
print('starts', ss[0], ss[-1], 'n', sum(1 for s in starts if s), 'tethers', sum(len(t['pts']) for t in teth.values()), 'last snap', max(max(t['snap']) for t in teth.values()))
