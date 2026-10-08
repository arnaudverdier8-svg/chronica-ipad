"""Check that over(flame, unlit) reproduces the full candle layer (premultiplied RGB + alpha), per matte dir.
usage: python3 verify_flames.py MATTE_DIR [tol_255=1.0]"""
import sys, os, json
import numpy as np
from PIL import Image

def load(p): return np.asarray(Image.open(p).convert('RGBA')).astype(np.float32) / 255.0

def over_pm(f, u):
    af, au = f[..., 3:4], u[..., 3:4]
    rgb = f[..., :3] * af + u[..., :3] * au * (1 - af)
    a = af + au * (1 - af)
    return rgb, a[..., 0]

def check(mdir, tol=1.0):
    res = {}
    for base in ('candle_left', 'candle_right', 'table_edge_bottom'):
        pf = os.path.join(mdir, base + '_flame.png')
        if not os.path.exists(pf): continue
        full, fl, un = load(os.path.join(mdir, base + '.png')), load(pf), load(os.path.join(mdir, base + '_unlit.png'))
        rgb, a = over_pm(fl, un)
        d_rgb = np.abs(rgb - full[..., :3] * full[..., 3:4]).max(2) * 255
        d_a = np.abs(a - full[..., 3]) * 255
        bad = (d_rgb > tol + 1e-3) | (d_a > tol + 1e-3)
        ys, xs = np.nonzero(bad)
        res[base] = {'max_pm_rgb_255': round(float(d_rgb.max()), 2), 'max_alpha_255': round(float(d_a.max()), 2),
                     'px_over_tol': int(bad.sum()), 'tol_255': tol,
                     'bbox_bad': None if not bad.any() else [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]}
    return res

if __name__ == '__main__':
    r = check(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 1.0)
    print(json.dumps(r, indent=1))
