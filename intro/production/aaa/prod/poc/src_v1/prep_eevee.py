"""Inputs for the Eevee scene: reveal-frame map (footprint switch A->B per piece), key-pool map, stitch bump tile,
trimmed figure cards, tether anchor/hole definitions, light rig JSON. python3 prep_eevee.py"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import numpy as np, cv2
from anim import schedule, tether_snap_frames, _h
from exr import write_exr
from r25render import kmap_for, write_lights
from elev import load_elev
from figures import load_card
D = f'{POC}/maps'; E = f'{POC}/data/eevee'; os.makedirs(E, exist_ok=True); os.makedirs(f'{E}/cards', exist_ok=True)
pieces = json.load(open(f'{POC}/data/pieces.json'))
mk = np.load(f'{D}/masks.npz')
pid = mk['pidmap'].astype(np.int32)
present = set(int(v) for v in np.unique(pid))
for i, p in enumerate(pieces):
    if (i + 1) not in present: p['skip'] = True
json.dump(pieces, open(f'{POC}/data/pieces.json', 'w'), indent=0)
starts = schedule(pieces)
st_arr = np.array([99999.0] + [float(s) if s is not None else 99999.0 for s in starts], np.float32)
reveal = st_arr[pid]
write_exr(f'{E}/reveal.exr', reveal.astype(np.float32), half=False)
km = kmap_for((H // 4, W // 4), 0, 0)
# kmap_for works in full-res px: rebuild at quarter res explicitly
yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32) * 4 + 2
from r25render import POOL
cxp, czp = (POOL['cx'] - BX0) * PPU, (POOL['cz'] - BZ0) * PPU
d = np.hypot((xx - cxp) / PX / POOL['aspect'], (yy - czp) / PX) / POOL['r_mm']
km = (POOL['floor'] + (1 - POOL['floor']) * np.exp(-d * d)).astype(np.float32)
write_exr(f'{E}/kmap.exr', km, half=False)
write_lights(f'{E}/lights.json')
# stitch bump tile (laid 2-ply wool): 16 strands per tile, ply ridges at 30 deg, per-strand phase / width jitter
N = 512; nst = 16; per = N / nst
v, u = np.mgrid[0:N, 0:N].astype(np.float32)
k = np.floor(v / per); f = v / per - k
rng = np.random.default_rng(3)
ph = rng.uniform(0, 2 * np.pi, nst)[k.astype(int) % nst]; wj = rng.uniform(0.85, 1.0, nst)[k.astype(int) % nst]
prof = np.clip(1 - ((f - 0.5) / (0.5 * wj)) ** 2, 0, 1) ** 0.45
ply = 0.5 + 0.5 * np.cos(2 * np.pi * (u + (f - 0.5) * per * 0.58) / (per * 0.9) + ph)
hgt = prof * (0.82 + 0.18 * ply)
hgt = cv2.GaussianBlur(hgt, (0, 0), 0.8)
cv2.imwrite(f'{E}/stitch_bump.png', np.clip(hgt * 65535, 0, 65535).astype(np.uint16))
# trimmed cards
for p in pieces:
    if p['kind'] != 'card': continue
    nm = f"{p['unit']}_{p['realm']}"
    if os.path.exists(f'{E}/cards/{nm}_alb.png'): continue
    c = load_card(p['unit'], p['realm'])
    rgba = np.dstack([c['alb'], c['alpha']])
    cv2.imwrite(f'{E}/cards/{nm}_alb.png', cv2.cvtColor((rgba * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGBA2BGRA))
    cv2.imwrite(f'{E}/cards/{nm}_nrm.png', cv2.cvtColor((c['nrm'] * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR))
# tethers: points on the lying elevation outline (face-local x, height y) = needle holes on the cloth
def contour_pts(alpha, n, xmin, ymax, ppu, seed, ylim=0.3):
    cs, _ = cv2.findContours(alpha.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=len)[:, 0, :].astype(np.float32)
    # prefer the lower 70 % of the outline (walls / feet), spread evenly along the contour
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
        pts = [[-rad * 0.85, 0.02], [rad * 0.85, 0.02], [-rad * 0.6, ht * 0.3], [rad * 0.55, ht * 0.32]]
    else:
        c = load_card(p['unit'], p['realm'])
        hh, ww = c['alpha'].shape
        pts = contour_pts(c['alpha'] > 0.5, 5, -p['w'] / 2, p['height'], hh / p['height'], i, ylim=0.3)
    snaps = tether_snap_frames(starts[i], len(pts), i)
    teth[p['id']] = dict(pts=pts, snap=snaps, start=starts[i])
json.dump(dict(starts=starts, tethers=teth), open(f'{E}/anim.json', 'w'))
print('reveal range', np.min(st_arr), sorted(set(s for s in starts if s))[:5], max(s for s in starts if s), 'tethers', sum(len(t['pts']) for t in teth.values()))
