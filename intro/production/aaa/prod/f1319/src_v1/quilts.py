"""Fog-of-war quilts (the game's cloud kit, assets/tex/table_clouds) turned into 2.5D appliques: albedo flattened from the sprite,
padding height from the distance to the running-stitch lines (each cell between stitches puffs out), stitch grooves, rounded rims;
placed on the world maps (over the strip and on the walnut), so they take the same relight, shadows and AO."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f1319/src')
from s18common import *
from chron.color import srgb2lin, lin2oklab, hex_lin

CLOUDS = AAA + '/assets/tex/table_clouds'
_cache = {}


def load_sprite(name):
    if name in _cache: return _cache[name]
    im = cv2.imread(f'{CLOUDS}/{name}.png', cv2.IMREAD_UNCHANGED)
    rgb = srgb2lin(cv2.cvtColor(im[..., :3], cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0)
    a = im[..., 3].astype(np.float32) / 255.0
    # stitch lines: orange-brown, chroma well above the cream
    lab = lin2oklab(rgb)
    C = np.hypot(lab[..., 1], lab[..., 2])
    Cm = np.median(C[a > 0.9]) if (a > 0.9).any() else 0.05
    line = np.clip((C - (Cm + 0.018)) / 0.05, 0, 1) * (a > 0.5)
    line = cv2.GaussianBlur(line, (0, 0), 0.7)
    # de-light: flatten the baked shading to 60 %
    L = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    w = (a > 0.5).astype(np.float32)
    Lb = cv2.GaussianBlur(L * w, (0, 0), 12) / (cv2.GaussianBlur(w, (0, 0), 12) + 1e-4)
    Lm = float(np.median(L[a > 0.9])) if (a > 0.9).any() else 0.5
    flat = rgb * ((Lm / np.maximum(Lb, 1e-3)) ** 0.6)[..., None]
    # padding: distance to the nearest stitch line / rim inside the sprite
    cells = ((line < 0.35) & (a > 0.5)).astype(np.uint8)
    d = cv2.distanceTransform(cells, cv2.DIST_L2, 5)
    puff = 1 - np.exp(-d / 5.5)
    puff = cv2.GaussianBlur(puff, (0, 0), 1.0) * (a > 0.4)
    _cache[name] = dict(alb=flat.astype(np.float32), a=a, line=line.astype(np.float32), puff=puff.astype(np.float32))
    return _cache[name]


def make_quilt(name, mm_per_px, angle_deg, flip, PX, hq=3.6, tint=(0.78, 0.76, 0.74), gain=0.80):
    sp = load_sprite(name)
    f = mm_per_px * PX                       # sprite px -> world px (one sprite px spans mm_per_px mm)
    H, W = sp['a'].shape
    Wn, Hn = max(2, int(round(W * f))), max(2, int(round(H * f)))
    ch = {}
    for k in ('alb', 'a', 'line', 'puff'):
        v = sp[k]
        ch[k] = cv2.resize(v, (Wn, Hn), interpolation=cv2.INTER_AREA if f < 1 else cv2.INTER_CUBIC)
    if flip:
        for k in ch: ch[k] = ch[k][:, ::-1].copy()
    # pad and rotate
    diag = int(math.hypot(Wn, Hn)) + 8
    M = cv2.getRotationMatrix2D((Wn / 2, Hn / 2), angle_deg, 1.0)
    M[0, 2] += (diag - Wn) / 2; M[1, 2] += (diag - Hn) / 2
    out = {k: cv2.warpAffine(v, M, (diag, diag), flags=cv2.INTER_LINEAR, borderValue=0) for k, v in ch.items()}
    lum = (out['alb'] * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
    alb = (lum + (out['alb'] - lum) * 0.40) * np.asarray(tint, np.float32) * gain      # fog: pale, desaturated cream
    # slightly darker / dustier toward the rim, stitch lines a bit deeper brown
    h = hq * np.clip(out['puff'], 0, 1) ** 0.85 - 0.9 * np.clip(out['line'], 0, 1) * out['a']
    # tangent along the cell contours (perpendicular to the padding gradient)
    gx = cv2.Sobel(out['puff'], cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(out['puff'], cv2.CV_32F, 0, 1, ksize=3)
    n = np.hypot(gx, gy) + 1e-6
    T = np.dstack([-gy / n, gx / n]).astype(np.float32)
    return dict(alb=alb.astype(np.float32), a=out['a'].astype(np.float32), h=h.astype(np.float32), T=T, size=diag)


def place_quilt(m, q, cx_mm, cy_mm, PX, lift=0.8):
    """alpha-composite the quilt onto the world maps m at world (cx_mm, cy_mm).  Height rides on the surface under it."""
    x0, y0 = m['origin_mm']
    Hm, Wm = m['h'].shape
    S = q['size']
    px0 = int(round((cx_mm - x0) * PX - S / 2)); py0 = int(round((cy_mm - y0) * PX - S / 2))
    X0, Y0 = max(px0, 0), max(py0, 0); X1, Y1 = min(px0 + S, Wm), min(py0 + S, Hm)
    if X1 <= X0 or Y1 <= Y0: return
    sx, sy = slice(X0 - px0, X1 - px0), slice(Y0 - py0, Y1 - py0)
    dx, dy = slice(X0, X1), slice(Y0, Y1)
    a = np.clip((q['a'][sy, sx] - 0.15) / 0.7, 0, 1)
    solid = a > 0.5
    under = cv2.GaussianBlur(m['h'][dy, dx], (0, 0), 2.0 * PX)           # padded quilt rests on the highest nearby surface
    under = np.maximum(under, m['h'][dy, dx])
    m['alb'][dy, dx] = m['alb'][dy, dx] * (1 - a[..., None]) + q['alb'][sy, sx] * a[..., None]
    hn = under + lift + q['h'][sy, sx]
    hh = m['h'][dy, dx]
    m['h'][dy, dx] = np.where(a > 0.05, hh * (1 - a) + hn * a, hh)
    for k, v in (('mat', 8), ('cov', 0)):
        t = m[k][dy, dx]; t[solid] = v
    m['T'][dy, dx][solid] = q['T'][sy, sx][solid]
    if 'solid' not in m: m['solid'] = np.zeros(m['h'].shape, np.float32)
    m['solid'][dy, dx] = np.maximum(m['solid'][dy, dx], a)
