"""COMP (v2): assemble f1664-1782 -> frames/f%04d.png (2560x1440 graded sRGB, or --preview 1280x720).
f1664-1719  R25 2D stitch-on frames (already graded, from r25/)
f1720-1725  registered swap: linear cross-dissolve R25 last state -> Eevee zero-tilt still (ev/f1725.exr); both renderers share the light state
f1726-1766  Eevee crane frames (ev/f%04d.exr), 180-degree camera motion blur by ground-plane homographies
f1767-1782  hold on the menu camera: Eevee frames on ones (flicker, light-state blend C -> D, idle motion, healing footprints)
One grade for both renderers (r25render.grade); grain per frame.  The candle swell is part of the Eevee light state (the pools themselves), not an exposure ramp.
python3 comp.py [--preview]"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from r25render import grade
from exr import read_exr
import numpy as np, cv2

PREV = '--preview' in sys.argv
R25D = f'{POC}/preview/r25_0.5' if PREV and os.path.exists(f'{POC}/preview/r25_0.5/f1664.png') else f'{POC}/r25'
EVD = f'{POC}/preview/ev720' if PREV else f'{POC}/ev'
OUT = f'{POC}/preview/frames720' if PREV else f'{POC}/frames'
os.makedirs(OUT, exist_ok=True)
Wo, Ho = (1280, 720) if PREV else (2560, 1440)
HOLD_RENDERED = [f for f in range(1768, F1 + 1, 2)]


def ev(f):
    a = read_exr(f'{EVD}/f{f:04d}.exr')[..., :3]
    if a.shape[1] != Wo: a = cv2.resize(a, (Wo, Ho), interpolation=cv2.INTER_AREA)
    return a


def add_grain(u8, seed, amt=0.011):
    g = np.random.default_rng(seed).standard_normal(u8.shape[:2]).astype(np.float32)
    g = cv2.GaussianBlur(g, (0, 0), 0.7)
    return np.clip(u8.astype(np.float32) + amt * 255 * g[..., None], 0, 255).round().astype(np.uint8)


from gamecam import Cam


def cam_at(t, Wo, Ho):
    pose = camera_pose(t)
    return Cam(np.array(pose['target'], float), math.radians(pose['pitch']), pose['dist'], FOV_V, Wo, Ho)


def motion_blur(lin, f, n=9, shutter=0.5):
    """180-degree camera motion blur: average of the frame re-projected (ground-plane homography) to sub-frame camera poses f-0.25 .. f+0.25"""
    c0 = cam_at(f, Wo, Ho)
    if abs(camera_pose(f + 0.25)['pitch'] - camera_pose(f - 0.25)['pitch']) < 1e-3:
        return lin
    corners = np.array([[0, 0], [Wo - 1, 0], [Wo - 1, Ho - 1], [0, Ho - 1]], np.float64)
    acc = np.zeros_like(lin)
    for d in np.linspace(-shutter / 2, shutter / 2, n):
        cd = cam_at(f + d, Wo, Ho)
        G = cd.ground(corners[:, 0], corners[:, 1])
        q, _ = c0.project(G)
        M = cv2.getPerspectiveTransform(corners.astype(np.float32), q.astype(np.float32))
        acc += cv2.warpPerspective(lin, M, (Wo, Ho), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
    return acc / n


def save(f, u8):
    cv2.imwrite(f'{OUT}/f{f:04d}.png', cv2.cvtColor(u8, cv2.COLOR_RGB2BGR))


if __name__ == '__main__':
    last = np.load(f'{R25D}/last_linear.npy').astype(np.float32)
    if last.shape[1] != Wo: last = cv2.resize(last, (Wo, Ho), interpolation=cv2.INTER_AREA)
    held = None
    for f in range(F0, F1 + 1):
        if f <= F_LASTHEX:
            im = cv2.imread(f'{R25D}/f{f:04d}.png')
            if im.shape[1] != Wo: im = cv2.resize(im, (Wo, Ho), interpolation=cv2.INTER_AREA)
            cv2.imwrite(f'{OUT}/f{f:04d}.png', add_grain(im, f))
            continue
        if f <= F_SWAP1:
            w = (f - F_LASTHEX) / (F_SWAP1 - F_LASTHEX + 1.0)
            w = w * w * (3 - 2 * w)
            lin = last * (1 - w) + ev(F_SWAP1) * w
        elif f <= F_CRANE1:
            lin = motion_blur(ev(f), f)
        else:
            lin = ev(f)          # v3: the hold is rendered on ones too (candle flicker, the light-state blend to D, idle motion, healing footprints)
        save(f, grade(lin, seed=f))
        print(f, flush=True)
