"""Palette check at the f1782 pose: class medians (OKLab) of a NEUTRAL-light Eevee render (CHRON_NEUTRAL=1, same intensities as the pool peak, white light,
neutral grade) vs the live menu board (native capture), same camera, same hex masks, same visible-board mask (UI excluded in both).
python3 palcheck_full.py ev.exr [exposure]  -> prints + data/palette_report.json"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from r25render import grade
from exr import read_exr
from sample_menu import hex_masks, class_stats, oklab_of_u8_bgr, CAP, VIS
sys.path.insert(0, RND)
import numpy as np, cv2
from emb.core import srgb2lin, lin2oklab, oklab2lin, lin2srgb
exr, exp = sys.argv[1], (float(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else None)
L = json.load(open(f'{POC}/data/layout.json'))
a = read_exr(exr)[..., :3]
if a.shape[1] != 2560: a = cv2.resize(a, (2560, 1440), interpolation=cv2.INTER_AREA)
SHOWN = '--shown' in sys.argv
img = grade(a, exposure=exp, grain=0.0, neutral=not SHOWN)
mine = lin2oklab(srgb2lin(img.astype(np.float32) / 255))
menu = oklab_of_u8_bgr(cv2.imread(CAP))
vis = cv2.imread(VIS, cv2.IMREAD_UNCHANGED); vis = (vis if vis.ndim == 2 else vis[..., -1]) > 200
idx, _ = hex_masks(L, inset=0.10)
cm, ph_m = class_stats(menu, idx, L, vis, 2500)
cx, ph_x = class_stats(mine, idx, L, vis, 2500)
rep = {}
print('class     |  mine  L     C     h    |  menu  L     C     h    | dE_ok x100 (class medians) | per-hex median dE | n_hex')
for t in cm:
    if t not in cx: continue
    a_, b_ = np.array(cx[t]['lab']), np.array(cm[t]['lab'])
    d = float(np.linalg.norm(a_ - b_) * 100)
    hs = [np.linalg.norm(np.array(ph_x[i]['lab']) - np.array(ph_m[i]['lab'])) * 100 for i in ph_m if i in ph_x and ph_m[i]['t'] == t]
    C1, h1 = math.hypot(a_[1], a_[2]), math.degrees(math.atan2(a_[2], a_[1])) % 360
    C2, h2 = math.hypot(b_[1], b_[2]), math.degrees(math.atan2(b_[2], b_[1])) % 360
    print(f'{t:9s} | {a_[0]:.3f} {C1:.3f} {h1:5.1f} | {b_[0]:.3f} {C2:.3f} {h2:5.1f} | {d:6.2f} | {np.median(hs):6.2f} | {len(hs)}')
    rep[t] = dict(mine=[float(v) for v in a_], menu=[float(v) for v in b_], dE_ok_x100=d, per_hex_median_dE=float(np.median(hs)), n_hex=len(hs))
json.dump(rep, open(f'{POC}/data/palette_report' + ('_shown' if SHOWN else '') + '.json', 'w'), indent=1)
