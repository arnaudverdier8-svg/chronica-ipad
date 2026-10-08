"""Recover the seed-4242 menu world's hex terrain around Grandbois from UI-free demo plates (rectified with the
decoded camera rig) and write data/hexes.json: per hex (q,r): terrain class + measured median colour.
Hexes are axial (q,r) relative to Grandbois (0,0) (Hex.to_world: x = sqrt3*(q+r/2), z = 1.5 r)."""
import sys, json, math, numpy as np, cv2
sys.path.insert(0, sys.argv[0].rsplit('/', 1)[0])
from gamecam import *
P = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc'
PPU = 40.0
X0, X1, Z0, Z1 = -17.0, 13.0, -10.0, 9.0
xs = np.arange(X0, X1, 1 / PPU); zs = np.arange(Z0, Z1, 1 / PPU)
X, Z = np.meshgrid(xs, zs)


def rect(img, zoom, Y):
    src = cv2.imread(img); H, W = src.shape[:2]
    pitch, d = rig(zoom)
    cam = Cam(np.array([0.0, 0, 0]), pitch, d, 30, W, H)
    S, _ = cam.project(np.stack([X, np.full_like(X, Y), Z], -1))
    valid = (S[..., 0] > 2) & (S[..., 0] < W - 3) & (S[..., 1] > 2) & (S[..., 1] < H - 3)
    o = cv2.remap(src, S[..., 0].astype(np.float32), S[..., 1].astype(np.float32), cv2.INTER_AREA if zoom > 20 else cv2.INTER_LINEAR)
    return cv2.cvtColor(o, cv2.COLOR_BGR2RGB), valid


z11, v11 = rect(f'{P}/data/plates/demo_z11_nounits.png', 11, 0.25)
z30, v30 = rect(f'{P}/data/plates/demo_z30_nounits.png', 30, 0.25)
comb = np.where(v11[..., None], z11, z30)
cv2.imwrite(f'{P}/data/rect_combined.png', cv2.cvtColor(comb, cv2.COLOR_RGB2BGR))
# reference colours (millefleurs summer + observed)
REF = {'sea': '#2F5F8E', 'plains': '#D8C98C', 'farm': '#C9C27A', 'forest': '#5E8B57', 'hills': '#C98B5C',
       'mountain': '#D2CCC0', 'cloud': '#E2C9A0'}
def hx(h): h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)
out = {}
for q in range(-24, 24):
    for r in range(-12, 12):
        c = hex_world(q, r)
        if not (X0 + 0.5 < c[0] < X1 - 0.5 and Z0 + 0.5 < c[2] < Z1 - 0.5): continue
        d = np.hypot(X - c[0], Z - c[2])
        # ring between 0.25 and 0.75 (avoid the centre where pieces stand)
        mk = (d < 0.78) & (d > 0.2)
        px = comb[mk].astype(np.float32)
        lab = cv2.cvtColor(px[None].astype(np.uint8), cv2.COLOR_RGB2LAB)[0].astype(np.float32)
        med = np.median(px, 0)
        # robust: fraction of blue pixels
        b = (px[:, 2] > px[:, 0] + 25) & (px[:, 2] > 90)
        g = (px[:, 1] > px[:, 0] + 8) & (px[:, 1] > px[:, 2] + 10)
        o = (px[:, 0] > px[:, 2] + 70) & (px[:, 0] > px[:, 1] + 25)
        w = (px.min(1) > 170) & (px.max(1) - px.min(1) < 45)
        cls = None
        if b.mean() > 0.55: cls = 'sea'
        elif w.mean() > 0.35: cls = 'mountain'
        elif g.mean() > 0.45: cls = 'forest'
        elif o.mean() > 0.30: cls = 'hills'
        else:
            dd = {k: np.linalg.norm(med - hx(v)) for k, v in REF.items() if k not in ('sea',)}
            cls = min(dd, key=dd.get)
        if c[0] > 11.5 and cls != 'sea': cls = 'sea'   # beyond the map (fog quilts) -> sea on our board
        if cls == 'cloud': cls = 'sea'
        out[f'{q},{r}'] = dict(q=q, r=r, x=float(c[0]), z=float(c[2]), cls=cls, med=[float(v) for v in med],
                               fb=float(b.mean()), fg=float(g.mean()), fo=float(o.mean()), fw=float(w.mean()))
json.dump(out, open(f'{P}/data/hexes_auto.json', 'w'), indent=0)
# debug image
dbg = comb.copy()
col = {'sea': (40, 90, 160), 'plains': (225, 205, 130), 'farm': (190, 200, 90), 'forest': (60, 130, 60), 'hills': (200, 120, 70),
       'mountain': (235, 235, 235)}
for k, v in out.items():
    pts = [((v['x'] + 0.45 * math.cos(math.radians(60 * i - 30)) - X0) * PPU, (v['z'] + 0.45 * math.sin(math.radians(60 * i - 30)) - Z0) * PPU) for i in range(6)]
    cv2.fillPoly(dbg, [np.array(pts, np.int32)], col[v['cls']])
    cv2.putText(dbg, k, (int((v['x'] - X0) * PPU) - 12, int((v['z'] - Z0) * PPU) + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.28, (0, 0, 0), 1, cv2.LINE_AA)
cv2.imwrite(f'{P}/data/hexes_auto_dbg.jpg', cv2.cvtColor(dbg, cv2.COLOR_RGB2BGR))
from collections import Counter
print(Counter(v['cls'] for v in out.values()))
