"""Linen ground: tileable tabby maps (shared by ground plane and baked into every patch) + world-space ageing map."""
import sys, os, json, math, numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emb
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, os.environ.get('MAPSDIR', 'maps')); os.makedirs(OUT, exist_ok=True)
cfg = json.load(open(os.path.join(ROOT, 'scene_layout.json')))
PX, T = cfg['px'], cfg['linen_tile_mm']
L = emb.linen_tile(T, PX, seed=3)
np.savez(os.path.join(OUT, 'linen_tile.npz'), h=L['h'], alb=L['alb'], T=L['T'])
cv = emb.Canvas(L['S'], L['S'], PX); cv.h = L['h'].copy(); cv.alb = L['alb'].copy(); cv.mat[:] = emb.MAT_LINEN
emb.finish(cv, fuzz=False)
# cavity baked into albedo must be tile-periodic: recompute with wrap borders
h = L['h']; hp = np.pad(h, 64, mode='wrap')
blur = cv2.GaussianBlur(hp, (0, 0), 0.5 * PX)[64:-64, 64:-64]; blur2 = cv2.GaussianBlur(hp, (0, 0), 1.5 * PX)[64:-64, 64:-64]
cav = np.clip(1 - 1.4 * np.clip(blur - h, 0, None), 0.45, 1) * np.clip(1 - 0.35 * np.clip(blur2 - h, 0, None), 0.6, 1)
alb = np.clip(L['alb'] * cav[..., None], 0, 1)
np.save(os.path.join(OUT, 'linen_alb_baked.npy'), alb.astype(np.float32))
emb.save_png8(os.path.join(OUT, 'linen_albedo.png'), emb.lin_to_srgb(alb))
Np = emb.normal_map(np.pad(h, 8, mode='wrap'), PX, sigma_hp_mm=None)[8:-8, 8:-8]
emb.save_png16(os.path.join(OUT, 'linen_normal.png'), Np * 0.5 + 0.5)
m = np.zeros(h.shape + (4,), np.float32); m[:] = emb.MAT_LINEN
emb.save_png8(os.path.join(OUT, 'linen_mat.png'), m[..., :3], alpha=m[..., 3])
# ---- world ageing / variation map over the whole ground (2 px/mm): dye-lot drift, foxing, one tideline, light fade
g = cfg['ground']; AP = 2.0
gw, gh = int((g['x1'] - g['x0']) * AP), int((g['y1'] - g['y0']) * AP)
rng = np.random.default_rng(5)
var = 1 + 0.035 * emb.snoise((gh, gw), 60 * AP, 1) + 0.02 * emb.snoise((gh, gw), 15 * AP, 2)
yy, xx = np.mgrid[0:gh, 0:gw].astype(np.float32)
X, Y = xx / AP + g['x0'], yy / AP + g['y0']
col = np.ones((gh, gw, 3), np.float32) * var[..., None]
# light-exposure fade: left side slightly lighter / less saturated
fade = np.clip((-X - 50) / 300, 0, 1) * 0.05
col = col * (1 + fade[..., None] * np.array([0.6, 0.8, 1.6], np.float32))
fox = emb.hex_lin('#9C7046') / emb.hex_lin('#D4BE98')
for _ in range(70):
    cx, cy = rng.uniform(g['x0'], g['x1']), rng.uniform(g['y0'], g['y1'])
    # clustered near the edges of the visible frame
    if abs(cx) < 150 and abs(cy) < 80 and rng.random() < 0.7: continue
    for _k in range(rng.integers(1, 6)):
        r = rng.uniform(0.3, 1.5); px_, py_ = cx + rng.normal(0, 4), cy + rng.normal(0, 4)
        d = np.hypot(X - px_, Y - py_)
        a = rng.uniform(0.15, 0.35) * np.clip(1 - d / r, 0, 1) ** 0.7
        col = col * (1 - a[..., None]) + col * fox * a[..., None]
# tideline ring (upper right, partly in frame)
d = np.hypot((X - 185) / 1.0, (Y + 112) / 0.8)
ang = np.arctan2(Y + 112, X - 185)
rr = 52 + 5 * np.sin(3 * ang + 1) + 3 * np.sin(7 * ang) + 4 * emb.snoise((gh, gw), 12 * AP, 9)
ring = np.exp(-((d - rr) / 1.3) ** 2) * 0.16 * (0.5 + 0.5 * np.clip(emb.snoise((gh, gw), 20 * AP, 10) + 0.6, 0, 1)) + np.clip(1 - d / rr, 0, 1) * 0.03
tide = emb.hex_lin('#7C5A38') / emb.hex_lin('#D4BE98')
col = col * (1 - ring[..., None]) + col * tide * ring[..., None]
np.save(os.path.join(OUT, 'ground_var.npy'), col.astype(np.float32))
emb.save_png16(os.path.join(OUT, 'ground_var.png'), np.clip(col * 0.5, 0, 1))   # stored x0.5 (decode x2 in shader)
# crease field (low-frequency height, mm) on the same grid: two soft horizontal folds + one diagonal
crease = 0.55 * np.exp(-((Y - 64 - 0.04 * X) / 7.0) ** 2) * (0.6 + 0.4 * np.cos(X / 70)) \
       - 0.35 * np.exp(-((Y + 70 + 0.02 * X) / 5.0) ** 2) \
       + 0.30 * np.exp(-((X * 0.6 + Y * 0.8 - 120) / 6.0) ** 2) * np.clip(1 - np.abs(X - 200) / 120, 0, 1)
np.save(os.path.join(OUT, 'ground_crease.npy'), crease.astype(np.float32))
print('linen tile', L['S'], 'ground var', gw, gh)
