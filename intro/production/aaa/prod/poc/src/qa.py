"""PoC acceptance checks -> qa.json (v3): swap match (R25 f1719 state vs Eevee zero-tilt still), crane curve and landing, pieces / tethers /
footprint durations, light state (candle ignition ramps, flicker, swell, light-state blend), per-frame luma statistics (floor, median, highlights, steps at the ignitions),
frame-to-frame change (no dead hold), void pixels, gold glint travel, Grandbois floor continuity.
python3 qa.py [--preview]"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from r25render import grade
from exr import read_exr
import anim, lightmodel as lm
import numpy as np, cv2
sys.path.insert(0, RND)
from emb.core import srgb2lin, lin2oklab

PREV = '--preview' in sys.argv
EVD = f'{POC}/preview/ev720' if PREV else f'{POC}/ev'
R25D = f'{POC}/preview/r25_0.5' if PREV else f'{POC}/r25'
FR = f'{POC}/preview/frames720' if PREV else f'{POC}/frames'
out = {}
r = np.load(f'{R25D}/last_linear.npy').astype(np.float32)
e = read_exr(f'{EVD}/f1725.exr')[..., :3]
if r.shape != e.shape: r = cv2.resize(r, (e.shape[1], e.shape[0]), interpolation=cv2.INTER_AREA)
ga = grade(r, grain=0).astype(np.float32) / 255; gb = grade(e, grain=0).astype(np.float32) / 255
la = lin2oklab(srgb2lin(ga)); lb = lin2oklab(srgb2lin(gb))
de = np.linalg.norm(la - lb, axis=-1) * 100
lfa = lin2oklab(srgb2lin(cv2.GaussianBlur(ga, (0, 0), 2))); lfb = lin2oklab(srgb2lin(cv2.GaussianBlur(gb, (0, 0), 2)))
de_lf = np.linalg.norm(lfa - lfb, axis=-1) * 100
sh, resp = cv2.phaseCorrelate(cv2.cvtColor(ga, cv2.COLOR_RGB2GRAY).astype(np.float64), cv2.cvtColor(gb, cv2.COLOR_RGB2GRAY).astype(np.float64))
out['swap'] = dict(median_dE_ok_x100=float(np.median(de)), median_dE_ok_x100_lowpass_2px=float(np.median(de_lf)),
                   p95_dE_ok_x100_lowpass=float(np.percentile(de_lf, 95)), global_shift_px=[float(sh[0]), float(sh[1])],
                   light_state=dict(gL_f1719=lm.gain('L', 1719, False), gR_f1719=lm.gain('R', 1719, False), gL_f1725=lm.gain('L', 1725, True), gR_f1725=lm.gain('R', 1725, True)),
                   note='pixel dE includes texture-filter differences (cv2 Gaussian+bilinear vs GPU mip/aniso + TAA); hidden by the 6-frame dissolve')
out['crane'] = {str(f): dict(pitch=round(camera_pose(f)['pitch'], 3), done=round(crane_s(f), 4), deg_left=round(camera_pose(f)['pitch'] - PITCH_MENU, 3)) for f in (1726, 1735, 1740, 1743, 1746, 1750, 1755, 1760, 1764, 1766)}
out['crane']['velocity_deg_per_frame'] = {str(f): round(abs(camera_pose(f + 0.5)['pitch'] - camera_pose(f - 0.5)['pitch']), 3) for f in range(1730, 1767, 4)}
out['crane']['peak_velocity_frame'] = int(max(range(1727, 1766), key=lambda f: abs(camera_pose(f + 0.5)['pitch'] - camera_pose(f - 0.5)['pitch'])))
an = json.load(open(f'{POC}/data/eevee/anim.json'))
pieces = json.load(open(f'{POC}/data/pieces.json'))
teth = [min(t['snap']) - t['start'] for t in an['tethers'].values()]
st = [s for s in an['starts'] if s is not None]
kinds = {}
for p, s in zip(pieces, an['starts']):
    if s is not None: kinds.setdefault(p['kind'], []).append(s)
out['pieces'] = dict(n_rising=len(st), first_rise=min(st), last_rise=max(st), last_tether_snap=max(max(t['snap']) for t in an['tethers'].values()),
                     settled_by=max(s + anim.RISE_DUR.get(p['kind'], 12) for p, s in zip(pieces, an['starts']) if s is not None),
                     min_tether_frames_before_first_snap=int(min(teth)),
                     footprint_open_frames_before_heal=int(anim.HEAL_DELAY - 2), n_tethers=sum(len(t['pts']) for t in an['tethers'].values()),
                     rise_start_histogram={str(k): int(sum(1 for s in st if s == k)) for k in sorted(set(st))},
                     by_kind={k: dict(n=len(v), first=min(v), last=max(v)) for k, v in kinds.items()},
                     hero={k: v for k, v in anim.HERO.items()})
out['light'] = dict(left_candle_gain_f1662_1672=[round(lm.gain('L', f, False), 3) for f in range(1662, 1673)],
                    right_candle_gain_f1706_1716=[round(lm.gain('R', f, False), 3) for f in range(1706, 1717)],
                    flicker_peak_to_peak_pct=round(100 * (max(lm.flicker(f, 1) for f in range(1700, 1800)) - min(lm.flicker(f, 1) for f in range(1700, 1800))), 2),
                    swell_ev={str(f): round(0.30 * lm.swell(f), 3) for f in (1744, 1750, 1755, 1760, 1766, 1782)},
                    light_state_blend_D={str(f): round(lm.conv(f), 3) for f in (1766, 1767, 1770, 1775, 1780, 1782)})
vo = []; mo = []; luma = {}
prev = None
LW = np.array([0.2126, 0.7152, 0.0722], np.float32)
for f in range(F0, F1 + 1):
    im = cv2.imread(f'{FR}/f{f:04d}.png')
    if im is None: continue
    if f % 7 == 0: vo.append(int((im.max(-1) < 4).sum()))
    small = cv2.resize(im, (640, 360), interpolation=cv2.INTER_AREA)
    rgb = small[..., ::-1].astype(np.float32)
    L = rgb @ LW
    luma[f] = dict(mean=float(L.mean()), p1=float(np.percentile(L, 1)), p50=float(np.percentile(L, 50)), p99=float(np.percentile(L, 99.5)), max=float(L.max()),
                   corners=[float(L[:20, :20].mean()), float(L[:20, -20:].mean()), float(L[-20:, :20].mean()), float(L[-20:, -20:].mean())])
    g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)
    if prev is not None:
        d = np.abs(g - prev)
        mo.append((f, float(d.mean()), float((d > 6).mean() * 100)))
    prev = g
out['void_pixels_sampled_frames'] = vo
out['frame_difference'] = {str(f): dict(mean_abs=round(v, 3), pct_pixels_changed_gt6=round(c, 2)) for f, v, c in mo}
out['luma_per_frame'] = {str(f): {k: (round(v, 1) if not isinstance(v, list) else [round(x, 1) for x in v]) for k, v in d.items()} for f, d in luma.items() if f % 3 == 0 or f in (1664, 1665, 1666, 1667, 1668, 1707, 1708, 1709, 1710, 1711, 1712)}
steps = {f: luma[f]['mean'] - luma[f - 1]['mean'] for f in luma if f - 1 in luma}
out['luma_steps'] = dict(max_abs_step=round(max(abs(v) for v in steps.values()), 2),
                         left_ignition_f1664_1670=[round(steps.get(f, 0), 2) for f in range(1664, 1671)],
                         right_ignition_f1707_1713=[round(steps.get(f, 0), 2) for f in range(1707, 1714)],
                         median_luma_f1668_f1706=[round(luma[f]['p50'], 1) for f in (1668, 1680, 1690, 1700, 1706) if f in luma],
                         floor_p1_f1690_f1760=[round(luma[f]['p1'], 1) for f in (1690, 1760) if f in luma],
                         corners_f1690=[round(x, 1) for x in luma[1690]['corners']] if 1690 in luma else None,
                         max_luma_in_move=round(max(d['max'] for d in luma.values()), 1))
# gold glint travel: bright warm-gold pixels per frame (x, y of the strongest cluster)
gl = {}
for f in range(1728, 1768, 2):
    im = cv2.imread(f'{FR}/f{f:04d}.png')
    if im is None: continue
    rgb = im[..., ::-1].astype(np.float32)
    Lg = rgb @ LW
    gold = (rgb[..., 0] > rgb[..., 1] * 1.04) & (rgb[..., 1] > rgb[..., 2] * 1.18) & (Lg > 170)
    ys, xs = np.nonzero(gold)
    gl[str(f)] = dict(n_px=int(gold.sum()), peak_luma=round(float(Lg[gold].max()), 1) if gold.any() else 0.0,
                      centroid_x=int(xs.mean()) if len(xs) else None)
out['gold_glint'] = gl
# Grandbois floor continuity
try:
    gx0, gz0 = hex_center(0, 0)
    from gamecam import Cam
    reg = []
    for f in range(1730, 1745):
        pose = camera_pose(f)
        cam = Cam(np.array(pose['target'], float), math.radians(pose['pitch']), pose['dist'], FOV_V, 2560, 1440)
        uv, _ = cam.project(np.array([[gx0, 0.25, gz0 + 0.1]]))
        x, y = int(uv[0, 0]), int(uv[0, 1])
        im = cv2.imread(f'{FR}/f{f:04d}.png')
        s = 2560 / im.shape[1]
        reg.append(im[int((y - 60) / s):int((y + 40) / s), int((x - 120) / s):int((x + 120) / s)].astype(np.float32).mean())
    d = np.abs(np.diff(reg))
    out['grandbois_floor'] = dict(mean_luma_f1730_1744=[round(float(v), 2) for v in reg], max_step=round(float(d.max()), 2), median_step=round(float(np.median(d)), 2))
except Exception as ex:
    out['grandbois_floor'] = str(ex)
json.dump(out, open(f'{POC}/qa{"_preview" if PREV else ""}.json', 'w'), indent=1)
print(json.dumps({k: out[k] for k in ('swap', 'luma_steps', 'pieces', 'light')}, indent=1))
