"""One grade for R25 and Eevee layers (pipeline 5.4): exposure -> ACES fit (Narkowicz) -> act grade (sat, lift, gamma,
gain) -> clamps (black #07070A, white #F3E8D0, cool shadow tint #1A1620) -> sRGB -> grain (1.2 % luminance, seeded)."""
import numpy as np, cv2
from .color import srgb2lin, lin2srgb, hex2srgb, LUMA
from .config import palette

BLACK = srgb2lin(hex2srgb('#07070A'))
WHITE = srgb2lin(hex2srgb('#F3E8D0'))
SHADOW_TINT = srgb2lin(hex2srgb('#1A1620'))

ACT_FRAMES = [('I', 0, 445), ('II', 446, 843), ('III', 844, 1381), ('IV', 1382, 1688), ('V', 1689, 1983)]
ACT_IDS = {'I': 'I_oath', 'II': 'II_death', 'III': 'III_war_ruin', 'IV': 'IV_renewal', 'V': 'V_question'}


def aces(x):
    return np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0, 1)


def act_params(act):
    """act: 'I'..'V' or a palette act id -> dict(sat, lift, gamma, gain) (linear lift/gain colours)."""
    if act is None:
        return None
    aid = ACT_IDS.get(act, act)
    for a in palette()['acts']:
        if a['id'].lower().startswith(aid.lower()[:4]) or a['id'] == aid:
            g = a['grade']
            return dict(sat=g.get('sat', 1.0), lift=srgb2lin(hex2srgb(g.get('lift', '#000000'))),
                        gamma=g.get('gamma', 1.0), gain=srgb2lin(hex2srgb(g.get('gain', '#FFFFFF'))))
    return None


def act_of_frame(f):
    for a, f0, f1 in ACT_FRAMES:
        if f0 <= f <= f1:
            return a
    return 'V'


def grade(lin, exposure=0.85, act=None, grain=0.012, seed=0, out_u16=False):
    """linear scene colour -> sRGB uint8 (or uint16)."""
    x = aces(np.asarray(lin, np.float32) * exposure)
    ap = act_params(act) if isinstance(act, str) else act
    if ap is not None:
        l = (x * LUMA).sum(-1, keepdims=True)
        x = l + (x - l) * ap['sat']
        x = np.clip(x, 0, 1) ** (1.0 / ap['gamma'])
        gain = ap['gain'] / ap['gain'].max()
        x = ap['lift'] * 0.6 + x * (gain - ap['lift'] * 0.6)
    lum = (x * LUMA).sum(-1, keepdims=True)
    sh = np.clip(1 - lum / 0.18, 0, 1) * 0.14
    x = x * (1 - sh) + (x * SHADOW_TINT / SHADOW_TINT.mean()) * sh
    x = BLACK + x * (WHITE - BLACK)
    s = lin2srgb(x)
    if grain > 0:
        r = np.random.default_rng(seed)
        g = r.standard_normal(s.shape[:2]).astype(np.float32)
        g = cv2.GaussianBlur(g, (0, 0), 0.7)
        s = s + grain * g[..., None]
    if out_u16:
        return np.clip(s * 65535 + 0.5, 0, 65535).astype(np.uint16)
    return np.clip(s * 255 + 0.5, 0, 255).astype(np.uint8)
