"""Figure cards (game art, realm-tinted in assets/tex_tinted) + their normal maps, trimmed to the alpha bbox."""
import numpy as np, cv2
from common import A

_cache = {}


def load_card(unit, realm):
    k = (unit, realm)
    if k in _cache: return _cache[k]
    a = cv2.imread(f'{A}/assets/tex_tinted/{unit}_idle_{realm}.png', cv2.IMREAD_UNCHANGED)
    n = cv2.imread(f'{A}/assets/tex/figures/{unit}_idle_normal.png', cv2.IMREAD_UNCHANGED)
    alb = cv2.cvtColor(a[..., :3], cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    al = a[..., 3].astype(np.float32) / 255
    nm = cv2.cvtColor(n[..., :3], cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    ys, xs = np.nonzero(al > 0.5)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    y0 = max(0, y0 - 2); x0 = max(0, x0 - 2); y1 = min(al.shape[0], y1 + 2); x1 = min(al.shape[1], x1 + 2)
    r = dict(alb=alb[y0:y1, x0:x1], alpha=al[y0:y1, x0:x1], nrm=nm[y0:y1, x0:x1])
    _cache[k] = r
    return r


def card_aspect(unit, realm):
    c = load_card(unit, realm)
    return c['alpha'].shape[1] / c['alpha'].shape[0]
