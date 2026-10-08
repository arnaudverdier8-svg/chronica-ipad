"""Sample the live menu board (native capture) in OKLab per terrain class, on the exact f1782 camera.
Writes data/menu_palette.json (class medians, per-hex medians, sRGB hex) and data/menu_classmask.png.
python3 sample_menu.py"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from gamecam import Cam
sys.path.insert(0, RND)
import numpy as np, cv2
from emb.core import srgb2lin, lin2oklab, oklab2lin, lin2srgb

CAP = f'{A}/prod/handoff/f1983_16x9_2560x1440.png'
VIS = f'{A}/prod/handoff/mattes_16x9_2560x1440/board_visible_alpha.png'


def hex_masks(layout, W=2560, Hh=1440, inset=0.10):
    """per-pixel hex index at the menu camera (ground plane y=0.25), eroded by `inset` game units from every edge (px map)"""
    cam = Cam(np.array(TARGET, float), math.radians(PITCH_MENU), DIST, FOV_V, W, Hh)
    ys, xs = np.mgrid[0:Hh, 0:W]
    G = cam.ground(xs.ravel().astype(np.float64), ys.ravel().astype(np.float64), 0.25)
    gx, gz = G[:, 0].reshape(Hh, W), G[:, 2].reshape(Hh, W)
    q, r = axial_round(gx, gz)
    lut = {}
    idx = -np.ones((Hh, W), np.int32)
    HK = {(h['q'], h['r']): i for i, h in enumerate(layout['hexes'])}
    for (qq, rr), i in HK.items():
        idx[(q == qq) & (r == rr)] = i
    hx = np.array([h['x'] for h in layout['hexes']], np.float32); hz = np.array([h['z'] for h in layout['hexes']], np.float32)
    ok = idx >= 0
    de = np.where(ok, edge_dist(gx, gz, hx[np.clip(idx, 0, None)], hz[np.clip(idx, 0, None)]), -1)
    idx = np.where(de > inset, idx, -1)
    return idx, (gx, gz)


def oklab_of_u8_bgr(im):
    rgb = cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    return lin2oklab(srgb2lin(rgb))


def class_stats(lab, idx, layout, vis, min_px=2500):
    ter = np.array([h['t'] for h in layout['hexes']])
    out = {}; perhex = {}
    for i in np.unique(idx[idx >= 0]):
        m = (idx == i) & vis
        if m.sum() < min_px: continue
        perhex[int(i)] = dict(n=int(m.sum()), lab=[float(v) for v in np.median(lab[m], 0)], t=str(ter[i]))
    for t in sorted(set(ter)):
        ids = [i for i, d in perhex.items() if d['t'] == t]
        if not ids: continue
        m = np.isin(idx, ids) & vis
        out[t] = dict(n=int(m.sum()), hexes=len(ids), lab=[float(v) for v in np.median(lab[m], 0)],
                      p25=[float(v) for v in np.percentile(lab[m], 25, 0)], p75=[float(v) for v in np.percentile(lab[m], 75, 0)])
        l = np.array(out[t]['lab'], np.float32)
        out[t]['srgb'] = '#%02X%02X%02X' % tuple(int(round(float(c) * 255)) for c in lin2srgb(oklab2lin(l[None]))[0])
    return out, perhex


if __name__ == '__main__':
    L = json.load(open(f'{POC}/data/layout.json'))
    cap = cv2.imread(CAP)
    vis = cv2.imread(VIS, cv2.IMREAD_UNCHANGED)
    vis = (vis if vis.ndim == 2 else vis[..., -1]) > 200
    # additionally drop the nameplates/shields roughly: none (class medians are robust)
    idx, _ = hex_masks(L)
    lab = oklab_of_u8_bgr(cap)
    out, perhex = class_stats(lab, idx, L, vis)
    json.dump(dict(classes=out, perhex=perhex), open(f'{POC}/data/menu_palette.json', 'w'), indent=1)
    for t, d in out.items():
        l = d['lab']; C = math.hypot(l[1], l[2]); h = math.degrees(math.atan2(l[2], l[1])) % 360
        print(f"{t:9s} n={d['n']:7d} hexes={d['hexes']:2d} L={l[0]:.3f} C={C:.3f} h={h:5.1f}  {d['srgb']}")
    # debug picture
    dbg = cap.copy(); dbg[(idx >= 0) & vis] = (dbg[(idx >= 0) & vis] * 0.4 + np.array([0, 0, 255]) * 0.6).astype(np.uint8)
    cv2.imwrite(f'{POC}/preview/menu_sample_mask.jpg', dbg, [cv2.IMWRITE_JPEG_QUALITY, 80])
