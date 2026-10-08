"""PoC acceptance checks -> qa.json: swap match (R25 f1719 state vs Eevee zero-tilt still), crane landing,
tether / footprint durations per piece, void pixels. python3 qa.py [--preview]"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from r25render import grade
from exr import read_exr
import numpy as np, cv2
sys.path.insert(0, RND)
from emb.core import srgb2lin, lin2oklab

PREV = '--preview' in sys.argv
EVD = f'{POC}/preview/ev720' if PREV else f'{POC}/ev'
R25D = f'{POC}/r25'
FR = f'{POC}/preview/frames720' if PREV else f'{POC}/frames'
out = {}
r = np.load(f'{R25D}/last_linear.npy').astype(np.float32)
e = read_exr(f'{EVD}/f1725.exr')[..., :3]
if r.shape != e.shape: r = cv2.resize(r, (e.shape[1], e.shape[0]), interpolation=cv2.INTER_AREA)
ga = grade(r, grain=0).astype(np.float32) / 255; gb = grade(e, grain=0).astype(np.float32) / 255
la = lin2oklab(srgb2lin(ga)); lb = lin2oklab(srgb2lin(gb))
de = np.linalg.norm(la - lb, axis=-1) * 100
# low-frequency (sigma 2 px) difference: what a dissolve can reveal; and per-pixel
lfa = lin2oklab(srgb2lin(cv2.GaussianBlur(ga, (0, 0), 2))); lfb = lin2oklab(srgb2lin(cv2.GaussianBlur(gb, (0, 0), 2)))
de_lf = np.linalg.norm(lfa - lfb, axis=-1) * 100
sh, resp = cv2.phaseCorrelate(cv2.cvtColor(ga, cv2.COLOR_RGB2GRAY).astype(np.float64), cv2.cvtColor(gb, cv2.COLOR_RGB2GRAY).astype(np.float64))
out['swap'] = dict(median_dE_ok_x100=float(np.median(de)), median_dE_ok_x100_lowpass_2px=float(np.median(de_lf)),
                   p95_dE_ok_x100_lowpass=float(np.percentile(de_lf, 95)), global_shift_px=[float(sh[0]), float(sh[1])],
                   note='pixel dE includes texture-filter differences (cv2 Gaussian+bilinear vs GPU mip/aniso + 16 TAA); hidden by the 6-frame dissolve')
out['crane'] = {str(f): round(camera_pose(f)['pitch'], 4) for f in (1726, 1740, 1750, 1760, 1766)}
out['crane']['menu_pitch'] = round(PITCH_MENU, 4)
out['crane']['err_at_1760_deg'] = round(camera_pose(1760)['pitch'] - PITCH_MENU, 4)
an = json.load(open(f'{POC}/data/eevee/anim.json'))
pieces = json.load(open(f'{POC}/data/pieces.json'))
teth = [min(t['snap']) - t['start'] for t in an['tethers'].values()]
foot = [F1 - s for s in an['starts'] if s is not None]
out['pieces'] = dict(n_rising=sum(1 for s in an['starts'] if s is not None), first_rise=min(s for s in an['starts'] if s), last_rise=max(s for s in an['starts'] if s),
                     settled_by=max(s for s in an['starts'] if s) + 12, min_tether_frames=int(min(teth)), min_footprint_frames=int(min(foot)),
                     n_tethers=sum(len(t['pts']) for t in an['tethers'].values()))
# void check on the composited frames (pure black / background pixels)
vo = []
for f in range(F0, F1 + 1, 7):
    im = cv2.imread(f'{FR}/f{f:04d}.png')
    if im is None: continue
    vo.append(int((im.max(-1) < 8).sum()))
out['void_pixels_sampled_frames'] = vo
json.dump(out, open(f'{POC}/qa{"_preview" if PREV else ""}.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
