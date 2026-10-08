"""palette check: class medians (OKLab) of a neutral-light render window vs the menu's class medians (data/menu_palette.json).
python3 palcheck.py lin.npy cx cz w_units [exposure]"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from r25render import grade
sys.path.insert(0, RND)
import numpy as np, cv2
from emb.core import srgb2lin, lin2oklab
lin = np.load(sys.argv[1]).astype(np.float32)
cx, cz, wu = float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
exp = float(sys.argv[5]) if len(sys.argv) > 5 else None
L = json.load(open(f'{POC}/data/layout.json'))
MP = json.load(open(f'{POC}/data/menu_palette.json'))['classes']
Hh, Ww = lin.shape[:2]
img = grade(lin, exposure=exp, grain=0.0, neutral=True).astype(np.float32) / 255
lab = lin2oklab(srgb2lin(img))
xs = cx - wu / 2 + (np.arange(Ww) + 0.5) / Ww * wu
zs = cz - wu * 9 / 16 / 2 + (np.arange(Hh) + 0.5) / Hh * wu * 9 / 16
GX, GZ = np.meshgrid(xs, zs)
q, r = axial_round(GX, GZ)
HK = {(h['q'], h['r']): i for i, h in enumerate(L['hexes'])}
idx = -np.ones(q.shape, np.int32)
for (qq, rr), i in HK.items(): idx[(q == qq) & (r == rr)] = i
hx = np.array([h['x'] for h in L['hexes']]); hz = np.array([h['z'] for h in L['hexes']])
de = edge_dist(GX, GZ, hx[np.clip(idx, 0, None)], hz[np.clip(idx, 0, None)])
idx = np.where(de > 0.10, idx, -1)
ter = np.array([h['t'] for h in L['hexes']])
for t in ['forest', 'farm', 'plains', 'hills', 'quarry', 'sea', 'lake']:
    m = np.isin(idx, [i for i in range(len(ter)) if ter[i] == t])
    if m.sum() < 3000 or t not in MP: continue
    med = np.median(lab[m], 0); tgt = np.array(MP[t]['lab'])
    d = np.linalg.norm(med - tgt) * 100
    C = math.hypot(med[1], med[2]); h = math.degrees(math.atan2(med[2], med[1])) % 360
    Ct = math.hypot(tgt[1], tgt[2]); ht = math.degrees(math.atan2(tgt[2], tgt[1])) % 360
    print(f'{t:8s} n={m.sum():7d} mine L={med[0]:.3f} C={C:.3f} h={h:5.1f} | menu L={tgt[0]:.3f} C={Ct:.3f} h={ht:5.1f} | dE_ok x100 = {d:5.2f}')
