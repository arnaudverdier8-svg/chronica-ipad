"""Fog-of-war quilts (the game's cloud kit, assets/tex/table_clouds) turned into 2.5D appliques (v2): albedo flattened from the sprite and
re-tinted to the cloth's warm drab (not grey-lilac), padding height from the distance to the running-stitch lines with PER-CELL random
padding, puckering at the stitch lines, linen slubs on the surface, soot / dust ageing toward the rim, a smooth random warp and a random
skew per instance so that no two read as the same stamp.  Placed on the world maps (over the strip and on the walnut), so they take the
same relight, shadows and AO."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f1319/src')
from s18common import *
from chron.color import srgb2lin, lin2oklab, oklab2lin, hex_lin
from detail import vn_aniso

CLOUDS = AAA + '/assets/tex/table_clouds'
_cache = {}


def load_sprite(name):
    if name in _cache: return _cache[name]
    im = cv2.imread(f'{CLOUDS}/{name}.png', cv2.IMREAD_UNCHANGED)
    rgb = srgb2lin(cv2.cvtColor(im[..., :3], cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0)
    a = im[..., 3].astype(np.float32) / 255.0
    lab = lin2oklab(rgb)
    C = np.hypot(lab[..., 1], lab[..., 2])
    Cm = np.median(C[a > 0.9]) if (a > 0.9).any() else 0.05
    line = np.clip((C - (Cm + 0.018)) / 0.05, 0, 1) * (a > 0.5)
    line = cv2.GaussianBlur(line, (0, 0), 0.7)
    L = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    w = (a > 0.5).astype(np.float32)
    Lb = cv2.GaussianBlur(L * w, (0, 0), 12) / (cv2.GaussianBlur(w, (0, 0), 12) + 1e-4)
    Lm = float(np.median(L[a > 0.9])) if (a > 0.9).any() else 0.5
    flat = rgb * ((Lm / np.maximum(Lb, 1e-3)) ** 0.6)[..., None]
    cells = ((line < 0.35) & (a > 0.5)).astype(np.uint8)
    d = cv2.distanceTransform(cells, cv2.DIST_L2, 5)
    puff = 1 - np.exp(-d / 5.5)
    puff = cv2.GaussianBlur(puff, (0, 0), 1.0) * (a > 0.4)
    # cell ids (the padded pillows between the stitch lines) for per-cell padding variation
    nlab, lab_ids = cv2.connectedComponents(cells, connectivity=4)
    _cache[name] = dict(alb=flat.astype(np.float32), a=a, line=line.astype(np.float32), puff=puff.astype(np.float32), cells=lab_ids.astype(np.int32), n=nlab)
    return _cache[name]


def make_quilt(name, mm_per_px, angle_deg, flip, PX, hq=3.6, tint=(0.92, 0.83, 0.70), gain=0.50, seed=0, skew=(0.0, 0.0), aspect=1.0):
    sp = load_sprite(name)
    r = np.random.default_rng(seed + 1000)
    f = mm_per_px * PX                       # sprite px -> world px (one sprite px spans mm_per_px mm)
    H, W = sp['a'].shape
    # per-cell padding (0.65 .. 1.35) and tone (+-6 %): irregular stuffing; 1/4 of the cells slump (0.45 .. 0.7)
    mult = r.uniform(0.70, 1.30, sp['n']).astype(np.float32)
    slump = r.random(sp['n']) < 0.22
    mult[slump] = r.uniform(0.45, 0.70, int(slump.sum()))
    mult[0] = 1.0
    cm = cv2.GaussianBlur(mult[sp['cells']], (0, 0), 1.6)
    tone = cv2.GaussianBlur(r.uniform(0.94, 1.06, sp['n']).astype(np.float32)[sp['cells']], (0, 0), 1.0)
    # puckering: low-frequency dimples of the padding, stronger along the stitch lines
    pk = cv2.GaussianBlur(r.standard_normal((H, W)).astype(np.float32), (0, 0), 6.0); pk /= (pk.std() + 1e-6)
    puff = np.clip(sp['puff'] * cm * (1 + 0.12 * pk), 0, 1.4)
    Wn, Hn = max(2, int(round(W * f * aspect))), max(2, int(round(H * f)))
    ch = {}
    src = dict(alb=sp['alb'] * tone[..., None], a=sp['a'], line=sp['line'], puff=puff)
    for k, v in src.items():
        ch[k] = cv2.resize(v, (Wn, Hn), interpolation=cv2.INTER_AREA if f < 1 else cv2.INTER_CUBIC)
    if flip:
        for k in ch: ch[k] = ch[k][:, ::-1].copy()
    diag = int(math.hypot(Wn, Hn)) + 16
    M = cv2.getRotationMatrix2D((Wn / 2, Hn / 2), angle_deg, 1.0)
    M[0, 0] += skew[0]; M[1, 1] += skew[1]; M[0, 1] += skew[0] * 0.5; M[1, 0] += skew[1] * 0.5
    M[0, 2] += (diag - Wn) / 2; M[1, 2] += (diag - Hn) / 2
    # smooth random warp (+-1.8 mm): hand-cut, hand-stuffed silhouettes
    gx = cv2.GaussianBlur(r.standard_normal((diag, diag)).astype(np.float32), (0, 0), 7.0 * PX); gx *= 1.8 * PX / (gx.std() + 1e-6)
    gy = cv2.GaussianBlur(r.standard_normal((diag, diag)).astype(np.float32), (0, 0), 7.0 * PX); gy *= 1.8 * PX / (gy.std() + 1e-6)
    yy, xx = np.mgrid[0:diag, 0:diag].astype(np.float32)
    out = {}
    for k, v in ch.items():
        w_ = cv2.warpAffine(v, M, (diag, diag), flags=cv2.INTER_LINEAR, borderValue=0)
        out[k] = cv2.remap(w_, xx + gx, yy + gy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    a = np.clip(out['a'], 0, 1)
    lum = (out['alb'] * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
    # warm drab linen (the cloth's own colour family, a little smokier): chroma restored to ~65 % of the sprite's, tinted to the key
    alb = (lum + (out['alb'] - lum) * 0.30) * np.asarray(tint, np.float32) * gain
    # soot / dust: darker toward the silhouette rim, in the stitch grooves and in random blotches
    dist = cv2.distanceTransform((a > 0.5).astype(np.uint8), cv2.DIST_L2, 3) / PX
    rim = np.exp(-dist / 7.0)
    blot = np.clip(0.5 + 0.9 * vn_aniso(diag, diag, PX, 22.0, 22.0, seed + 5, 3), 0, 1)
    soot = np.clip(0.20 * rim + 0.18 * blot + 0.28 * np.clip(out['line'], 0, 1), 0, 0.7)
    alb = alb * (1 - soot[..., None]) + (alb * np.array([0.55, 0.50, 0.46], np.float32)) * soot[..., None]
    # linen surface: slubs / barre at the resolvable scale
    barre = vn_aniso(diag, diag, PX, 40.0, 2.3, seed + 6, 2); slub = vn_aniso(diag, diag, PX, 2.4, 14.0, seed + 7, 2)
    alb = alb * (1 + 0.07 * barre[..., None] + 0.05 * slub[..., None])
    h = hq * np.clip(out['puff'], 0, 1.4) ** 0.85 - 1.1 * np.clip(out['line'], 0, 1) * out['a'] + 0.05 * (barre + slub)
    gx_ = cv2.Sobel(out['puff'], cv2.CV_32F, 1, 0, ksize=3); gy_ = cv2.Sobel(out['puff'], cv2.CV_32F, 0, 1, ksize=3)
    n = np.hypot(gx_, gy_) + 1e-6
    T = np.dstack([-gy_ / n, gx_ / n]).astype(np.float32)
    return dict(alb=alb.astype(np.float32), a=a.astype(np.float32), h=h.astype(np.float32), T=T, size=diag)


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
