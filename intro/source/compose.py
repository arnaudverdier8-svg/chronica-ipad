"""Chronica intro compositor: renders all 66 s at 1920x1080/24fps and pipes to ffmpeg.
Usage: python3 compose.py [--from T] [--to T] [--stills t1,t2,...] [--out file.mp4]"""
import sys, math, os, subprocess
import numpy as np, cv2

D = os.path.dirname(os.path.abspath(__file__)) + '/'
EX = D + 'tex/'
AUDIO = D + '../intro_chronica.mp3'
OW, OH, FPS, DUR = 1920, 1080, 24, 66.0
args = sys.argv[1:]
def arg(n, d):
    return args[args.index(n) + 1] if n in args else d

# ---------------- helpers ----------------
def load(p, alpha=False):
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if im is None:
        im = cv2.cvtColor(np.array(__import__('PIL.Image', fromlist=['Image']).open(p).convert('RGBA')), cv2.COLOR_RGBA2BGRA)
    if im.ndim == 2:
        im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    if not alpha and im.shape[2] == 4:
        im = im[..., :3]
    return im.astype(np.float32) / 255.0

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))
def ss(a, b, x):  # smoothstep
    t = clamp((x - a) / (b - a)) if b != a else (1.0 if x >= b else 0.0)
    return t * t * (3 - 2 * t)
def eio(t):
    t = clamp(t); return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2
def path(keys, t):
    """keys: [(t, *vals)], eased in/out between keys."""
    if t <= keys[0][0]:
        return keys[0][1:]
    for k0, k1 in zip(keys, keys[1:]):
        if t <= k1[0]:
            u = eio((t - k0[0]) / (k1[0] - k0[0]))
            return tuple(a + (b - a) * u for a, b in zip(k0[1:], k1[1:]))
    return keys[-1][1:]

def view(img, cx, cy, zoom, shake=(0, 0), fit=None):
    h, w = img.shape[:2]
    s = (fit or (OH / h)) * zoom
    M = np.float32([[s, 0, OW / 2 - s * cx + shake[0]], [0, s, OH / 2 - s * cy + shake[1]]])
    return cv2.warpAffine(img, M, (OW, OH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT), M

def to_out(M, x, y):
    return (M[0, 0] * x + M[0, 2], M[1, 1] * y + M[1, 2])

def blit(dst, spr, cx, cy, scale=1.0, alpha=1.0, rot=0.0, add=False, tint=None):
    """Alpha-composite sprite (BGRA float) centred at (cx,cy) in dst (BGR float)."""
    if alpha <= 0.003 or scale <= 0.01:
        return
    h, w = spr.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, scale)
    M[0, 2] += cx - w / 2; M[1, 2] += cy - h / 2
    # bounding box in dst
    corners = np.array([[0, 0, 1], [w, 0, 1], [0, h, 1], [w, h, 1]], np.float32) @ M.T
    x0, y0 = np.floor(corners.min(0)).astype(int); x1, y1 = np.ceil(corners.max(0)).astype(int)
    x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(dst.shape[1], x1), min(dst.shape[0], y1)
    if x1 <= x0 or y1 <= y0:
        return
    M2 = M.copy(); M2[0, 2] -= x0; M2[1, 2] -= y0
    warped = cv2.warpAffine(spr, M2, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    col = warped[..., :3]
    if tint is not None:
        col = col * np.array(tint, np.float32)
    a = warped[..., 3:4] * alpha
    roi = dst[y0:y1, x0:x1]
    if add:
        roi += col * a
    else:
        roi[:] = roi * (1 - a) + col * a

def glow_sprite(size=256, sigma=0.22):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / size - 0.5
    g = np.exp(-(xx ** 2 + yy ** 2) / (2 * sigma ** 2 / 4))
    return np.dstack([g, g, g, np.ones_like(g)]).astype(np.float32)
GLOW = glow_sprite()

def add_glow(dst, x, y, radius, color, strength):
    spr = GLOW.copy(); spr[..., :3] *= np.array(color, np.float32)
    blit(dst, spr, x, y, scale=radius / 128.0, alpha=strength, add=True)

def noise2(h, w, scale, seed, stretch=1.0):
    r = np.random.default_rng(seed)
    sm = r.random((max(2, int(h / scale)) + 2, max(2, int(w / (scale * stretch))) + 2)).astype(np.float32)
    return cv2.resize(sm, (w, h), interpolation=cv2.INTER_CUBIC)

# ---------------- precomputed layers ----------------
yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
VIG = (1 - 0.42 * np.clip((((xx - OW / 2) / (OW * 0.62)) ** 2 + ((yy - OH / 2) / (OH * 0.68)) ** 2), 0, 1.4) ** 1.6)[..., None]
GRAIN = [(np.random.default_rng(i).normal(0, 1, (OH, OW)).astype(np.float32) * 0.018)[..., None] for i in range(6)]
# stitch-dissolve field: blotchy noise + horizontal thread streaks
DIS = 0.62 * noise2(OH, OW, 160, 11) + 0.25 * noise2(OH, OW, 18, 12, stretch=7) + 0.13 * noise2(OH, OW, 5, 13, stretch=4)
DIS = (DIS - DIS.min()) / (DIS.max() - DIS.min())
GOLD = np.array([0.30, 0.68, 0.98], np.float32)  # BGR thread gold

def dissolve(a, b, p, glow=1.0):
    """Reveal b over a with a stitched edge glowing in gold thread."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    th = p * 1.12 - 0.06
    m = np.clip((th - DIS) / 0.035, 0, 1)[..., None]
    band = np.exp(-((DIS - th) / 0.012) ** 2)[..., None] * glow
    return a * (1 - m) + b * m + band * GOLD * 0.9

def goldmask(img):
    hsv = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] > 12) & (hsv[..., 0] < 34) & (hsv[..., 1] > 90) & (hsv[..., 2] > 140)).astype(np.float32)
    return cv2.GaussianBlur(m, (0, 0), 2)

def shimmer(out, gm_out, t, speed=0.35, strength=0.35):
    ph = ((t * speed) % 1.6 - 0.3) * (OW + OH)
    band = np.exp(-(((xx * 0.75 + yy * 0.65) - ph) / 140) ** 2)
    out += (gm_out * band)[..., None] * strength * np.array([0.55, 0.85, 1.0], np.float32)

def finish(out, t, grain=1.0, vig=1.0):
    out = out * (1 - (1 - VIG) * vig)
    out += GRAIN[int(t * FPS) % len(GRAIN)] * grain
    return np.clip(out, 0, 1)

MOTES = np.random.default_rng(21).random((46, 4)).astype(np.float32)
def motes(out, t, strength=1.0, color=(0.75, 0.88, 1.0)):
    for (a, b, c, d) in MOTES:
        x = (a * OW + math.sin(t * 0.4 + d * 6) * 40) % OW
        y = OH - ((b * OH + t * (14 + 30 * c)) % OH)
        add_glow(out, x, y, 6 + 10 * c, color, 0.10 * strength * (0.5 + 0.5 * math.sin(t * 1.3 + d * 9)))

def flick(t, i, base=0.78, amp=0.22):
    return base + amp * (0.5 * math.sin(t * 11 + i * 1.7) + 0.3 * math.sin(t * 23.3 + i * 4.1) + 0.2 * math.sin(t * 5.1 + i))

def couched_path(out, pts, frac, width=6, color=GOLD, alpha=1.0):
    n = max(2, int(len(pts) * clamp(frac)))
    if frac <= 0:
        return
    p = np.array(pts[:n], np.float32)
    ov = out.copy()
    cv2.polylines(ov, [p.astype(np.int32)], False, (0.05, 0.12, 0.2), width + 5, cv2.LINE_AA)
    cv2.polylines(ov, [p.astype(np.int32)], False, color.tolist(), width, cv2.LINE_AA)
    cv2.polylines(ov, [(p + [0, -width * 0.25]).astype(np.int32)], False, np.minimum(color * 1.35 + 0.15, 1).tolist(), max(1, width // 3), cv2.LINE_AA)
    # couching ties
    for i in range(0, n - 1, 5):
        q = p[i]; d = p[min(n - 1, i + 1)] - q; d /= (np.linalg.norm(d) + 1e-6); nrm = np.array([-d[1], d[0]])
        a = q + (nrm + d * 0.5) * width * 0.7; b = q - (nrm + d * 0.5) * width * 0.7
        cv2.line(ov, tuple(a.astype(int)), tuple(b.astype(int)), (0.75, 0.92, 1.0), 2, cv2.LINE_AA)
    out[:] = out * (1 - alpha) + ov * alpha
    if 0 < frac < 1:  # needle-point sparkle at the growing end
        add_glow(out, p[-1][0], p[-1][1], 26, (0.6, 0.9, 1.0), 0.9)

# ---------------- assets ----------------
P1 = load(D + 'panels/p1_oath.jpg'); P1E = load(D + 'p1_empty.png'); P3 = load(D + 'panels/p3_death.jpg'); P6 = load(D + 'panels/p6_ruin.jpg')
WAR = load(D + 'war_bg.png')
GM1, GM3, GM6 = goldmask(P1), goldmask(P3), goldmask(P6)
CROWN = load(D + 'crown.png', True)
def sprite(name, flip=False):
    im = load(D + 'tex/' + name + '.png', True)
    return cv2.flip(im, 1) if flip else im
LOGO = load(D + 'tex/logo_title.png', True)
PUFF = [load(D + 'tex/cloud_puff_%d.png' % i, True) for i in range(1, 9)]

# P1-empty in night grade (BGR multiply), precomputed
NIGHT = np.clip(P1E * np.array([0.78, 0.50, 0.40], np.float32) * 0.62, 0, 1)
GMN = goldmask(P1E) * 0.6

# ruin: flame mask + displacement base
hsv6 = cv2.cvtColor((P6 * 255).astype(np.uint8), cv2.COLOR_BGR2HSV)
FLAME = (((hsv6[..., 0] < 22) | (hsv6[..., 0] > 172)) & (hsv6[..., 1] > 140) & (hsv6[..., 2] > 170)).astype(np.float32)
FLAME[:, :] *= (np.arange(P6.shape[0])[:, None] < 1150)
FLAME = cv2.GaussianBlur(FLAME, (0, 0), 6)
SMOKE = ((hsv6[..., 1] < 70) & (hsv6[..., 2] < 150)).astype(np.float32) * (np.arange(P6.shape[0])[:, None] < 700)
SMOKE = cv2.GaussianBlur(SMOKE, (0, 0), 10)
Y6, X6 = np.mgrid[0:P6.shape[0], 0:P6.shape[1]].astype(np.float32)

# ---------------- shots ----------------
P1_CANDLES = [(104, 1010), (2656, 1010), (2390, 1180), (2516, 1170)]
P3_CANDLES = [(244, 575), (460, 385), (2300, 385), (2512, 568)]
CUPS = [(290, 1150), (612, 1140), (1805, 1150), (2222, 1150)]
LORD_HEADS = [(530, 545), (892, 505), (1888, 520), (2262, 540)]
RING_C, RING_R = (1376, 820), (1230, 640)

def ring_pts():
    return [(RING_C[0] + RING_R[0] * math.cos(a), RING_C[1] + RING_R[1] * math.sin(a)) for a in np.linspace(math.pi / 2, math.pi / 2 + 2 * math.pi, 220)]
def cup_thread(i):
    x0, y0 = CUPS[i]; x1, y1 = RING_C[0] + RING_R[0] * math.cos(math.pi / 2 + (i - 1.5) * 0.5), RING_C[1] + RING_R[1] * math.sin(math.pi / 2 + (i - 1.5) * 0.5)
    pts = []
    for s in np.linspace(0, 1, 90):
        x = x0 + (x1 - x0) * s + 60 * math.sin(s * 9 + i) * (1 - s) * s * 4
        y = y0 + (y1 - y0) * (s ** 0.8) - 120 * math.sin(s * math.pi)
        pts.append((x, y))
    return pts
RING = ring_pts(); THREADS = [cup_thread(i) for i in range(4)]

def shot_oath(t):
    """0 -> 15.9 : one realm, one table, one oath, one crown; cups and the oath-ring."""
    keys = [(0.0, 1380, 330, 1.9), (2.6, 1380, 300, 1.75), (3.4, 1380, 300, 1.7),
            (4.4, 1380, 1050, 1.25), (5.2, 1380, 1060, 1.25), (5.9, 1360, 1240, 1.9), (6.7, 1370, 1245, 1.95),
            (7.4, 1380, 560, 2.15), (8.3, 1380, 540, 2.2), (9.4, 1376, 760, 1.0), (14.6, 1376, 768, 1.04), (15.9, 1376, 768, 1.06)]
    cx, cy, z = path(keys, t)
    out, M = view(P1, cx, cy, z)
    gm = cv2.warpAffine(GM1, M, (OW, OH))
    shimmer(out, gm, t, 0.33, 0.30)
    # word accents: soft gold bloom on the named thing
    for (tw, (px, py), r) in [(3.05, (1380, 300), 420), (4.7, (1380, 1250), 600), (5.8, (1380, 1270), 360), (7.7, (1380, 520), 260)]:
        k = math.exp(-((t - tw - 0.3) / 0.45) ** 2)
        if k > 0.01:
            x, y = to_out(M, px, py); add_glow(out, x, y, r * M[0, 0], (0.35, 0.75, 1.0), 0.32 * k)
    snuff = 1 - ss(14.9, 15.5, t)
    for i, (px, py) in enumerate(P1_CANDLES):
        x, y = to_out(M, px, py - 20)
        add_glow(out, x, y, 120 * M[0, 0] * 2.2, (0.35, 0.7, 1.0), 0.42 * flick(t, i) * snuff)
    # threads from the cups rise into a ring around the banner (10.2 -> 13.4)
    fade = 1 - ss(14.85, 15.35, t)
    if t > 10.1 and fade > 0:
        for i in range(4):
            cx_, cy_ = to_out(M, *CUPS[i])
            k = math.exp(-((t - 10.5 - i * 0.12) / 0.5) ** 2)
            add_glow(out, cx_, cy_ - 20 * M[0, 0], 140 * M[0, 0], (0.45, 0.85, 1.0), 0.65 * k)
        rf = ss(11.55, 13.3, t)
        sag = ss(14.85, 15.5, t)
        pts = [to_out(M, x, y + sag * 120 * max(0, (y - RING_C[1]) / RING_R[1])) for x, y in RING]
        couched_path(out, pts, rf, width=max(5, int(16 * M[0, 0])), alpha=fade)
        if t > 13.3:
            k = math.exp(-((t - 13.45) / 0.35) ** 2)
            x, y = to_out(M, *RING_C); add_glow(out, x, y, 700 * M[0, 0], (0.45, 0.8, 1.0), 0.35 * k * fade)
    # nightfall at the king's death
    out *= 1 - 0.55 * ss(14.9, 15.8, t)
    out[..., 0] += 0.05 * ss(14.9, 15.8, t)
    motes(out, t, 1.0)
    return out

def shot_death(t):
    """15.3 -> 19.4 : the king lies dead."""
    cx, cy, z = path([(15.3, 1376, 768, 1.0), (17.2, 1640, 690, 1.25), (19.4, 1900, 640, 1.6)], t)
    out, M = view(P3, cx, cy, z)
    gm = cv2.warpAffine(GM3, M, (OW, OH)); shimmer(out, gm, t, 0.25, 0.22)
    for i, (px, py) in enumerate(P3_CANDLES):
        out_i = 1.0 if i != 3 else 1 - ss(17.5, 17.9, t)
        x, y = to_out(M, px, py)
        add_glow(out, x, y, 150 * M[0, 0] * 2, (0.35, 0.72, 1.0), 0.5 * flick(t, i) * out_i)
    motes(out, t, 0.7)
    return out

def shot_chair(t):
    """18.6 -> 27.6 : the empty chair; every lord sees a crown on his own head."""
    keys = [(18.6, 1376, 820, 1.04), (21.0, 1380, 760, 1.18), (22.4, 1380, 680, 1.75), (23.6, 1380, 690, 1.85),
            (24.5, 1376, 760, 1.06), (27.6, 1376, 760, 1.12)]
    cx, cy, z = path(keys, t)
    out, M = view(NIGHT, cx, cy, z)
    gm = cv2.warpAffine(GMN, M, (OW, OH)); shimmer(out, gm, t, 0.25, 0.25)
    # light shaft onto the throne
    sx, sy = to_out(M, 1380, 360)
    shaft = np.exp(-((xx - sx) / (260 * M[0, 0])) ** 2) * np.clip((yy - (sy - 900 * M[0, 0])) / (900 * M[0, 0]), 0, 1) * (yy < sy + 520 * M[0, 0])
    lit = ss(19.2, 21.5, t)
    out += shaft[..., None] * np.array([0.30, 0.42, 0.52], np.float32) * 0.55 * lit
    # floating crown above the empty seat
    bob = math.sin(t * 2.1) * 8
    x, y = to_out(M, 1380, 470 + bob)
    add_glow(out, x, y, 260 * M[0, 0], (0.4, 0.8, 1.0), 0.55 * lit)
    blit(out, CROWN, x, y, scale=M[0, 0] * 1.05, alpha=lit, rot=math.sin(t * 1.3) * 3)
    # crowns on each lord's head (24.4 -> 26.2)
    for i, (hx, hy) in enumerate(LORD_HEADS):
        t0 = 24.45 + i * 0.42
        a = ss(t0, t0 + 0.4, t)
        if a > 0:
            x, y = to_out(M, hx, hy - 30 - 20 * (1 - a))
            k = math.exp(-((t - t0 - 0.25) / 0.3) ** 2)
            add_glow(out, x, y, 180 * M[0, 0], (0.45, 0.85, 1.0), 0.7 * k + 0.12)
            blit(out, CROWN, x, y, scale=M[0, 0] * 0.62, alpha=a * 0.92, rot=(i - 1.5) * 4)
    # darkness falls in the pause before the war
    out *= 1 - ss(26.7, 27.5, t)
    motes(out, t, 0.6)
    return out

# ---- war ----
LEFT = [('unit_legionary', False), ('unit_spearman', False), ('unit_knight', False), ('unit_man_at_arms', False), ('unit_engineer', False)]
RIGHT = [('unit_horse_archer', True), ('unit_archer', True), ('unit_scout', True), ('unit_mercenary', True), ('unit_goblin', True)]
LS = [sprite(n, f) for n, f in LEFT]; RS = [sprite(n, f) for n, f in RIGHT]
LION_R = sprite('vignette_red'); LION_B = sprite('vignette_blue', True)
ARROWS = np.random.default_rng(31).random((44, 4)).astype(np.float32)
def arrow(out, p, d, s):
    d = d / (np.linalg.norm(d) + 1e-6); n = np.array([-d[1], d[0]])
    tail = p - d * 70 * s; head = p + d * 8 * s
    cv2.line(out, tuple(tail.astype(int)), tuple(p.astype(int)), (0.10, 0.22, 0.35), max(2, int(5 * s)), cv2.LINE_AA)
    cv2.line(out, tuple(p.astype(int)), tuple(head.astype(int)), (0.8, 0.8, 0.82), max(2, int(6 * s)), cv2.LINE_AA)
    for sgn in (-1, 1):
        f = tail + d * 14 * s + n * sgn * 10 * s
        cv2.line(out, tuple((tail + d * 2).astype(int)), tuple(f.astype(int)), (0.15, 0.15, 0.7), max(2, int(4 * s)), cv2.LINE_AA)

def shot_war(t):
    """28.1 -> 32.9 : the hundred years' war."""
    z = 1.14 + 0.1 * ss(28.1, 32.9, t)
    clash = 29.85
    sh = (0, 0)
    if clash < t < clash + 0.6:
        k = (1 - (t - clash) / 0.6) * 18; sh = (k * math.sin(t * 90), k * math.cos(t * 77))
    canvas = WAR.copy()
    # a hundred years: sky hue drifts through seasons
    yrs = ss(29.6, 30.9, t) * (1 - ss(30.9, 31.6, t))
    if yrs > 0:
        canvas[:1000] = canvas[:1000] * (1 - 0.35 * yrs) + 0.35 * yrs * canvas[:1000, :, ::-1]
    adv = ss(28.1, clash - 0.15, t)
    unravel = ss(30.9, 31.9, t)
    # banners above each army
    for (spr, side) in [(LION_R, -1), (LION_B, 1)]:
        x = 1376 + side * (1500 - 900 * adv)
        blit(canvas, spr, x, 560 + 10 * math.sin(t * 3 + side), scale=1.5, alpha=1 - unravel)
    for row in (1, 0):  # back row first
        for i in range(5):
            for side, sprs in ((-1, LS), (1, RS)):
                spr = sprs[(i + row * 2) % 5]
                base_x = 1376 + side * (300 + i * 250 + row * 125)
                x = base_x + side * (1700 * (1 - adv))
                if t > clash:
                    x += side * (-40 * math.sin((t - clash) * 5 + i))
                hop = abs(math.sin(t * 9 + i * 1.3 + side)) * 26 * (1 - ss(clash, clash + 0.3, t) * 0.6)
                y = (1080 if row else 1290) - hop + i * 8
                sc_ = (1.4 if row else 1.85)
                tint = (0.75, 0.75, 0.8) if row else None
                blit(canvas, spr, x, y, scale=sc_, alpha=1 - unravel, tint=tint)
    # arrows: volleys arcing across the sky
    for k, (a, b, c, d) in enumerate(ARROWS):
        t0 = 28.5 + a * 2.2; dur = 1.1 + 0.4 * b
        u = (t - t0) / dur
        if 0 < u < 1:
            side = 1 if k % 2 else -1
            x0 = 1376 + side * (1300 + 200 * c); x1 = 1376 - side * (200 + 900 * d)
            x = x0 + (x1 - x0) * u; y = 1000 - 900 * 4 * u * (1 - u) * (0.7 + 0.3 * c) + 100 * u
            dx = (x1 - x0); dy = -900 * 4 * (1 - 2 * u) * (0.7 + 0.3 * c) + 100
            arrow(canvas, np.array([x, y], np.float32), np.array([dx, dy], np.float32), 2.0)
    # clash: dust clouds of stitched puffs
    if t > clash - 0.05:
        for j in range(9):
            r = np.random.default_rng(j)
            u = clamp((t - clash) / 1.6)
            px = 1376 + (r.random() - 0.5) * 900 * (0.4 + u); py = 1080 - r.random() * 380 - 120 * u
            blit(canvas, PUFF[j % 8], px, py, scale=(0.9 + 1.2 * u) * (0.8 + 0.6 * r.random()), alpha=(1 - ss(31.2, 32.0, t)) * 0.9, tint=(0.5, 0.55, 0.62))
    out, M = view(canvas, 1376, 880, z, sh)
    if clash < t < clash + 0.5:
        add_glow(out, OW / 2, OH * 0.62, 900, (0.6, 0.85, 1.0), 0.8 * (1 - (t - clash) / 0.5))
    motes(out, t, 0.5, (0.5, 0.8, 1.0))
    return out

def shot_ruin(t):
    """32.4 -> 35.4 : cities fell to ruin."""
    cx, cy, z = path([(32.4, 1376, 760, 1.0), (35.4, 1440, 640, 1.32)], t)
    sh = (0, 0)
    if 33.8 < t < 34.5:
        k = (1 - (t - 33.8) / 0.7) * 10; sh = (k * math.sin(t * 80), k * math.cos(t * 71))
    disp_y = (np.sin(X6 / 37 + t * 7.0) * 5 + np.sin(Y6 / 23 + t * 11.0) * 4) * FLAME - SMOKE * (np.sin(X6 / 90 + t * 1.7) * 6)
    disp_x = np.sin(Y6 / 41 + t * 9.0) * 4 * FLAME + SMOKE * np.sin(Y6 / 70 + t * 1.3) * 8
    src = cv2.remap(P6, X6 + disp_x, Y6 + disp_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    src = src + FLAME[..., None] * (0.12 * flick(t, 3, 0.6, 0.4)) * np.array([0.2, 0.55, 1.0], np.float32)
    out, M = view(src, cx, cy, z, sh)
    gm = cv2.warpAffine(GM6, M, (OW, OH)); shimmer(out, gm, t, 0.3, 0.2)
    # embers rising
    r = np.random.default_rng(7)
    for k in range(70):
        a, b, c = r.random(3)
        x0, y0 = to_out(M, 900 + a * 1500, 1000 - b * 300)
        life = (t * (0.5 + c) + a * 5) % 1.0
        add_glow(out, x0 + math.sin(t * 3 + k) * 30, y0 - life * 600, 10 + 8 * c, (0.25, 0.6, 1.0), 0.45 * (1 - life))
    return out

# ---- 3D map frames ----
def frame3d(t):
    i = int(round((t - 35.0) * FPS)) + 1
    i = max(1, min(467, i))
    p = D + 'frames3d/f_%04d.jpg' % i
    while not os.path.exists(p) and i > 1:
        i -= 1; p = D + 'frames3d/f_%04d.jpg' % i
    im = cv2.imread(p)
    if im is None:
        return np.zeros((OH, OW, 3), np.float32)
    im = cv2.resize(im, (OW, OH), interpolation=cv2.INTER_LANCZOS4).astype(np.float32) / 255
    blur = cv2.GaussianBlur(im, (0, 0), 1.2)
    return np.clip(im * 1.35 - blur * 0.35, 0, 1)

# ---- blank page + title ----
def make_linen():
    r = np.random.default_rng(9)
    base = np.zeros((OH + 200, OW + 200, 3), np.float32) + np.array([0.70, 0.82, 0.88], np.float32)
    Y, X = np.mgrid[0:OH + 200, 0:OW + 200].astype(np.float32)
    weave = (np.sin(X * 1.9) * np.sin(Y * 1.9)) * 0.035 + (np.sin(X * 0.95 + np.sin(Y * 0.05) * 2) * 0.02)
    fib = noise2(OH + 200, OW + 200, 3, 4, stretch=8) * 0.05 + noise2(OH + 200, OW + 200, 60, 5) * 0.06
    return np.clip(base + (weave + fib - 0.05)[..., None], 0, 1)
LINEN = make_linen()

def hoop(out, cx, cy, rx, ry, s):
    for k, (w, col) in enumerate([(int(46 * s), (0.10, 0.20, 0.32)), (int(36 * s), (0.22, 0.42, 0.62)), (int(10 * s), (0.42, 0.66, 0.86))]):
        cv2.ellipse(out, (int(cx), int(cy + (8 * s if k == 0 else 0))), (int(rx), int(ry)), 0, 0, 360, col, w, cv2.LINE_AA)
    # screw clasp at the top
    cv2.rectangle(out, (int(cx - 40 * s), int(cy - ry - 52 * s)), (int(cx + 40 * s), int(cy - ry + 14 * s)), (0.18, 0.34, 0.52), -1, cv2.LINE_AA)
    cv2.circle(out, (int(cx), int(cy - ry - 64 * s)), int(22 * s), (0.62, 0.66, 0.70), -1, cv2.LINE_AA)

def needle(out, fx, fy, s=1.0):
    tip = np.array([fx, fy]); d = np.array([0.48, -0.88]); n = np.array([0.88, 0.48])
    eye = tip + d * 300 * s
    poly = np.array([tip, eye + n * 7 * s, eye + d * 14 * s, eye - n * 7 * s], np.float32)
    shadow = poly + [10, 12]
    cv2.fillPoly(out, [shadow.astype(np.int32)], (0.25, 0.3, 0.33), cv2.LINE_AA)
    cv2.fillPoly(out, [poly.astype(np.int32)], (0.70, 0.73, 0.76), cv2.LINE_AA)
    cv2.line(out, tuple((tip + n * 2).astype(int)), tuple((eye + n * 3).astype(int)), (0.96, 0.97, 0.98), 2, cv2.LINE_AA)
    cv2.ellipse(out, tuple((eye - d * 4 * s).astype(int)), (int(3 * s), int(9 * s)), math.degrees(math.atan2(d[1], d[0])) + 90, 0, 360, (0.3, 0.35, 0.4), -1, cv2.LINE_AA)
    thr = [eye - d * 4 * s + np.array([k * 10, -k * 1.5 - 40 * math.sin(k * 0.1)]) for k in range(45)]
    cv2.polylines(out, [np.array(thr, np.int32)], False, (0.05, 0.12, 0.2), 8, cv2.LINE_AA)
    cv2.polylines(out, [np.array(thr, np.int32)], False, GOLD.tolist(), 5, cv2.LINE_AA)

def shot_page(t):
    """53.7 -> 66 : one blank page; the chronicle stitches its own name."""
    z = 1.0 + 0.08 * ss(53.7, 66, t)
    ox = int(100 - 40 * (z - 1)); out = LINEN[ox:ox + OH, ox:ox + OW].copy()
    # warm candlelight pool
    out *= (0.82 + 0.25 * np.exp(-(((xx - OW * 0.5) / 900) ** 2 + ((yy - OH * 0.48) / 620) ** 2)))[..., None]
    s = z
    hoop(out, OW / 2, OH / 2 + 10, 820 * s, 470 * s, s)
    # logo stitched in, left to right, 57.6 -> 61.4
    p = ss(57.6, 61.4, t)
    if p > 0:
        lw = 1360 * s
        sc_ = lw / LOGO.shape[1]
        L = LOGO.copy()
        cols = np.arange(L.shape[1])[None, :, None].astype(np.float32) / L.shape[1]
        jag = (np.sin(np.arange(L.shape[0]) * 0.9)[:, None, None] * 0.006)
        m = np.clip((p * 1.04 - cols - jag) / 0.012, 0, 1)
        L[..., 3:4] *= m
        blit(out, L, OW / 2, OH / 2 - 10, scale=sc_)
        if p < 1:
            fx = OW / 2 - lw / 2 + lw * p
            fy = OH / 2 - 10 + math.sin(t * 14) * 60 * s
            add_glow(out, fx, fy, 70, (0.5, 0.85, 1.0), 0.9)
            needle(out, fx, fy, s)
        if t > 61.4:
            k = math.exp(-((t - 61.7) / 0.5) ** 2)
            add_glow(out, OW / 2, OH / 2, 900, (0.5, 0.82, 1.0), 0.35 * k)
    else:
        # needle resting on the blank linen before it starts to sew
        u = ss(56.3, 57.6, t)
        nx, ny = OW / 2 - 300 * s - 380 * u, OH / 2 + 180 - 190 * u
        needle(out, nx, ny, s)
    motes(out, t, 0.6)
    return out

BLACK = np.zeros((OH, OW, 3), np.float32)
def frame(t):
    # ---- timeline ----
    if t < 15.3:
        out = shot_oath(t)
        if t < 1.6:
            out = dissolve(BLACK, out, ss(0.0, 1.6, t))
    elif t < 16.3:
        out = dissolve(shot_oath(t), shot_death(t), ss(15.3, 16.3, t))
    elif t < 18.6:
        out = shot_death(t)
    elif t < 19.6:
        out = dissolve(shot_death(t), shot_chair(t), ss(18.6, 19.6, t))
    elif t < 27.6:
        out = shot_chair(t)
    elif t < 28.1:
        out = BLACK.copy()
    elif t < 32.4:
        out = shot_war(t)
        if t < 28.5:
            out = dissolve(BLACK, out, ss(28.1, 28.45, t), 1.5)
    elif t < 33.1:
        out = dissolve(shot_war(t), shot_ruin(t), ss(32.4, 33.1, t))
    elif t < 34.8:
        out = shot_ruin(t)
    elif t < 35.5:
        out = dissolve(shot_ruin(t), frame3d(t), ss(34.8, 35.5, t))
    elif t < 53.75:
        out = frame3d(t)
    elif t < 54.4:
        out = dissolve(frame3d(t), shot_page(t), ss(53.75, 54.4, t), 1.4)
    else:
        out = shot_page(t)
    out = finish(out, t, 1.0, 0.85 if 35.5 < t < 53.75 else 1.0)
    out *= 1 - ss(64.3, 65.9, t)
    return out

def to8(img):
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)

if __name__ == '__main__':
    if '--stills' in args:
        for s in arg('--stills', '').split(','):
            t = float(s); cv2.imwrite(D + 'still_%05.2f.jpg' % t, to8(frame(t)), [cv2.IMWRITE_JPEG_QUALITY, 90])
        sys.exit(0)
    t0, t1 = float(arg('--from', 0)), float(arg('--to', DUR))
    outp = arg('--out', D + 'chronica_intro.mp4')
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', '%dx%d' % (OW, OH), '-r', str(FPS), '-i', '-']
    if '--noaudio' not in args:
        cmd += ['-ss', str(t0), '-i', AUDIO, '-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-b:a', '192k', '-shortest']
    cmd += ['-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', outp]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n0, n1 = int(round(t0 * FPS)), int(round(t1 * FPS))
    for i in range(n0, n1):
        ff.stdin.write(to8(frame(i / FPS)).tobytes())
        if i % 48 == 0:
            print('t=%.1f' % (i / FPS), flush=True)
    ff.stdin.close(); ff.wait()
    print('DONE', outp)
